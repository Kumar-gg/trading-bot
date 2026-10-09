param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$paths = @(
    "/api/health",
    "/api/bots",
    "/api/strategies",
    "/api/journal?limit=5",
    "/api/decisions?limit=5"
)

foreach ($p in $paths) {
    $uri = "$BaseUrl$p"
    try {
        $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
        Write-Host "OK   $p"
    } catch {
        Write-Error "FAIL $p $_"
        exit 1
    }
}

Write-Host "All checks passed against $BaseUrl"
