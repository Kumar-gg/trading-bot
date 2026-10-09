$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

function Get-NpmCmd {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $fallback = Join-Path ${env:ProgramFiles} "nodejs\npm.cmd"
    if (Test-Path $fallback) { return $fallback }
    throw "npm.cmd not found. Install Node.js from https://nodejs.org/"
}

Write-Host "Starting Trading Bot (API :8000, UI :5173)..."

Push-Location $backend
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
    & (Join-Path $backend ".venv\Scripts\pip.exe") install -e ".[dev]"
}
$api = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
    -PassThru -WorkingDirectory $backend
Pop-Location

Push-Location $frontend
if (-not (Test-Path "node_modules")) { & (Get-NpmCmd) install }
$npmCmd = Get-NpmCmd
$ui = Start-Process -FilePath $npmCmd `
    -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" `
    -PassThru -WorkingDirectory $frontend
Pop-Location

Write-Host "API PID $($api.Id) · UI PID $($ui.Id)"
Write-Host "Waiting for API on :8000..."
$apiOk = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $apiOk = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $apiOk) {
    Write-Host "ERROR: API did not start. Check the uvicorn window for errors (often Binance/network)." -ForegroundColor Red
} else {
    Write-Host "API is up."
}
Write-Host "Waiting for UI..."
Start-Sleep -Seconds 3
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Host "UI is up. Opening browser..."
    Start-Process "http://127.0.0.1:5173"
} catch {
    Write-Host "UI not ready yet. Open manually: http://127.0.0.1:5173"
    Write-Host "If the UI window closed, check the Vite console for errors."
}
