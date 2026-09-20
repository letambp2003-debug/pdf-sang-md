$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
Write-Host "Mo trinh duyet tai http://127.0.0.1:8765"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
