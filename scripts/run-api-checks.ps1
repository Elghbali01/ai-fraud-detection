param([string]$PythonPath = ".venv-isolated\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$env:PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
& $VenvPython -m pytest tests\test_api_unit.py tests\test_api_real_data.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m ruff check --no-cache backend src\fraud_detection\explainability\api_background.py scripts tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m ruff format --check --no-cache backend src\fraud_detection\explainability\api_background.py scripts tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Mission 04 API checks passed."
