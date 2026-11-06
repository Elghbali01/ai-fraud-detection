param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$ResultsPath = "reports\ml\latest_results.json"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Python executable was not found: $PythonCandidate" }
& $VenvPython -m fraud_detection.ml.cli evaluate --results $ResultsPath
exit $LASTEXITCODE
