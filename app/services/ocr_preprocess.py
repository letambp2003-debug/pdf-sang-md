import shutil
import subprocess
from pathlib import Path


def ocrmypdf_available() -> bool:
    return shutil.which("ocrmypdf") is not None


def should_ocr(preflight: dict) -> bool:
    pages = max(1, int(preflight.get("page_count", 0)))
    scanned = int(preflight.get("likely_scanned_pages", 0))
    return scanned > 0 and (scanned / pages >= 0.01)


def preprocess_pdf(
    source_pdf: Path,
    work_dir: Path,
    preflight: dict,
    mode: str = "auto",
    languages: str = "vie+eng",
    timeout_sec: int = 7200,
) -> dict:
    report = {
        "requested_mode": mode,
        "languages": languages,
        "available": ocrmypdf_available(),
        "applied": False,
        "input_pdf": str(source_pdf),
        "output_pdf": str(source_pdf),
        "warning": "",
        "command": [],
    }
    if mode == "off":
        return report
    if mode == "auto" and not should_ocr(preflight):
        report["warning"] = "OCR khong can thiet theo preflight: tat ca hoac gan tat ca trang da co text layer."
        return report
    if not report["available"]:
        report["warning"] = "OCRmyPDF chua co trong PATH; tiep tuc voi PDF goc va danh dau QA neu co trang scan."
        return report

    out_pdf = work_dir / "ocr_processed.pdf"
    cmd = [
        "ocrmypdf",
        "--rotate-pages",
        "--deskew",
        "--optimize", "1",
        "--output-type", "pdf",
        "-l", languages,
    ]
    if mode == "force":
        cmd.append("--force-ocr")
    else:
        cmd.append("--skip-text")
    cmd.extend([str(source_pdf), str(out_pdf)])
    report["command"] = cmd

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    report["returncode"] = proc.returncode
    report["stdout_tail"] = proc.stdout[-4000:]
    report["stderr_tail"] = proc.stderr[-4000:]
    if proc.returncode != 0 or not out_pdf.exists():
        report["warning"] = "OCRmyPDF that bai; tiep tuc voi PDF goc."
        return report

    report["applied"] = True
    report["output_pdf"] = str(out_pdf)
    return report
