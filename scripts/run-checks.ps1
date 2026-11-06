param([string]$PythonPath)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) {
        $PythonPath
    } else {
        Join-Path $ProjectRoot $PythonPath
    }
    $VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
} else {
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        $PythonCommand = Get-Command python -ErrorAction Stop
        $VenvPython = $PythonCommand.Source
    }
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Python executable was not found: $VenvPython"
}

& $VenvPython -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m ruff check --no-cache .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m ruff format --check --no-cache .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m compileall -q src scripts tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython scripts\validate_notebooks.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m fraud_detection.eda --synthetic-demo --output-dir reports
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
