import re
from pathlib import Path

SEP_CELL = re.compile(r"^:?-{3,}:?$")


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def _validate_markdown_tables(text: str, page: int) -> list[dict]:
    issues = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if "|" not in lines[i] or "|" not in lines[i + 1]:
            i += 1
            continue
        header = _split_row(lines[i])
        sep = _split_row(lines[i + 1])
        if not sep or not all(SEP_CELL.match(c.replace(" ", "")) for c in sep if c):
            i += 1
            continue
        expected = len(header)
        if len(sep) != expected:
            issues.append({"page": page, "type": "table", "severity": "high", "evidence": f"Bang Markdown gan dong {i+1}: header co {expected} cot nhung separator co {len(sep)} cot."})
        j = i + 2
        while j < len(lines) and "|" in lines[j] and lines[j].strip():
            count = len(_split_row(lines[j]))
            if count != expected:
                issues.append({"page": page, "type": "table", "severity": "medium", "evidence": f"Bang Markdown gan dong {j+1}: dong co {count} cot, ky vong {expected}."})
            j += 1
        i = max(j, i + 1)
    return issues


def _validate_html_tables(text: str, page: int) -> list[dict]:
    issues = []
    opens = len(re.findall(r"<table\b", text, re.I))
    closes = len(re.findall(r"</table>", text, re.I))
    if opens != closes:
        issues.append({"page": page, "type": "table", "severity": "high", "evidence": f"HTML table khong dong du: <table>={opens}, </table>={closes}."})
    bad_span = re.findall(r"(?:rowspan|colspan)\s*=\s*[\"']?(-?\d+)", text, re.I)
    for value in bad_span:
        if int(value) <= 0:
            issues.append({"page": page, "type": "table", "severity": "high", "evidence": f"rowspan/colspan khong hop le: {value}."})
    return issues


def validate_table_text(text: str, page: int = 0) -> list[dict]:
    return _validate_markdown_tables(text, page) + _validate_html_tables(text, page)


def run_table_qa(document_md: Path, page_files: list[str | Path] | None = None) -> dict:
    issues = []
    if page_files:
        for idx, path in enumerate(page_files, start=1):
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            issues.extend(validate_table_text(text, idx))
    else:
        text = document_md.read_text(encoding="utf-8", errors="replace")
        issues.extend(validate_table_text(text, 0))
    return {"issues": issues, "issue_count": len(issues), "status": "PASS" if not issues else "REVIEW"}
