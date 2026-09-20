import json
import shutil
import subprocess
import zipfile
from pathlib import Path


def mineru_available() -> bool:
    return shutil.which("mineru-kit") is not None


def _find_one(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        matches = list(root.rglob(name))
        if matches:
            return matches[0]
    return None


def _copy_assets(extracted: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for d in extracted.rglob("images"):
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(d)
                    dst = target / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dst)


def extract_with_mineru(pdf_path: Path, out_root: Path, tier: str = "standard", timeout_sec: int = 14400) -> dict:
    if not mineru_available():
        raise RuntimeError("MinerU chua duoc cai dat hoac mineru-kit khong co trong PATH.")

    raw_dir = out_root / "mineru_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / "mineru_output.zip"

    cmd = [
        "mineru-kit", "parse", str(pdf_path),
        "-o", str(zip_path),
        "--format", "zip",
        "--tier", tier,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0:
        raise RuntimeError(f"MinerU failed: {proc.stderr[-4000:]}")

    extracted = raw_dir / "unpacked"
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extracted)

    md_path = _find_one(extracted, ("markdown.md", f"{pdf_path.stem}.md"))
    if md_path is None:
        md_candidates = list(extracted.rglob("*.md"))
        if not md_candidates:
            raise RuntimeError("Khong tim thay Markdown trong ZIP MinerU.")
        md_path = md_candidates[0]

    target_md = out_root / "document.md"
    shutil.copy2(md_path, target_md)

    assets_dir = out_root / "assets"
    _copy_assets(extracted, assets_dir)

    structured_path = _find_one(extracted, ("structured_content.json",))
    structured = None
    if structured_path and structured_path.exists():
        structured = json.loads(structured_path.read_text(encoding="utf-8"))
        (out_root / "structured_content.json").write_text(
            json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return {
        "engine": "mineru",
        "document_md": target_md,
        "page_files": [],
        "assets_dir": assets_dir,
        "structured_content": structured,
        "raw_dir": raw_dir,
    }
