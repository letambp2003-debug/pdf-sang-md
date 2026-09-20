#!/usr/bin/env python3
"""Validate the structural integrity of a PDF2Markdown Pro result ZIP."""
from __future__ import annotations
import argparse, hashlib, json, re, sys, zipfile
from pathlib import PurePosixPath

REQUIRED_FILES = {
    "00_SOURCE/original.pdf",
    "01_MARKDOWN/document.md",
    "05_QA/QA_REPORT.md",
    "05_QA/qa_report.json",
    "MANIFEST.json",
}
REQUIRED_DIR_PREFIXES = ("02_ASSETS/", "04_STRUCTURED/", "05_QA/")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
PAGE_RE = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->", re.I)


def norm_link(link: str) -> str:
    link = link.split("#", 1)[0].split("?", 1)[0].strip().replace("\\", "/")
    base = PurePosixPath("01_MARKDOWN") / link
    parts = []
    for p in base.parts:
        if p in ("", "."):
            continue
        if p == "..":
            if parts:
                parts.pop()
        else:
            parts.append(p)
    return "/".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    args = ap.parse_args()
    issues: list[str] = []

    try:
        zf = zipfile.ZipFile(args.zip_path)
    except Exception as exc:
        print(f"FAILED: cannot open ZIP: {exc}")
        return 2

    names = set(zf.namelist())
    missing = sorted(REQUIRED_FILES - names)
    if missing:
        issues.append("missing required files: " + ", ".join(missing))
    for prefix in REQUIRED_DIR_PREFIXES:
        if not any(n.startswith(prefix) for n in names):
            issues.append(f"missing required area: {prefix}")

    manifest = {}
    if "MANIFEST.json" in names:
        try:
            manifest = json.loads(zf.read("MANIFEST.json"))
        except Exception as exc:
            issues.append(f"invalid MANIFEST.json: {exc}")

    if manifest and manifest.get("source_preserved") is False:
        issues.append("manifest says source_preserved=false")

    if "00_SOURCE/original.pdf" in names and manifest:
        expected = manifest.get("source_sha256") or manifest.get("sha256")
        if expected:
            actual = hashlib.sha256(zf.read("00_SOURCE/original.pdf")).hexdigest()
            if str(expected).lower() != actual.lower():
                issues.append("source SHA-256 mismatch")

    if "01_MARKDOWN/document.md" in names:
        md = zf.read("01_MARKDOWN/document.md").decode("utf-8", "replace")
        for link in IMG_RE.findall(md):
            if re.match(r"^[a-z]+://", link, re.I) or link.startswith("data:"):
                continue
            target = norm_link(link)
            if target not in names:
                issues.append(f"broken image link: {link} -> {target}")
        pages = [int(x) for x in PAGE_RE.findall(md)]
        if pages:
            unique = sorted(set(pages))
            if unique[0] != 1:
                issues.append(f"page markers start at {unique[0]}, expected 1")
            gaps = [n for n in range(unique[0], unique[-1] + 1) if n not in set(unique)]
            if gaps:
                issues.append("missing page markers: " + ", ".join(map(str, gaps[:30])))
            page_count = manifest.get("page_count") if manifest else None
            if isinstance(page_count, int) and unique[-1] != page_count:
                issues.append(f"last page marker {unique[-1]} != manifest page_count {page_count}")

    if "05_QA/qa_report.json" in names:
        try:
            json.loads(zf.read("05_QA/qa_report.json"))
        except Exception as exc:
            issues.append(f"invalid qa_report.json: {exc}")

    if issues:
        print("REVIEW")
        for item in issues:
            print("- " + item)
        return 1
    print("PASS")
    print(f"- files: {len(names)}")
    print(f"- qa_status: {manifest.get('qa_status', 'UNKNOWN') if manifest else 'UNKNOWN'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
