param(
    [string]$PythonPath = "",
    [string]$NodePath = "node.exe",
    [int]$ApiPort = 8001,
    [int]$FrontendPort = 3100,
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$DatabaseDirectory = Join-Path $ProjectRoot "data\backend"
$UploadDirectory = Join-Path $ProjectRoot "data\uploads\mission06-demo"
$LogDirectory = Join-Path $DatabaseDirectory "mission06-demo-logs"
New-Item -ItemType Directory -Force -Path $DatabaseDirectory, $UploadDirectory, $LogDirectory | Out-Null

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonCandidates = @(
        (Join-Path $ProjectRoot ".venv-isolated\Scripts\python.exe"),
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
    )
    $PythonCandidate = $PythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $PythonCandidate) {
        throw "No project virtual environment was found. Run the setup instructions in README.md first."
    }
} elseif ([IO.Path]::IsPathRooted($PythonPath)) {
    $PythonCandidate = $PythonPath
} else {
    $PythonCandidate = Join-Path $ProjectRoot $PythonPath
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

function Get-ProcessExecutablePath([object]$Process) {
    $processPath = [string]$Process.Path
    if ([string]::IsNullOrWhiteSpace($processPath)) {
        try { $processPath = [string]$Process.MainModule.FileName } catch { }
    }
    if ([string]::IsNullOrWhiteSpace($processPath)) {
        try {
            $processDetails = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($Process.Id)" -ErrorAction Stop
            $processPath = [string]$processDetails.ExecutablePath
        } catch { }
    }
    if ([string]::IsNullOrWhiteSpace($processPath)) {
        throw "The executable path for PID $($Process.Id) is unavailable."
    }
    return (Resolve-Path -LiteralPath $processPath -ErrorAction Stop).Path
}

function Stop-OwnedStartedProcess([object]$StartedProcess, [string]$ExpectedExecutable, [long]$ExpectedStartTicks) {
    if ($null -eq $StartedProcess) { return }
    $current = Get-Process -Id $StartedProcess.Id -ErrorAction SilentlyContinue
    if ($null -eq $current) { return }
    if ($ExpectedStartTicks -le 0) {
        throw "Refusing to stop PID $($StartedProcess.Id) without a captured start time."
    }
    try {
        $actualPath = Get-ProcessExecutablePath -Process $current
        $expectedPath = (Resolve-Path -LiteralPath $ExpectedExecutable).Path
        $actualStartTicks = $current.StartTime.ToUniversalTime().Ticks
    } catch {
        throw "Could not verify PID $($StartedProcess.Id); it was not stopped."
    }
    if (
        -not $actualPath.Equals($expectedPath, [StringComparison]::OrdinalIgnoreCase) -or
        $actualStartTicks -ne $ExpectedStartTicks
    ) {
        throw "PID $($StartedProcess.Id) no longer matches the launched process; it was not stopped."
    }
    $current.Kill()
    if (-not $current.WaitForExit(10000)) {
        throw "Owned PID $($StartedProcess.Id) did not stop within 10 seconds."
    }
}

foreach ($Port in @($ApiPort, $FrontendPort)) {
    if (-not (Test-LoopbackPortAvailable $Port)) {
        throw "Loopback port $Port is already occupied. Choose unused ports; no process was changed."
    }
}

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
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$ApiLog = Join-Path $LogDirectory "mission06-demo-api-$stamp-$suffix.log"
$ApiErrorLog = Join-Path $LogDirectory "mission06-demo-api-$stamp-$suffix.err.log"
$FrontendLog = Join-Path $LogDirectory "mission06-demo-frontend-$stamp-$suffix.log"
$FrontendErrorLog = Join-Path $LogDirectory "mission06-demo-frontend-$stamp-$suffix.err.log"

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
$apiIdentity = $null
$frontendIdentity = $null
$apiStartTicks = 0L
$frontendStartTicks = 0L

try {
    foreach ($key in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($key, $overrides[$key], "Process")
    }

    Write-Output "[2/5] Verifying model artifacts..."
    & $VenvPython (Join-Path $ProjectRoot "scripts\verify_api_artifacts.py")
    if ($LASTEXITCODE -ne 0) { throw "Trusted model/API artifacts did not verify." }
    & $VenvPython -m backend.app.db.initialization
    if ($LASTEXITCODE -ne 0) { throw "The dedicated Mission 06 demo database did not reach migration head." }

    Write-Output "[3/5] Starting FastAPI on 127.0.0.1:$ApiPort and waiting for readiness..."
    $apiArguments = @(
        "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort"
    )
    $apiProcess = Start-Process -FilePath $VenvPython -ArgumentList $apiArguments `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErrorLog
    $apiIdentity = Get-Process -Id $apiProcess.Id -ErrorAction Stop
    $apiStartTicks = $apiIdentity.StartTime.ToUniversalTime().Ticks
    $apiExecutablePath = Get-ProcessExecutablePath -Process $apiIdentity
    if (-not $apiExecutablePath.Equals($VenvPython, [StringComparison]::OrdinalIgnoreCase)) {
        throw "FastAPI started from an unexpected executable path. Review $ApiErrorLog"
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $apiReady = $false
    $databaseReady = $false
    $modelReady = $false
    $modelVersion = ""
    while ((Get-Date) -lt $deadline) {
        if ($apiProcess.HasExited) {
            throw "The FastAPI process exited before readiness. Review $ApiErrorLog"
        }
        try {
            $ready = Invoke-RestMethod -Uri "$ApiUrl/ready" -TimeoutSec 3
            $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 3
            $apiReady = $ready.status -eq "ready"
            $databaseReady = $health.components.database -eq "available"
            $modelReady = $health.components.models -eq "available" -and
                -not [string]::IsNullOrWhiteSpace([string]$ready.model_version)
            if ($modelReady) { $modelVersion = [string]$ready.model_version }
        } catch {
            $apiReady = $false
            $databaseReady = $false
            $modelReady = $false
        }
        if ($apiReady -and $databaseReady -and $modelReady) { break }
        Start-Sleep -Seconds 2
    }
    if (-not ($apiReady -and $databaseReady -and $modelReady)) {
        if (-not $apiProcess.HasExited) { Stop-OwnedStartedProcess -StartedProcess $apiProcess -ExpectedExecutable $VenvPython -ExpectedStartTicks $apiStartTicks }
        throw "FastAPI did not become ready within $TimeoutSeconds seconds. Review $ApiErrorLog"
    }
    Write-Output "Backend: ONLINE; SQLite: READY; Model: READY ($modelVersion)."

    Write-Output "[4/5] Starting Next.js on 127.0.0.1:$FrontendPort and waiting for HTTP readiness..."
    $quotedNextBinary = '"' + $NextBinary + '"'
    $frontendArguments = @($quotedNextBinary, "start", "--hostname", "127.0.0.1", "--port", "$FrontendPort")
    try {
        $frontendProcess = Start-Process -FilePath $NodeExecutable -ArgumentList $frontendArguments `
            -WorkingDirectory $FrontendRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrorLog
        $frontendIdentity = Get-Process -Id $frontendProcess.Id -ErrorAction Stop
        $frontendStartTicks = $frontendIdentity.StartTime.ToUniversalTime().Ticks
        $frontendExecutablePath = Get-ProcessExecutablePath -Process $frontendIdentity
        if (-not $frontendExecutablePath.Equals($NodeExecutable, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Next.js started from an unexpected executable path. Review $FrontendErrorLog"
        }
    } catch {
        $frontendCleanupFailure = $null
        if ($null -ne $frontendProcess -and $frontendStartTicks -gt 0) {
            try {
                Stop-OwnedStartedProcess -StartedProcess $frontendProcess -ExpectedExecutable $NodeExecutable -ExpectedStartTicks $frontendStartTicks
            } catch {
                $frontendCleanupFailure = $_.Exception.Message
            }
        }
        if (-not $apiProcess.HasExited) { Stop-OwnedStartedProcess -StartedProcess $apiProcess -ExpectedExecutable $VenvPython -ExpectedStartTicks $apiStartTicks }
        $cleanupNote = if ($frontendCleanupFailure) { " Frontend cleanup also failed: $frontendCleanupFailure" } else { " Any launched frontend process was safely stopped." }
        throw "Next.js could not start. Review $FrontendErrorLog. $($_.Exception.Message)$cleanupNote"
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $frontendReady = $false
    while ((Get-Date) -lt $deadline) {
        if ($apiProcess.HasExited) {
            if (-not $frontendProcess.HasExited) {
                Stop-OwnedStartedProcess -StartedProcess $frontendProcess -ExpectedExecutable $NodeExecutable -ExpectedStartTicks $frontendStartTicks
            }
            throw "FastAPI exited while Next.js was starting. Review $ApiErrorLog"
        }
        if ($frontendProcess.HasExited) {
            if (-not $apiProcess.HasExited) {
                Stop-OwnedStartedProcess -StartedProcess $apiProcess -ExpectedExecutable $VenvPython -ExpectedStartTicks $apiStartTicks
            }
            throw "The Next.js process exited before HTTP readiness. Review $FrontendErrorLog"
        }
        try {
            $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 5 -UseBasicParsing
            $frontendReady = $response.StatusCode -eq 200 -and
                $response.Content -match "Analyst command center"
        } catch {
            $frontendReady = $false
        }
        if ($frontendReady) { break }
        Start-Sleep -Seconds 2
    }
    if (-not $frontendReady) {
        foreach ($process in @($frontendProcess, $apiProcess)) {
            if ($null -ne $process -and -not $process.HasExited) {
                if ($process.Id -eq $frontendProcess.Id) {
                    Stop-OwnedStartedProcess -StartedProcess $process -ExpectedExecutable $NodeExecutable -ExpectedStartTicks $frontendStartTicks
                } else {
                    Stop-OwnedStartedProcess -StartedProcess $process -ExpectedExecutable $VenvPython -ExpectedStartTicks $apiStartTicks
                }
            }
        }
        throw "Next.js did not become HTTP-ready within $TimeoutSeconds seconds. Review $FrontendErrorLog"
    }
} finally {
    foreach ($key in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], "Process")
    }
}

$apiIdentity = Get-Process -Id $apiProcess.Id -ErrorAction Stop
$frontendIdentity = Get-Process -Id $frontendProcess.Id -ErrorAction Stop
$apiExecutablePath = Get-ProcessExecutablePath -Process $apiIdentity
$frontendExecutablePath = Get-ProcessExecutablePath -Process $frontendIdentity
$SessionPath = Join-Path $DatabaseDirectory "mission06-demo-session-$stamp-$suffix.json"
$session = [ordered]@{
    project_root = $ProjectRoot
    started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    api_port = $ApiPort
    frontend_port = $FrontendPort
    api_url = $ApiUrl
    dashboard_url = $FrontendUrl
    database_path = $DemoDatabase
    model_version = $modelVersion
    event_log_path = Join-Path $LogDirectory "mission06-demo-$stamp-$suffix.log"
    api = [ordered]@{
        process_id = $apiIdentity.Id
        executable = $apiExecutablePath
        started_at_utc = $apiIdentity.StartTime.ToUniversalTime().ToString("o")
    }
    frontend = [ordered]@{
        process_id = $frontendIdentity.Id
        executable = $frontendExecutablePath
        started_at_utc = $frontendIdentity.StartTime.ToUniversalTime().ToString("o")
    }
}
$session | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $SessionPath -Encoding utf8

Write-Output "Mission 06 demo is ready on loopback."
Write-Output "Backend: ONLINE"
Write-Output "Frontend: ONLINE"
Write-Output "Database: READY"
Write-Output "Model: READY ($modelVersion)"
Write-Output "Dashboard: $FrontendUrl"
Write-Output "API Docs: http://127.0.0.1:$ApiPort/docs"
Write-Output "Persistent demo database: $DemoDatabase (existing records are preserved)."
Write-Output "API process ID: $($apiProcess.Id)"
Write-Output "Frontend process ID: $($frontendProcess.Id)"
Write-Output "Stop both demo processes safely with: scripts\stop-demo.ps1 -SessionPath `"$SessionPath`""
Write-Output "Logs: $LogDirectory"
