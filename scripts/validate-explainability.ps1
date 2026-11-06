param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [switch]$RealData
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
if ($RealData) {
    $env:RUN_MISSION03_REAL_DATA = "1"
    & $VenvPython -m pytest tests/test_explainability_real_data.py -m mission03_real_data -q
    $Result = $LASTEXITCODE
    Remove-Item Env:RUN_MISSION03_REAL_DATA -ErrorAction SilentlyContinue
    exit $Result
}
& $VenvPython -m pytest tests/test_explainability.py tests/test_risk_intelligence.py -q
exit $LASTEXITCODE
