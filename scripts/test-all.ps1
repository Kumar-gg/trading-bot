$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"
$results = @()

function Add-Result($Suite, $Status, $Detail) {
    $script:results += [PSCustomObject]@{ Suite = $Suite; Status = $Status; Detail = $Detail }
}

Write-Host "`n=== Trading Bot test pipeline ===`n" -ForegroundColor Cyan

Push-Location $backend
& $venvPy -m pytest -q --tb=no -m smoke 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Add-Result "backend-smoke" "PASS" "pytest -m smoke" } else { Add-Result "backend-smoke" "FAIL" "exit $LASTEXITCODE" }

& $venvPy -m pytest -q --tb=short 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Add-Result "backend-all" "PASS" "pytest full suite" } else { Add-Result "backend-all" "FAIL" "exit $LASTEXITCODE" }
Pop-Location

Push-Location $frontend
npm run build 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Add-Result "frontend-build" "PASS" "tsc + vite build" } else { Add-Result "frontend-build" "FAIL" "exit $LASTEXITCODE" }

npm run test:unit 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Add-Result "frontend-unit" "PASS" "vitest" } else { Add-Result "frontend-unit" "FAIL" "exit $LASTEXITCODE" }

npm run test:e2e 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Add-Result "frontend-e2e" "PASS" "playwright" } else { Add-Result "frontend-e2e" "FAIL" "exit $LASTEXITCODE" }
Pop-Location

Write-Host "`n=== Summary ===`n" -ForegroundColor Cyan
$results | Format-Table -AutoSize
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
if ($failed -gt 0) {
    Write-Host "FAILED suites: $failed" -ForegroundColor Red
    exit 1
}
Write-Host "All suites passed." -ForegroundColor Green
exit 0
