import re
from pathlib import Path


IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
PAGE_RE = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")


def run_rule_qa(document_md: Path, expected_pages: int, assets_root: Path) -> dict:
    text = document_md.read_text(encoding="utf-8", errors="replace")
    page_markers = [int(x) for x in PAGE_RE.findall(text)]
    image_refs = IMAGE_RE.findall(text)
    broken_images = []
    remote_images = []

    for ref in image_refs:
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if clean.startswith(("http://", "https://", "data:")):
            remote_images.append(ref)
            continue
        candidates = [
            document_md.parent / clean,
            assets_root / Path(clean).name,
        ]
        if not any(p.exists() for p in candidates):
            broken_images.append(ref)

    missing_markers = []
    duplicate_markers = []
    if page_markers:
        seen = set()
        for p in page_markers:
            if p in seen:
                duplicate_markers.append(p)
            seen.add(p)
        missing_markers = sorted(set(range(1, expected_pages + 1)) - set(page_markers))

    warnings = []
    if page_markers and len(set(page_markers)) != expected_pages:
        warnings.append("So marker trang Markdown khong khop so trang PDF.")
    if broken_images:
        warnings.append("Co lien ket anh cuc bo bi hong.")
    if "[TRANG KHONG CO TEXT LAYER - CAN OCR/REVIEW]" in text:
        warnings.append("Co trang khong co text layer; can OCR hoac kiem tra thu cong.")

    return {
        "expected_pages": expected_pages,
        "page_markers_found": len(page_markers),
        "missing_page_markers": missing_markers,
        "duplicate_page_markers": duplicate_markers,
        "image_references": len(image_refs),
        "broken_image_references": broken_images,
        "remote_image_references": remote_images,
        "markdown_chars": len(text),
        "warnings": warnings,
        "status": "PASS" if not warnings else "REVIEW",
    }
