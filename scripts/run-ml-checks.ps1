param([string]$PythonPath = ".venv-isolated\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $PSScriptRoot "run-checks.ps1") -PythonPath $PythonPath
exit $LASTEXITCODE
