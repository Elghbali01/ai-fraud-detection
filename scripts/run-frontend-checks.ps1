$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $NpmCommand) { throw "npm.cmd is unavailable. Install Node.js 20.9 or newer." }
if (-not (Test-Path -LiteralPath (Join-Path $FrontendRoot "node_modules"))) { throw "Frontend dependencies are not installed. Run npm install from frontend first." }
Set-Location $FrontendRoot
foreach ($Task in @("typecheck", "lint", "test", "build")) {
    Write-Host "`n=== Frontend $Task ===" -ForegroundColor Cyan
    & $NpmCommand.Source run $Task
    if ($LASTEXITCODE -ne 0) { throw "Frontend $Task failed with exit code $LASTEXITCODE." }
}
Write-Host "`nFrontend checks completed successfully." -ForegroundColor Green
