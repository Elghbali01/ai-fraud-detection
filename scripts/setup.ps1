param(
    [switch]$OfflineSystemPackages
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "Python 3.11 was not found on PATH. Install Python 3.11 for your user, then retry."
}
$PythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($PythonVersion -ne "3.11") {
    throw "Python 3.11 is required; found Python $PythonVersion."
}

$VenvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path -LiteralPath $VenvPath)) {
    if ($OfflineSystemPackages) {
        & python -m venv --system-site-packages $VenvPath
    } else {
        & python -m venv $VenvPath
    }
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "The local virtual environment is incomplete: $VenvPython"
}
if ($OfflineSystemPackages) {
    & $VenvPython -m pip install --no-index -r requirements-mission04.lock
} else {
    & $VenvPython -m pip install -r requirements-mission04.lock
}
if ($LASTEXITCODE -ne 0) { throw "Installing the Mission 04 resolved dependency set failed." }
& $VenvPython -m pip install --no-build-isolation --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw "Editable project installation failed." }
Write-Output "Environment ready: $VenvPath"
