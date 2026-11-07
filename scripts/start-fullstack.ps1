param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiHealth = "http://127.0.0.1:$ApiPort/api/v1/health"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"

function Test-Port([int]$Port) {
    $Client = [Net.Sockets.TcpClient]::new()
    try { $Async = $Client.BeginConnect("127.0.0.1", $Port, $null, $null); return $Async.AsyncWaitHandle.WaitOne(500) -and $Client.Connected }
    catch { return $false }
    finally { $Client.Dispose() }
}

function Test-FraudFrontend([string]$Url) {
    try {
        $Response = Invoke-WebRequest -Uri $Url -TimeoutSec 5
        return $Response.StatusCode -eq 200 -and $Response.Content -match "Analyst command center"
    } catch {
        return $false
    }
}

function Start-HiddenScript([string]$ScriptPath, [string]$ScriptArguments = "") {
    $Command = "& '$($ScriptPath.Replace("'", "''"))' $ScriptArguments"
    $Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    $ShellPath = (Get-Process -Id $PID).Path
    Start-Process -FilePath $ShellPath -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $Encoded) -WindowStyle Hidden -PassThru
}

if (-not (Test-Port $ApiPort)) {
    Write-Host "Starting local API on 127.0.0.1:$ApiPort..."
    $ApiScript = Join-Path $ProjectRoot "scripts\start-api.ps1"
    $Args = "-PythonPath '$($PythonPath.Replace("'", "''"))' -HostName '127.0.0.1' -Port $ApiPort"
    $null = Start-HiddenScript $ApiScript $Args
} else {
    try { $null = Invoke-RestMethod -Uri $ApiHealth -TimeoutSec 3 }
    catch { throw "Port $ApiPort is occupied, but the Mission 04 health endpoint did not respond. No duplicate API was started." }
}

$Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ApiReady = $false
while ((Get-Date) -lt $Deadline) {
    try { $Health = Invoke-RestMethod -Uri $ApiHealth -TimeoutSec 3; if ($Health.status -eq "alive") { $ApiReady = $true; break } }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $ApiReady) { throw "Mission 04 API did not become healthy within $TimeoutSeconds seconds." }

if (-not (Test-Port $FrontendPort)) {
    Write-Host "Starting frontend on 127.0.0.1:$FrontendPort..."
    $FrontendScript = Join-Path $ProjectRoot "scripts\start-frontend.ps1"
    $null = Start-HiddenScript $FrontendScript "-Port $FrontendPort -ApiPort $ApiPort"
} else {
    if (-not (Test-FraudFrontend $FrontendUrl)) {
        throw "Port $FrontendPort is occupied by a different or unresponsive application. No duplicate frontend was started."
    }
}

$Deadline = (Get-Date).AddSeconds(120)
$FrontendReady = $false
while ((Get-Date) -lt $Deadline) {
    if (Test-FraudFrontend $FrontendUrl) { $FrontendReady = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $FrontendReady) { throw "Frontend did not become ready within 120 seconds." }
Write-Host "Full stack is ready: $FrontendUrl · $ApiHealth" -ForegroundColor Green
