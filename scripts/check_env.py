import os
import shutil
import sys
from pathlib import Path

print("PDF2Markdown Pro V2 - Environment check")
print("Python:", sys.version.split()[0])
for cmd in ("mineru-kit", "ocrmypdf", "tesseract"):
    print(f"{cmd}:", shutil.which(cmd) or "NOT FOUND")
print("GEMINI_API_KEY:", "SET" if os.getenv("GEMINI_API_KEY") else "NOT SET (or load through .env at app runtime)")
print("cwd:", Path.cwd())
