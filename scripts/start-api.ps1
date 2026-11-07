param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$HostName = "",
    [int]$Port = 0,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$env:PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
if (-not $HostName -or $Port -eq 0) {
    $Configured = & $VenvPython -c "from backend.app.core.config import Settings; s=Settings(); print(s.host + '|' + str(s.port))"
    if ($LASTEXITCODE -ne 0) { throw "API configuration could not be loaded safely." }
    $ConfiguredHost, $ConfiguredPort = $Configured.Trim().Split('|', 2)
    if (-not $HostName) { $HostName = $ConfiguredHost }
    if ($Port -eq 0) { $Port = [int]$ConfiguredPort }
}
if ($HostName -eq "localhost") { $HostName = "127.0.0.1" }
$Address = $null
if (-not [Net.IPAddress]::TryParse($HostName, [ref]$Address) -or -not [Net.IPAddress]::IsLoopback($Address)) {
    throw "The API start script only binds to localhost or a loopback IP address."
}
if ($Port -lt 1 -or $Port -gt 65535) { throw "Port must be between 1 and 65535." }
& (Join-Path $ProjectRoot "scripts\init-db.ps1") -PythonPath $VenvPython
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$UvicornArgs = @("-m", "uvicorn", "backend.app.main:app", "--host", $HostName, "--port", "$Port")
if ($Reload) { $UvicornArgs += "--reload" }
& $VenvPython @UvicornArgs
exit $LASTEXITCODE
