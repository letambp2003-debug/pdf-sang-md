import json
import re
import shutil
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PAGE_RE = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")


def _safe_name(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_-]+", "_", value.strip())
    return value.strip("_") or "section"


def build_datapack(final_md: Path, out_dir: Path, metadata: dict, source_sha256: str) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = out_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    text = final_md.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    current_page = 0
    headings = []
    for line_no, line in enumerate(lines, start=1):
        page_match = PAGE_RE.search(line)
        if page_match:
            current_page = int(page_match.group(1))
        m = HEADING_RE.match(line)
        if m:
            headings.append({
                "line": line_no,
                "level": len(m.group(1)),
                "title": m.group(2).strip(),
                "page": current_page or None,
            })

    boundaries = [0]
    primary_heading_lines = []
    for h in headings:
        if h["level"] <= 2:
            primary_heading_lines.append(h["line"] - 1)
    boundaries += [x for x in primary_heading_lines if x > 0]
    boundaries = sorted(set(boundaries))
    boundaries.append(len(lines))

    segments = []
    for idx in range(len(boundaries) - 1):
        start, end = boundaries[idx], boundaries[idx + 1]
        chunk = "\n".join(lines[start:end]).strip()
        if not chunk:
            continue
        first_heading = next((h for h in headings if start < h["line"] <= end and h["level"] <= 2), None)
        title = first_heading["title"] if first_heading else ("Tai lieu" if idx == 0 else f"Phan {idx+1}")
        page = first_heading.get("page") if first_heading else None
        name = f"{len(segments)+1:03d}_{_safe_name(title)[:70]}.md"
        path = chapters_dir / name
        front = ["---", f'title: "{title.replace(chr(34), chr(39))}"']
        if page:
            front.append(f"source_page: {page}")
        front += [f'source_sha256: "{source_sha256}"', "---", ""]
        path.write_text("\n".join(front) + chunk + "\n", encoding="utf-8")
        segments.append({"index": len(segments) + 1, "title": title, "source_page": page, "file": f"chapters/{name}"})

    master_header = [
        "---",
        f'subject: "{metadata.get("subject", "")}"',
        f'grade: "{metadata.get("grade", "")}"',
        f'book_set: "{metadata.get("book_set", "")}"',
        f'source_sha256: "{source_sha256}"',
        "---",
        "",
    ]
    (out_dir / "DATA_PACK_MASTER.md").write_text("\n".join(master_header) + text, encoding="utf-8")

    index_payload = {
        "schema_version": "2.0",
        "metadata": metadata,
        "source_sha256": source_sha256,
        "headings": headings,
        "segments": segments,
    }
    (out_dir / "DATA_PACK_INDEX.json").write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    index_md = ["# DATA PACK INDEX", ""]
    for key in ("subject", "grade", "book_set"):
        if metadata.get(key):
            index_md.append(f"- {key}: {metadata[key]}")
    index_md += [f"- source_sha256: `{source_sha256}`", "", "## Segments", ""]
    for item in segments:
        suffix = f" - trang {item['source_page']}" if item.get("source_page") else ""
        index_md.append(f"- [{item['title']}]({item['file']}){suffix}")
    (out_dir / "00_INDEX.md").write_text("\n".join(index_md) + "\n", encoding="utf-8")

    return {"heading_count": len(headings), "segment_count": len(segments), "output_dir": str(out_dir)}
