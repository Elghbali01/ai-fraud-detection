param([int]$Port = 3000, [int]$ApiPort = 8000)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
if (-not (Test-Path -LiteralPath (Join-Path $FrontendRoot "package.json"))) { throw "Frontend package.json is missing." }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Node.js/npm is required. Install Node.js 20.9 or newer." }
if ($Port -lt 1 -or $Port -gt 65535) { throw "Port must be between 1 and 65535." }
if ($ApiPort -lt 1 -or $ApiPort -gt 65535) { throw "API port must be between 1 and 65535." }
$env:NEXT_PUBLIC_FRAUD_API_URL = "http://127.0.0.1:$ApiPort/api/v1"
Set-Location $FrontendRoot
& npm.cmd run dev -- --port $Port
exit $LASTEXITCODE
