param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"
$ApiBaseUrl = "http://127.0.0.1:$ApiPort/api/v1"
& (Join-Path $PSScriptRoot "start-fullstack.ps1") -PythonPath $PythonPath -ApiPort $ApiPort -FrontendPort $FrontendPort

$Health = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/v1/health" -TimeoutSec 10
$Ready = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/v1/ready" -TimeoutSec 10
$Frontend = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 10
if ($Health.status -ne "alive" -or $Ready.status -ne "ready" -or $Frontend.StatusCode -ne 200 -or $Frontend.Content -notmatch "Analyst command center") {
    throw "A full-stack health, readiness, or frontend HTTP check failed."
}
Write-Host "API health: $($Health.status) · readiness: $($Ready.status) · frontend HTTP: $($Frontend.StatusCode)"

if (-not $SkipBrowser) {
    $NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $NpmCommand) { throw "npm.cmd is unavailable for browser E2E." }
    Set-Location $FrontendRoot
    $PreviousBaseUrl = $env:PLAYWRIGHT_BASE_URL
    $PreviousApiBaseUrl = $env:PLAYWRIGHT_API_BASE_URL
    $PreviousReuse = $env:PLAYWRIGHT_REUSE_SERVER
    try {
        $env:PLAYWRIGHT_BASE_URL = $FrontendUrl
        $env:PLAYWRIGHT_API_BASE_URL = $ApiBaseUrl
        $env:PLAYWRIGHT_REUSE_SERVER = "1"
        & $NpmCommand.Source run test:e2e -- --workers=1
        if ($LASTEXITCODE -ne 0) { throw "Browser E2E failed with exit code $LASTEXITCODE." }
    } finally {
        if ($null -eq $PreviousBaseUrl) { Remove-Item Env:PLAYWRIGHT_BASE_URL -ErrorAction SilentlyContinue } else { $env:PLAYWRIGHT_BASE_URL = $PreviousBaseUrl }
        if ($null -eq $PreviousApiBaseUrl) { Remove-Item Env:PLAYWRIGHT_API_BASE_URL -ErrorAction SilentlyContinue } else { $env:PLAYWRIGHT_API_BASE_URL = $PreviousApiBaseUrl }
        if ($null -eq $PreviousReuse) { Remove-Item Env:PLAYWRIGHT_REUSE_SERVER -ErrorAction SilentlyContinue } else { $env:PLAYWRIGHT_REUSE_SERVER = $PreviousReuse }
    }
}
