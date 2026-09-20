import re
from pathlib import Path

DISPLAY_MATH = re.compile(r"\$\$(.*?)\$\$", re.S)
INLINE_MATH = re.compile(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", re.S)
LATEX_ENV = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|cases|matrix|pmatrix|bmatrix)\}(.*?)\\end\{\1\}", re.S)


def _brace_balance(text: str) -> int:
    level = 0
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "{":
            level += 1
        elif ch == "}":
            level -= 1
            if level < 0:
                return level
    return level


def validate_formula_text(text: str, page: int = 0) -> list[dict]:
    issues = []
    if text.count("$$") % 2:
        issues.append({"page": page, "type": "formula", "severity": "high", "evidence": "So delimiter $$ khong can bang."})

    stripped = text.replace("$$", "")
    single_dollars = len(re.findall(r"(?<!\\)\$", stripped))
    if single_dollars % 2:
        issues.append({"page": page, "type": "formula", "severity": "medium", "evidence": "So delimiter $ inline khong can bang."})

    blocks = [m.group(1) for m in DISPLAY_MATH.finditer(text)]
    blocks += [m.group(1) for m in INLINE_MATH.finditer(text)]
    blocks += [m.group(2) for m in LATEX_ENV.finditer(text)]
    for idx, block in enumerate(blocks, start=1):
        bal = _brace_balance(block)
        if bal != 0:
            issues.append({"page": page, "type": "formula", "severity": "high", "evidence": f"Khoi cong thuc {idx} lech dau ngoac nhon, balance={bal}."})
        if re.search(r"\\frac(?!\s*\{)", block):
            issues.append({"page": page, "type": "formula", "severity": "medium", "evidence": f"Khoi cong thuc {idx} co \\frac khong theo sau boi '{{'."})
        if "[TRANG KHONG CO TEXT LAYER" in block:
            issues.append({"page": page, "type": "formula", "severity": "high", "evidence": "Cong thuc nam tren trang khong co text layer."})
    return issues


def run_formula_qa(document_md: Path, page_files: list[str | Path] | None = None) -> dict:
    issues = []
    if page_files:
        for idx, path in enumerate(page_files, start=1):
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            issues.extend(validate_formula_text(text, idx))
    else:
        text = document_md.read_text(encoding="utf-8", errors="replace")
        issues.extend(validate_formula_text(text, 0))
    return {
        "issues": issues,
        "issue_count": len(issues),
        "status": "PASS" if not issues else "REVIEW",
    }
