param(
    [string]$DatasetPath = "data/raw/creditcard.csv"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) { $VenvPython = "python" }

& $VenvPython -m fraud_detection.eda --dataset $DatasetPath --output-dir reports
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
