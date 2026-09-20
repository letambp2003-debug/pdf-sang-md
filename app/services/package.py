import json
import re
import shutil
import zipfile
from pathlib import Path


IMAGE_RE = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for p in src.rglob("*"):
        if p.is_file():
            target = dst / p.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def _portable_markdown(source_md: Path, target_md: Path, assets_source: Path) -> None:
    text = source_md.read_text(encoding="utf-8", errors="replace")
    asset_names = {p.name for p in assets_source.rglob("*") if p.is_file()} if assets_source.exists() else set()

    def repl(match: re.Match) -> str:
        ref = match.group(2).strip().strip("<>")
        if ref.startswith(("http://", "https://", "data:")):
            return match.group(0)
        name = Path(ref.replace("\\", "/")).name
        if name in asset_names:
            return f"{match.group(1)}../02_ASSETS/{name}{match.group(3)}"
        return match.group(0)

    target_md.parent.mkdir(parents=True, exist_ok=True)
    target_md.write_text(IMAGE_RE.sub(repl, text), encoding="utf-8")


def build_delivery(
    work_dir: Path,
    source_pdf: Path,
    processed_pdf: Path,
    final_md: Path,
    manifest: dict,
    qa_report: dict,
    preserve_renders: bool,
    datapack_dir: Path | None = None,
) -> Path:
    delivery = work_dir / "delivery"
    if delivery.exists():
        shutil.rmtree(delivery)
    delivery.mkdir(parents=True)

    source_dir = delivery / "00_SOURCE"
    md_dir = delivery / "01_MARKDOWN"
    assets_dir = delivery / "02_ASSETS"
    renders_dir = delivery / "03_PAGE_RENDER"
    structured_dir = delivery / "04_STRUCTURED"
    qa_dir = delivery / "05_QA"
    datapack_target = delivery / "06_DATA_PACK"
    for d in (source_dir, md_dir, assets_dir, structured_dir, qa_dir):
        d.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_pdf, source_dir / "original.pdf")
    if processed_pdf.resolve() != source_pdf.resolve() and processed_pdf.exists():
        shutil.copy2(processed_pdf, source_dir / "ocr_processed.pdf")

    copy_tree(work_dir / "extract" / "assets", assets_dir)
    _portable_markdown(final_md, md_dir / "document.md", work_dir / "extract" / "assets")

    if (work_dir / "extract" / "structured_content.json").exists():
        shutil.copy2(work_dir / "extract" / "structured_content.json", structured_dir / "structured_content.json")
    if (work_dir / "preflight.json").exists():
        shutil.copy2(work_dir / "preflight.json", structured_dir / "preflight.json")
    if (work_dir / "ocr_report.json").exists():
        shutil.copy2(work_dir / "ocr_report.json", structured_dir / "ocr_report.json")
    if preserve_renders:
        copy_tree(work_dir / "page_renders", renders_dir)

    (delivery / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (qa_dir / "qa_report.json").write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    copy_tree(work_dir / "qa", qa_dir / "artifacts")

    qa_md = ["# QA REPORT", "", f"- Status: **{qa_report.get('status', 'UNKNOWN')}**"]
    for warning in qa_report.get("warnings", []):
        qa_md.append(f"- Canh bao: {warning}")
    for section_name in ("formula", "table"):
        section = qa_report.get(section_name, {})
        if section.get("issues"):
            qa_md.extend(["", f"## {section_name.title()} QA", ""])
            for issue in section["issues"]:
                qa_md.append(f"- Trang {issue.get('page')}: {issue.get('severity')} - {issue.get('evidence')}")
    gemini = qa_report.get("gemini")
    if gemini:
        qa_md.extend(["", "## Gemini QA", ""])
        for item in gemini:
            qa_md.append(f"- Trang {item.get('page')}: {item.get('status')}")
            for issue in item.get("issues", []):
                qa_md.append(f"  - {issue.get('severity')}: {issue.get('error_type')} - {issue.get('evidence')}")
    autofix = qa_report.get("autofix")
    if autofix:
        qa_md.extend(["", "## Safe Auto-Fix", "", f"- Applied: {autofix.get('applied_count', 0)}", f"- Rejected: {autofix.get('rejected_count', 0)}", f"- Rolled back: {autofix.get('rolled_back', False)}"])
    (qa_dir / "QA_REPORT.md").write_text("\n".join(qa_md) + "\n", encoding="utf-8")

    if datapack_dir and datapack_dir.exists():
        copy_tree(datapack_dir, datapack_target)

    zip_path = work_dir / "PDF2Markdown_Pro_V2_Result.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in delivery.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(delivery))
    return zip_path
