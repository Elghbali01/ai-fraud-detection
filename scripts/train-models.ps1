param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$DatasetPath = "data\raw\creditcard.csv",
    [string]$OutputDirectory = "reports\ml",
    [string]$ArtifactDirectory = "data\models",
    [int]$RandomState = 17
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Python executable was not found: $PythonCandidate" }

& $VenvPython -m fraud_detection.ml.cli prepare --dataset $DatasetPath --output-directory $OutputDirectory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m fraud_detection.ml.cli run --dataset $DatasetPath --output-directory $OutputDirectory --artifact-directory $ArtifactDirectory --random-state $RandomState --cv-splits 3
exit $LASTEXITCODE
