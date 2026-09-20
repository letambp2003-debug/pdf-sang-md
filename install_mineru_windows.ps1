$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip uv
uv pip install -U "mineru>=4.0,<5"
mineru version --json
Write-Host "MinerU da duoc cai. Lan parse dau tien co the tai model weights."
