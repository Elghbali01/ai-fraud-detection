param(
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$NodePath = "node.exe",
    [int]$ApiPort = 8001,
    [int]$FrontendPort = 3100,
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) {
    $PythonPath
} else {
    Join-Path $ProjectRoot $PythonPath
}
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$NodeCommand = if ([IO.Path]::IsPathRooted($NodePath)) {
    $NodePath
} else {
    (Get-Command $NodePath -ErrorAction Stop).Source
}
$NodeExecutable = (Resolve-Path -LiteralPath $NodeCommand).Path
$NextBinary = Join-Path $FrontendRoot "node_modules\next\dist\bin\next"
if (-not (Test-Path -LiteralPath $NextBinary)) {
    throw "Next.js dependencies are missing. Install the locked frontend dependencies first."
}
$FrontendBuildId = Join-Path $FrontendRoot ".next\BUILD_ID"
if (-not (Test-Path -LiteralPath $FrontendBuildId)) {
    throw "The optimized frontend build is missing. Build the frontend before starting the portfolio demo."
}
if ($ApiPort -lt 1 -or $ApiPort -gt 65535 -or $FrontendPort -lt 1 -or $FrontendPort -gt 65535) {
    throw "Ports must be between 1 and 65535."
}
if ($ApiPort -eq $FrontendPort) { throw "API and frontend ports must be different." }

$pythonVersion = & $VenvPython -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0 -or -not $pythonVersion.StartsWith("3.11.")) {
    throw "The project Python environment must use Python 3.11; found '$pythonVersion'."
}
$nodeVersionText = (& $NodeExecutable --version).Trim()
if ($LASTEXITCODE -ne 0 -or $nodeVersionText -notmatch '^v(\d+\.\d+\.\d+)$') {
    throw "Could not read the installed Node.js version."
}
if ([version]$Matches[1] -lt [version]"20.9.0") {
    throw "Node.js 20.9 or newer is required; found $nodeVersionText."
}

function Test-LoopbackPortAvailable([int]$Port) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        $listener.Stop()
    }
}

foreach ($Port in @($ApiPort, $FrontendPort)) {
    if (-not (Test-LoopbackPortAvailable $Port)) {
        throw "Loopback port $Port is already occupied. Choose unused ports; no process was changed."
    }
}

$DatabaseDirectory = Join-Path $ProjectRoot "data\backend"
$UploadDirectory = Join-Path $ProjectRoot "data\uploads\mission06-demo"
New-Item -ItemType Directory -Force -Path $DatabaseDirectory, $UploadDirectory | Out-Null
$DemoDatabase = Join-Path $DatabaseDirectory "mission06-demo.sqlite3"
$ApiUrl = "http://127.0.0.1:$ApiPort/api/v1"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"
$ApiUrlIsBakedIntoBuild = $false
foreach ($chunk in Get-ChildItem (Join-Path $FrontendRoot ".next\static\chunks") -Filter "*.js" -File -Recurse) {
    if ([IO.File]::ReadAllText($chunk.FullName).Contains($ApiUrl)) {
        $ApiUrlIsBakedIntoBuild = $true
        break
    }
}
if (-not $ApiUrlIsBakedIntoBuild) {
    throw "The production frontend bundle is not configured for $ApiUrl. Build it with NEXT_PUBLIC_FRAUD_API_URL set to that API URL first."
}
$stamp = Get-Date -AsUTC -Format "yyyyMMddTHHmmssZ"
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$ApiLog = Join-Path $DatabaseDirectory "mission06-demo-api-$stamp-$suffix.log"
$ApiErrorLog = Join-Path $DatabaseDirectory "mission06-demo-api-$stamp-$suffix.err.log"
$FrontendLog = Join-Path $DatabaseDirectory "mission06-demo-frontend-$stamp-$suffix.log"
$FrontendErrorLog = Join-Path $DatabaseDirectory "mission06-demo-frontend-$stamp-$suffix.err.log"

$overrides = @{
    PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
    FRAUD_API_APP_ENV = "development"
    FRAUD_API_ENABLE_DOCS = "true"
    FRAUD_API_HOST = "127.0.0.1"
    FRAUD_API_PORT = "$ApiPort"
    FRAUD_API_CORS_ORIGINS = "[`"http://127.0.0.1:$FrontendPort`",`"http://localhost:$FrontendPort`"]"
    FRAUD_API_DATABASE_PATH = $DemoDatabase
    FRAUD_API_UPLOAD_DIRECTORY = $UploadDirectory
    NEXT_PUBLIC_FRAUD_API_URL = $ApiUrl
}
$previous = @{}
foreach ($key in $overrides.Keys) {
    $previous[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
}
$apiProcess = $null
$frontendProcess = $null

try {
    foreach ($key in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($key, $overrides[$key], "Process")
    }

    & $VenvPython (Join-Path $ProjectRoot "scripts\verify_api_artifacts.py")
    if ($LASTEXITCODE -ne 0) { throw "Trusted model/API artifacts did not verify." }
    & (Join-Path $ProjectRoot "scripts\init-db.ps1") -PythonPath $VenvPython
    if ($LASTEXITCODE -ne 0) { throw "The dedicated Mission 06 demo database did not reach migration head." }

    $apiArguments = @(
        "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort"
    )
    $apiProcess = Start-Process -FilePath $VenvPython -ArgumentList $apiArguments `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErrorLog

    $quotedNextBinary = '"' + $NextBinary + '"'
    $frontendArguments = @($quotedNextBinary, "start", "--hostname", "127.0.0.1", "--port", "$FrontendPort")
    $frontendProcess = Start-Process -FilePath $NodeExecutable -ArgumentList $frontendArguments `
        -WorkingDirectory $FrontendRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrorLog
} catch {
    foreach ($process in @($frontendProcess, $apiProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
    }
    throw
} finally {
    foreach ($key in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], "Process")
    }
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$apiReady = $false
$frontendReady = $false
while ((Get-Date) -lt $deadline) {
    if ($apiProcess.HasExited) {
        if (-not $frontendProcess.HasExited) {
            Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
        }
        throw "Demo API exited early. Review $ApiErrorLog"
    }
    if ($frontendProcess.HasExited) {
        if (-not $apiProcess.HasExited) {
            Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue
        }
        throw "Demo frontend exited early. Review $FrontendErrorLog"
    }
    if (-not $apiReady) {
        try {
            $ready = Invoke-RestMethod -Uri "$ApiUrl/ready" -TimeoutSec 3
            $apiReady = $ready.status -eq "ready"
        } catch { }
    }
    if (-not $frontendReady) {
        try {
            $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 5
            $frontendReady = $response.StatusCode -eq 200
        } catch { }
    }
    if ($apiReady -and $frontendReady) { break }
    Start-Sleep -Seconds 2
}
if (-not $apiReady -or -not $frontendReady) {
    foreach ($process in @($frontendProcess, $apiProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
    }
    if (-not $apiReady) { throw "Demo API did not become ready. Review $ApiErrorLog" }
    throw "Demo frontend did not become ready. Review $FrontendErrorLog"
}

$apiIdentity = Get-Process -Id $apiProcess.Id -ErrorAction Stop
$frontendIdentity = Get-Process -Id $frontendProcess.Id -ErrorAction Stop
$SessionPath = Join-Path $DatabaseDirectory "mission06-demo-session-$stamp-$suffix.json"
$session = [ordered]@{
    project_root = $ProjectRoot
    api = [ordered]@{
        process_id = $apiIdentity.Id
        executable = $apiIdentity.Path
        started_at_utc = $apiIdentity.StartTime.ToUniversalTime().ToString("o")
    }
    frontend = [ordered]@{
        process_id = $frontendIdentity.Id
        executable = $frontendIdentity.Path
        started_at_utc = $frontendIdentity.StartTime.ToUniversalTime().ToString("o")
    }
}
$session | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $SessionPath -Encoding utf8

Write-Output "Mission 06 demo is ready on loopback."
Write-Output "Dashboard: $FrontendUrl"
Write-Output "API readiness: $ApiUrl/ready"
Write-Output "Persistent demo database: $DemoDatabase (existing records are preserved)."
Write-Output "API process ID: $($apiProcess.Id)"
Write-Output "Frontend process ID: $($frontendProcess.Id)"
Write-Output "Stop both demo processes safely with: scripts\stop-demo.ps1 -SessionPath `"$SessionPath`""
Write-Output "Logs: $ApiLog ; $ApiErrorLog ; $FrontendLog ; $FrontendErrorLog"
