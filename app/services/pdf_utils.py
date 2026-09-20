import hashlib
import json
from pathlib import Path
import fitz


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight_pdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    text_pages = 0
    image_count = 0
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        images = page.get_images(full=True)
        if text:
            text_pages += 1
        image_count += len(images)
        pages.append({
            "page": i + 1,
            "width_pt": round(page.rect.width, 2),
            "height_pt": round(page.rect.height, 2),
            "text_chars": len(text),
            "embedded_images": len(images),
        })
    result = {
        "page_count": len(doc),
        "text_pages": text_pages,
        "likely_scanned_pages": len(doc) - text_pages,
        "embedded_image_occurrences": image_count,
        "pages": pages,
    }
    doc.close()
    return result


def render_pages(pdf_path: Path, out_dir: Path, dpi: int = 220) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    outputs = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out = out_dir / f"page_{i+1:04d}.png"
        pix.save(out)
        outputs.append(out)
    doc.close()
    return outputs


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
