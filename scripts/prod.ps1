$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

Write-Host "Production API only (no --reload, no Vite). Data: backend\data\" -ForegroundColor Cyan

Push-Location $backend
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
    & (Join-Path $backend ".venv\Scripts\pip.exe") install -e .
}
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
$env:TB_DATABASE_URL = if ($env:TB_DATABASE_URL) { $env:TB_DATABASE_URL } else { "sqlite+aiosqlite:///./data/trading_bot.db" }

& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
