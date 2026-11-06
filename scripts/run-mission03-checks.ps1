param([string]$PythonPath = ".venv-isolated\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
& (Join-Path $PSScriptRoot "run-checks.ps1") -PythonPath $PythonPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:RUN_MISSION03_REAL_DATA = "1"
& $VenvPython -m pytest tests/test_explainability_real_data.py -m mission03_real_data -q
$Result = $LASTEXITCODE
Remove-Item Env:RUN_MISSION03_REAL_DATA -ErrorAction SilentlyContinue
exit $Result
