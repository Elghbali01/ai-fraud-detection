param([string]$PythonPath = ".venv-isolated\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$env:PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
& $VenvPython -m backend.app.db.initialization
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Mission 04 SQLite schema is at the latest Alembic revision."
