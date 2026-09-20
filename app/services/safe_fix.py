import difflib
import json
import shutil
from pathlib import Path

ALLOWED_TYPES = {"wrong_text", "formula", "caption", "heading"}


def collect_safe_patches(gemini_results: list[dict], markdown_text: str, min_confidence: float) -> tuple[list[dict], list[dict]]:
    accepted = []
    rejected = []
    for page in gemini_results:
        for issue in page.get("issues", []):
            original = (issue.get("original") or "").strip()
            replacement = (issue.get("replacement") or issue.get("correction") or "").strip()
            record = {
                "page": issue.get("page", page.get("page", 0)),
                "error_type": issue.get("error_type"),
                "confidence": float(issue.get("confidence", 0)),
                "original": original,
                "replacement": replacement,
            }
            reason = ""
            if not issue.get("safe_to_apply", False):
                reason = "AI khong danh dau safe_to_apply."
            elif record["error_type"] not in ALLOWED_TYPES:
                reason = "Loai loi khong duoc phep auto-fix."
            elif record["confidence"] < min_confidence:
                reason = "Confidence thap hon nguong."
            elif not original or not replacement or original == replacement:
                reason = "Thieu original/replacement hoac khong co thay doi."
            elif len(original) > 1500 or len(replacement) > max(3000, len(original) * 4):
                reason = "Patch qua lon."
            elif markdown_text.count(original) != 1:
                reason = f"Original khong duy nhat trong Markdown (count={markdown_text.count(original)})."
            if reason:
                record["reason"] = reason
                rejected.append(record)
            else:
                accepted.append(record)
    return accepted, rejected


def apply_patches(document_md: Path, gemini_results: list[dict], qa_dir: Path, min_confidence: float) -> dict:
    qa_dir.mkdir(parents=True, exist_ok=True)
    before = document_md.read_text(encoding="utf-8", errors="replace")
    patches, rejected = collect_safe_patches(gemini_results, before, min_confidence)
    after = before
    applied = []
    for patch in patches:
        if after.count(patch["original"]) != 1:
            patch = dict(patch)
            patch["reason"] = "Original khong con duy nhat sau patch truoc."
            rejected.append(patch)
            continue
        after = after.replace(patch["original"], patch["replacement"], 1)
        applied.append(patch)

    before_path = qa_dir / "before_autofix.md"
    after_path = qa_dir / "after_autofix.md"
    diff_path = qa_dir / "autofix.diff"
    before_path.write_text(before, encoding="utf-8")
    after_path.write_text(after, encoding="utf-8")
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="before_autofix.md", tofile="after_autofix.md"))
    diff_path.write_text(diff, encoding="utf-8")
    (qa_dir / "autofix_patches.json").write_text(json.dumps({"applied": applied, "rejected": rejected}, ensure_ascii=False, indent=2), encoding="utf-8")

    if applied:
        shutil.copy2(document_md, qa_dir / "document_pre_autofix.md")
        document_md.write_text(after, encoding="utf-8")

    return {
        "attempted": len(patches) + len(rejected),
        "applied_count": len(applied),
        "rejected_count": len(rejected),
        "applied": applied,
        "rejected": rejected,
        "changed": bool(applied),
        "backup": str(qa_dir / "document_pre_autofix.md") if applied else "",
        "diff": str(diff_path),
    }


def rollback(document_md: Path, autofix_report: dict) -> bool:
    backup = autofix_report.get("backup")
    if not backup:
        return False
    backup_path = Path(backup)
    if not backup_path.exists():
        return False
    shutil.copy2(backup_path, document_md)
    return True
