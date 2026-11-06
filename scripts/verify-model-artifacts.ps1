param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$ManifestPath = "reports\ml\artifact_manifest.json",
    [string]$AnomalyManifestPath = "reports\ml\anomaly_artifact_manifest.json"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Python executable was not found: $PythonCandidate" }
& $VenvPython -m fraud_detection.ml.cli verify-artifact --manifest $ManifestPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m fraud_detection.ml.cli verify-artifact --manifest $AnomalyManifestPath
exit $LASTEXITCODE
