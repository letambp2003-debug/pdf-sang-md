import traceback
from datetime import datetime, timezone
from pathlib import Path
from app.config import settings
from app.services.job_store import JobStore
from app.services.pdf_utils import preflight_pdf, render_pages, sha256_file, write_json
from app.services.ocr_preprocess import preprocess_pdf
from app.services.extract_pymupdf import extract_with_pymupdf
from app.services.extract_mineru import extract_with_mineru, mineru_available
from app.services.qa_rules import run_rule_qa
from app.services.formula_qa import run_formula_qa
from app.services.table_qa import run_table_qa
from app.services.gemini_qa import qa_page
from app.services.safe_fix import apply_patches, rollback
from app.services.datapack import build_datapack
from app.services.package import build_delivery


def _load_page_md(extract_result: dict, page_no: int) -> str:
    files = extract_result.get("page_files") or []
    if files and page_no <= len(files):
        return Path(files[page_no - 1]).read_text(encoding="utf-8", errors="replace")

    structured = extract_result.get("structured_content") or {}
    pages = structured.get("pages", []) if isinstance(structured, dict) else []
    if page_no <= len(pages):
        blocks = pages[page_no - 1].get("blocks", [])
        parts = []
        for block in blocks:
            content = block.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
        return "\n\n".join(parts)
    return ""


def _local_qa(extracted: dict, expected_pages: int) -> dict:
    document_md = Path(extracted["document_md"])
    page_files = extracted.get("page_files") or []
    rule = run_rule_qa(document_md, expected_pages, Path(extracted["assets_dir"]))
    formula = run_formula_qa(document_md, page_files)
    table = run_table_qa(document_md, page_files)
    warnings = list(rule.get("warnings", []))
    if formula["status"] == "REVIEW":
        warnings.append(f"Formula QA phat hien {formula['issue_count']} van de can xem lai.")
    if table["status"] == "REVIEW":
        warnings.append(f"Table QA phat hien {table['issue_count']} van de can xem lai.")
    return {
        **rule,
        "formula": formula,
        "table": table,
        "warnings": warnings,
        "status": "PASS" if not warnings else "REVIEW",
    }


def _flagged_pages(preflight: dict, local_qa: dict, total: int) -> list[int]:
    pages = set()
    for p in preflight.get("pages", []):
        if p.get("text_chars", 0) < 80 or p.get("embedded_images", 0) > 0:
            pages.add(int(p["page"]))
    for section in ("formula", "table"):
        for issue in local_qa.get(section, {}).get("issues", []):
            page = int(issue.get("page", 0) or 0)
            if page > 0:
                pages.add(page)
    if total:
        pages.add(1)
        pages.add(total)
    return sorted(p for p in pages if 1 <= p <= total)


def _qa_score(report: dict) -> tuple[int, int, int, int]:
    return (
        len(report.get("broken_image_references", [])),
        len(report.get("missing_page_markers", [])),
        int(report.get("formula", {}).get("issue_count", 0)),
        int(report.get("table", {}).get("issue_count", 0)),
    )


def process_job(job_id: str, store: JobStore) -> None:
    job = store.read(job_id)
    work_dir = store.job_dir(job_id)
    source_pdf = work_dir / "source.pdf"
    options = job["options"]

    try:
        store.update(job_id, status="running", stage="preflight", progress=4, message="Dang kiem tra PDF goc...")
        preflight = preflight_pdf(source_pdf)
        write_json(work_dir / "preflight.json", preflight)

        store.update(job_id, stage="ocr", progress=9, message="Dang kiem tra nhu cau OCR/deskew/rotate...")
        ocr_report = preprocess_pdf(
            source_pdf=source_pdf,
            work_dir=work_dir,
            preflight=preflight,
            mode=options.get("ocr_mode", "auto"),
            languages=options.get("ocr_languages", "vie+eng"),
            timeout_sec=settings.ocrmypdf_timeout_sec,
        )
        processed_pdf = Path(ocr_report["output_pdf"])
        if ocr_report.get("applied"):
            ocr_report["processed_preflight"] = preflight_pdf(processed_pdf)
        write_json(work_dir / "ocr_report.json", ocr_report)

        store.update(job_id, stage="render", progress=15, message="Dang render tung trang PDF goc lam ban doi chung...")
        page_renders = render_pages(source_pdf, work_dir / "page_renders", int(options.get("render_dpi", settings.default_dpi)))

        extract_dir = work_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        requested_engine = options.get("engine", "auto")
        use_mineru = requested_engine == "mineru" or (requested_engine == "auto" and mineru_available())

        store.update(job_id, stage="extract", progress=25, message="Dang trich xuat Markdown, bang, cong thuc va tai nguyen...")
        if use_mineru:
            try:
                extracted = extract_with_mineru(processed_pdf, extract_dir, tier=options.get("mineru_tier", "standard"), timeout_sec=settings.mineru_timeout_sec)
            except Exception:
                if requested_engine == "mineru":
                    raise
                extracted = extract_with_pymupdf(processed_pdf, extract_dir)
                extracted["fallback_reason"] = "MinerU failed; switched to PyMuPDF4LLM."
        else:
            extracted = extract_with_pymupdf(processed_pdf, extract_dir)

        store.update(job_id, stage="local_qa", progress=55, message="Dang kiem tra coverage, asset, cong thuc va bang...")
        qa_report = _local_qa(extracted, preflight["page_count"])
        qa_report["ocr"] = {
            "applied": ocr_report.get("applied", False),
            "warning": ocr_report.get("warning", ""),
            "languages": ocr_report.get("languages", ""),
        }
        if ocr_report.get("warning") and preflight.get("likely_scanned_pages", 0) > 0:
            qa_report["warnings"].append(ocr_report["warning"])
            qa_report["status"] = "REVIEW"

        gemini_results = []
        if bool(options.get("gemini_qa")):
            if not settings.gemini_api_key:
                qa_report["warnings"].append("Da bat Gemini QA nhung GEMINI_API_KEY dang trong.")
                qa_report["status"] = "REVIEW"
            else:
                total = max(1, preflight["page_count"])
                scope = options.get("gemini_qa_scope", "flagged")
                pages_to_check = list(range(1, total + 1)) if scope == "all" else _flagged_pages(preflight, qa_report, total)
                qa_report["gemini_scope"] = {"mode": scope, "pages": pages_to_check}
                store.update(job_id, stage="gemini_qa", progress=64, message=f"Gemini dang doi chieu {len(pages_to_check)} trang...")
                for pos, page_no in enumerate(pages_to_check, start=1):
                    image_path = page_renders[page_no - 1]
                    candidate_md = _load_page_md(extracted, page_no)
                    if not candidate_md:
                        gemini_results.append({
                            "page": page_no,
                            "status": "REVIEW",
                            "issues": [{
                                "page": page_no,
                                "error_type": "missing_text",
                                "severity": "high",
                                "evidence": "Khong co Markdown theo trang de doi chieu tu dong.",
                                "correction": "Kiem tra parser output hoac chay lai voi PyMuPDF4LLM/OCR.",
                                "original": "",
                                "replacement": "",
                                "confidence": 1.0,
                                "safe_to_apply": False,
                            }],
                        })
                    else:
                        result = qa_page(settings.gemini_api_key, settings.gemini_model, page_no, image_path, candidate_md)
                        page_items = result.get("pages", []) if isinstance(result, dict) else []
                        if page_items:
                            gemini_results.extend(page_items)
                    progress = 64 + int((pos / max(1, len(pages_to_check))) * 17)
                    store.update(job_id, progress=min(progress, 81), message=f"Gemini QA {pos}/{len(pages_to_check)} - trang {page_no}...")

        if gemini_results:
            qa_report["gemini"] = gemini_results
            if any(x.get("status") == "REVIEW" for x in gemini_results):
                qa_report["status"] = "REVIEW"

        if bool(options.get("auto_apply_safe_fixes")) and gemini_results:
            store.update(job_id, stage="safe_autofix", progress=84, message="Dang tao patch an toan + diff + kiem tra rollback...")
            before_local = _local_qa(extracted, preflight["page_count"])
            autofix = apply_patches(
                Path(extracted["document_md"]),
                gemini_results,
                work_dir / "qa",
                float(options.get("safe_fix_min_confidence", 0.985)),
            )
            autofix["rolled_back"] = False
            if autofix.get("changed"):
                after_local = _local_qa(extracted, preflight["page_count"])
                if _qa_score(after_local) > _qa_score(before_local) or after_local.get("markdown_chars", 0) < before_local.get("markdown_chars", 0):
                    rollback(Path(extracted["document_md"]), autofix)
                    autofix["rolled_back"] = True
                    autofix["rollback_reason"] = "QA sau auto-fix xau hon truoc hoac Markdown bi rut ngan bat thuong."
                else:
                    qa_report = after_local | {
                        "ocr": qa_report.get("ocr", {}),
                        "gemini": gemini_results,
                        "gemini_scope": qa_report.get("gemini_scope", {}),
                    }
                    if any(x.get("status") == "REVIEW" for x in gemini_results):
                        qa_report["status"] = "REVIEW"
            qa_report["autofix"] = autofix

        final_md = Path(extracted["document_md"])
        source_hash = sha256_file(source_pdf)
        datapack_dir = None
        datapack_report = None
        if bool(options.get("build_datapack", True)):
            store.update(job_id, stage="datapack", progress=89, message="Dang tao Data Pack theo cau truc chuong/bai/nguon...")
            datapack_dir = work_dir / "datapack"
            datapack_report = build_datapack(
                final_md,
                datapack_dir,
                {
                    "subject": options.get("subject", ""),
                    "grade": options.get("grade", ""),
                    "book_set": options.get("book_set", ""),
                },
                source_hash,
            )

        store.update(job_id, stage="package", progress=94, message="Dang dong goi ZIP V2...")
        manifest = {
            "schema_version": "2.0",
            "app_version": "2.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_filename": job["filename"],
            "source_sha256": source_hash,
            "source_preserved": True,
            "page_count": preflight["page_count"],
            "parser_engine": extracted["engine"],
            "mineru_tier": options.get("mineru_tier") if extracted["engine"] == "mineru" else None,
            "ocr": {
                "mode": options.get("ocr_mode"),
                "applied": ocr_report.get("applied", False),
                "languages": options.get("ocr_languages"),
            },
            "gemini_qa_enabled": bool(options.get("gemini_qa")),
            "gemini_qa_scope": options.get("gemini_qa_scope") if options.get("gemini_qa") else None,
            "gemini_model": settings.gemini_model if options.get("gemini_qa") else None,
            "safe_autofix_enabled": bool(options.get("auto_apply_safe_fixes")),
            "qa_status": qa_report["status"],
            "datapack": datapack_report,
            "traceability": {
                "original_pdf": "00_SOURCE/original.pdf",
                "page_renders": "03_PAGE_RENDER/",
                "qa_report": "05_QA/QA_REPORT.md",
            },
            "notes": [
                "He thong kiem soat page coverage, source preservation va traceability; khong tuyen bo OCR/semantic 100% cho moi tai lieu.",
                "Safe Auto-Fix chi ap dung patch nho, duy nhat, du confidence va se rollback neu QA sau sua xau hon.",
            ],
        }
        zip_path = build_delivery(
            work_dir,
            source_pdf,
            processed_pdf,
            final_md,
            manifest,
            qa_report,
            bool(options.get("preserve_page_renders", True)),
            datapack_dir,
        )
        store.update(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            message="Hoan tat V2. Co the tai ZIP.",
            result_zip=str(zip_path),
            qa_status=qa_report["status"],
            parser_engine=extracted["engine"],
            ocr_applied=ocr_report.get("applied", False),
            datapack_segments=(datapack_report or {}).get("segment_count", 0),
        )
    except Exception as exc:
        (work_dir / "error_trace.txt").write_text(traceback.format_exc(), encoding="utf-8")
        store.update(
            job_id,
            status="failed",
            stage="failed",
            message="Xu ly that bai.",
            error=str(exc),
        )
