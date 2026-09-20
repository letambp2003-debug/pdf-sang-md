$ErrorActionPreference = "Stop"
Write-Host "=== PDF2Markdown Pro V2 - OCRmyPDF setup ==="
Write-Host "1) Cai Tesseract 64-bit bang winget neu chua co..."
if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
  winget install -e --id tesseract-ocr.tesseract
} else {
  Write-Host "Tesseract da co."
}

Write-Host "2) Cai uv neu chua co..."
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  winget install -e --id astral-sh.uv
}

Write-Host "3) Cai OCRmyPDF bang uv tool..."
uv tool install ocrmypdf
Write-Host "Neu ocrmypdf chua vao PATH, dong/mo lai PowerShell hoac chay: uv tool update-shell"

Write-Host "4) Kiem tra language packs..."
tesseract --list-langs
Write-Host "Can co 'vie' va 'eng' neu su dung OCR_LANGUAGES=vie+eng. Neu thieu 'vie', cai them Vietnamese traineddata cho Tesseract."
Write-Host "Ghostscript chi can cho mot so luong chuyen PDF/A; V2 dung --output-type pdf de giam phu thuoc."
