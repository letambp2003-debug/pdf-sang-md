import re
from pathlib import Path
import fitz


PAGE_MARKER = "<!-- PAGE: {page} -->"


def _normalize_markdown(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    return md.strip() + "\n"


def _extract_fallback(pdf_path: Path, out_root: Path) -> dict:
    assets_dir = out_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = out_root / "markdown_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    page_files = []
    full_parts = []
    for idx, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        blocks = [text] if text else []
        seen_xrefs = set()
        for img_no, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            data = doc.extract_image(xref)
            ext = data.get("ext", "png")
            asset_name = f"page_{idx:04d}_img_{img_no:02d}.{ext}"
            asset_path = assets_dir / asset_name
            asset_path.write_bytes(data["image"])
            blocks.append(f"![Hinh trang {idx}]({asset_path.as_posix()})")

        body = _normalize_markdown("\n\n".join(blocks) if blocks else "[TRANG KHONG CO TEXT LAYER - CAN OCR/REVIEW]")
        page_md = f"{PAGE_MARKER.format(page=idx)}\n\n{body}"
        page_path = pages_dir / f"page_{idx:04d}.md"
        page_path.write_text(page_md, encoding="utf-8")
        page_files.append(page_path)
        full_parts.append(page_md)

    doc.close()
    full_path = out_root / "document.md"
    full_path.write_text("\n\n".join(full_parts).strip() + "\n", encoding="utf-8")
    return {
        "engine": "pymupdf-fallback",
        "document_md": full_path,
        "page_files": page_files,
        "assets_dir": assets_dir,
    }


def extract_with_pymupdf(pdf_path: Path, out_root: Path) -> dict:
    try:
        import pymupdf4llm
    except ImportError:
        return _extract_fallback(pdf_path, out_root)

    assets_dir = out_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    chunks = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        write_images=True,
        image_path=str(assets_dir),
        image_format="png",
        dpi=180,
    )

    pages_dir = out_root / "markdown_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_files = []
    full_parts = []
    for idx, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        text = _normalize_markdown(text)
        page_md = f"{PAGE_MARKER.format(page=idx)}\n\n{text}"
        page_path = pages_dir / f"page_{idx:04d}.md"
        page_path.write_text(page_md, encoding="utf-8")
        page_files.append(page_path)
        full_parts.append(page_md)

    full_path = out_root / "document.md"
    full_path.write_text("\n\n".join(full_parts).strip() + "\n", encoding="utf-8")
    return {
        "engine": "pymupdf4llm",
        "document_md": full_path,
        "page_files": page_files,
        "assets_dir": assets_dir,
    }
