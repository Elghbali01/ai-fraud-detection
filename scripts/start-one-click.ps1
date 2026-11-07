$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DatabaseDirectory = Join-Path $ProjectRoot "data\backend"
$UploadDirectory = Join-Path $ProjectRoot "data\uploads\mission06-demo"
$LogDirectory = Join-Path $DatabaseDirectory "mission06-demo-logs"
$SessionPattern = "mission06-demo-session-*.json"
$LockPath = Join-Path $DatabaseDirectory "mission06-demo-start.lock"
$ApiPort = 8001
$FrontendPort = 3100
$ApiUrl = "http://127.0.0.1:$ApiPort/api/v1"
$DashboardUrl = "http://127.0.0.1:$FrontendPort"
$DemoScript = Join-Path $ProjectRoot "scripts\start-demo.ps1"
$VerifyScript = Join-Path $ProjectRoot "scripts\verify_api_artifacts.py"
$PythonPath = ""
$NodeExecutable = ""
$SessionFile = $null
$Session = $null
$LockStream = $null

New-Item -ItemType Directory -Force -Path $DatabaseDirectory, $UploadDirectory, $LogDirectory | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$EventLog = Join-Path $LogDirectory "mission06-launch-$stamp-$suffix.log"
Set-Content -LiteralPath $EventLog -Value "AI Fraud Detection launcher started at $((Get-Date).ToUniversalTime().ToString('o'))" -Encoding UTF8

function Write-LaunchLog([string]$Message, [string]$Level = "INFO") {
    $line = "{0} [{1}] {2}" -f (Get-Date).ToUniversalTime().ToString("o"), $Level, $Message
    Add-Content -LiteralPath $EventLog -Value $line -Encoding UTF8
    if ($Level -eq "ERROR") {
        Write-Host $Message -ForegroundColor Red
    } elseif ($Level -eq "WARN") {
        Write-Host $Message -ForegroundColor Yellow
    } else {
        Write-Host $Message
    }
}

function Get-RecordedProcessState([object]$Identity) {
    if ($null -eq $Identity -or [int]$Identity.process_id -lt 1) {
        return [pscustomobject]@{ status = "mismatch"; process = $null }
    }
    $process = Get-Process -Id ([int]$Identity.process_id) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return [pscustomobject]@{ status = "stopped"; process = $null }
    }
    try {
        $actualPath = Get-ProcessExecutablePath -Process $process
        $expectedPath = (Resolve-Path -LiteralPath ([string]$Identity.executable)).Path
        $actualStart = $process.StartTime.ToUniversalTime().Ticks
        $expectedStart = ([datetime]$Identity.started_at_utc).ToUniversalTime().Ticks
        if (
            $actualPath.Equals($expectedPath, [StringComparison]::OrdinalIgnoreCase) -and
            $actualStart -eq $expectedStart
        ) {
            return [pscustomobject]@{ status = "match"; process = $process }
        }
    } catch { }
    return [pscustomobject]@{ status = "mismatch"; process = $null }
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

function Get-ServiceReadiness {
    try {
        $ready = Invoke-RestMethod -Uri "$ApiUrl/ready" -TimeoutSec 3
        $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 3
        $isReady = $ready.status -eq "ready"
        return [pscustomobject]@{
            backend = $isReady -and $health.status -eq "alive"
            database = $isReady -and $health.components.database -eq "available"
            model = $isReady -and $health.components.models -eq "available" -and
                -not [string]::IsNullOrWhiteSpace([string]$ready.model_version)
            model_version = [string]$ready.model_version
        }
    } catch {
        return [pscustomobject]@{ backend = $false; database = $false; model = $false; model_version = "" }
    }
}

function Test-FrontendReady {
    try {
        $response = Invoke-WebRequest -Uri $DashboardUrl -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200 -and $response.Content -match "Analyst command center"
    } catch {
        return $false
    }
}

function Open-DashboardAndReport([object]$ServiceState, [bool]$FrontendReady, [string]$ActiveSessionPath) {
    if (-not ($ServiceState.backend -and $ServiceState.database -and $ServiceState.model -and $FrontendReady)) {
        throw "Refusing to report READY or open a dashboard that did not pass endpoint checks."
    }

    Write-LaunchLog "[5/5] Opening the default browser after API readiness and frontend HTTP 200."
    $browserNote = ""
    try {
        Start-Process -FilePath $DashboardUrl
        $browserNote = "The Windows default URL handler was invoked. Page rendering is not observable by this launcher."
        Write-LaunchLog $browserNote
    } catch {
        $browserNote = "Automatic browser launch failed: $($_.Exception.Message)"
        Write-LaunchLog $browserNote "WARN"
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " AI FRAUD DETECTION - READY" -ForegroundColor Green
    Write-Host " Explainable Intelligence Platform" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Backend: ONLINE" -ForegroundColor Green
    Write-Host "Frontend: ONLINE" -ForegroundColor Green
    Write-Host "Database: READY" -ForegroundColor Green
    Write-Host "Model: READY ($($ServiceState.model_version))" -ForegroundColor Green
    Write-Host "Dashboard: $DashboardUrl"
    Write-Host "API Docs: http://127.0.0.1:$ApiPort/docs"
    Write-Host "Session: $ActiveSessionPath"
    Write-Host "Logs: $LogDirectory"
    if ($browserNote -like "Automatic browser launch failed:*") { Write-Host $browserNote -ForegroundColor Yellow }
}

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " AI FRAUD DETECTION" -ForegroundColor Cyan
    Write-Host " Explainable Intelligence Platform" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-LaunchLog "Startup requested. Project root: $ProjectRoot"

    try {
        $LockStream = [IO.File]::Open($LockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch {
        throw "Another one-click startup is already in progress. Wait for it to finish; no duplicate services were started."
    }

    Write-Host "[1/5] Checking PowerShell, Python, Node.js, virtual environment, dependencies, and configuration..." -ForegroundColor Cyan
    if ($PSVersionTable.PSVersion.Major -lt 5) { throw "Windows PowerShell 5.1 or PowerShell 7 is required." }
    if (-not (Test-Path -LiteralPath $DemoScript)) { throw "Startup script is missing: $DemoScript" }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "backend\app\core\config.py"))) {
        throw "FastAPI configuration file is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "frontend\package.json"))) {
        throw "Frontend package configuration is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "frontend\package-lock.json"))) {
        throw "Frontend package-lock.json is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env.example"))) {
        throw "The documented configuration template .env.example is missing."
    }

    $pythonCandidates = @(
        (Join-Path $ProjectRoot ".venv-isolated\Scripts\python.exe"),
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
    )
    $PythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $PythonPath) {
        throw "No project virtual environment was found. Run the Python setup instructions in README.md; dependencies will not be installed automatically."
    }
    $PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
    $pythonVersion = (& $PythonPath -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^3\.11\.') {
        throw "The project environment must use Python 3.11; found '$pythonVersion'."
    }
    Write-LaunchLog "Python environment found: $PythonPath (Python $pythonVersion)."

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand) { throw "Node.js was not found. Install Node.js 20.9 or newer and reopen this launcher." }
    $NodeExecutable = (Resolve-Path -LiteralPath $nodeCommand.Source).Path
    $nodeVersionText = (& $NodeExecutable --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $nodeVersionText -notmatch '^v(\d+\.\d+\.\d+)$') {
        throw "Could not read the Node.js version."
    }
    if ([version]$Matches[1] -lt [version]"20.9.0") {
        throw "Node.js 20.9 or newer is required; found $nodeVersionText."
    }
    Write-LaunchLog "Node.js found: $NodeExecutable ($nodeVersionText)."

    $nextBinary = Join-Path $ProjectRoot "frontend\node_modules\next\dist\bin\next"
    $buildId = Join-Path $ProjectRoot "frontend\.next\BUILD_ID"
    $chunksPath = Join-Path $ProjectRoot "frontend\.next\static\chunks"
    if (-not (Test-Path -LiteralPath $nextBinary)) {
        throw "Frontend dependencies are missing. Install the locked npm dependencies from README.md; they will not be installed automatically."
    }
    if (-not (Test-Path -LiteralPath $buildId) -or -not (Test-Path -LiteralPath $chunksPath)) {
        throw "The optimized Next.js production build is missing. Build the frontend before using the one-click launcher."
    }

    $oldPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
        $dependencyCheck = (& $PythonPath -c "import fastapi, uvicorn, sqlalchemy, alembic, numpy, pandas, sklearn, shap, joblib; from backend.app.core.config import Settings; print('runtime-dependencies=ready')" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "A required Python runtime dependency is missing or invalid. $dependencyCheck"
        }
    } finally {
        $env:PYTHONPATH = $oldPythonPath
    }
    Write-LaunchLog "Python API, SQLite, model-service, and explainability imports verified."

    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        $nextVersion = (& $NodeExecutable -p "require('./node_modules/next/package.json').version" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $nextVersion -ne "16.4.5") {
            throw "Expected the installed Next.js 16.4.5 runtime; found '$nextVersion'."
        }
    } finally {
        Pop-Location
    }
    Write-LaunchLog "Next.js production runtime dependencies and build configuration verified."

    Write-Host "[2/5] Checking model artifacts, SQLite configuration, ports, and existing sessions..." -ForegroundColor Cyan
    $sessionFiles = @(Get-ChildItem -LiteralPath $DatabaseDirectory -Filter $SessionPattern -File -ErrorAction SilentlyContinue)
    if ($sessionFiles.Count -gt 1) {
        throw "Multiple demo session manifests exist. No new services were started; use STOP_AI_FRAUD.bat to safely close recorded sessions."
    }

    if ($sessionFiles.Count -eq 1) {
        $SessionFile = $sessionFiles[0]
        $Session = Get-Content -LiteralPath $SessionFile.FullName -Raw | ConvertFrom-Json
        if (-not $Session.project_root.Equals($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "The saved session belongs to a different project root. No process was changed."
        }
        $apiState = Get-RecordedProcessState -Identity $Session.api
        $frontendState = Get-RecordedProcessState -Identity $Session.frontend
        if ($apiState.status -eq "mismatch" -or $frontendState.status -eq "mismatch") {
            throw "A saved PID no longer matches its recorded executable/start time. No process was changed; inspect the session manifest and logs."
        }
        if ($apiState.status -eq "stopped" -and $frontendState.status -eq "stopped") {
            Remove-Item -LiteralPath $SessionFile.FullName -Force
            Write-LaunchLog "Removed stale session manifest; both recorded processes were already stopped."
            $SessionFile = $null
            $Session = $null
        } elseif ($apiState.status -ne "match" -or $frontendState.status -ne "match") {
            throw "Only part of a recorded demo session is running. No duplicate was started; use STOP_AI_FRAUD.bat to stop the remaining owned process."
        } else {
            $existingReadiness = Get-ServiceReadiness
            $existingFrontendReady = Test-FrontendReady
            if (-not ($existingReadiness.backend -and $existingReadiness.database -and $existingReadiness.model -and $existingFrontendReady)) {
                throw "A recorded demo session is running but a readiness check failed. No duplicate was started; review the logs and use STOP_AI_FRAUD.bat before retrying."
            }
            $Session = Get-Content -LiteralPath $SessionFile.FullName -Raw | ConvertFrom-Json
            Write-LaunchLog "Existing session is healthy; reusing recorded API PID $($Session.api.process_id) and frontend PID $($Session.frontend.process_id)."
            Open-DashboardAndReport -ServiceState $existingReadiness -FrontendReady $existingFrontendReady -ActiveSessionPath $SessionFile.FullName
            return
        }
    }

    $databasePath = Join-Path $DatabaseDirectory "mission06-demo.sqlite3"
    if (Test-Path -LiteralPath $databasePath) {
        Write-LaunchLog "Existing SQLite database found and will be preserved: $databasePath"
    } else {
        Write-LaunchLog "No Mission 06 demo database exists yet; the existing migration workflow will initialize it without deleting other database files."
    }

    $oldEnvironment = @{}
    $overrides = @{
        PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
        FRAUD_API_APP_ENV = "development"
        FRAUD_API_ENABLE_DOCS = "true"
        FRAUD_API_HOST = "127.0.0.1"
        FRAUD_API_PORT = "$ApiPort"
        FRAUD_API_CORS_ORIGINS = "[`"http://127.0.0.1:$FrontendPort`",`"http://localhost:$FrontendPort`"]"
        FRAUD_API_DATABASE_PATH = $databasePath
        FRAUD_API_UPLOAD_DIRECTORY = $UploadDirectory
        NEXT_PUBLIC_FRAUD_API_URL = $ApiUrl
    }
    try {
        foreach ($key in $overrides.Keys) {
            $oldEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
            [Environment]::SetEnvironmentVariable($key, $overrides[$key], "Process")
        }
        $artifactOutput = (& $PythonPath $VerifyScript 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw "The local ML/explainability artifact verifier failed. $artifactOutput" }
        $artifactReport = $artifactOutput | ConvertFrom-Json
        if ($artifactReport.status -ne "verified" -or [string]::IsNullOrWhiteSpace([string]$artifactReport.model_version)) {
            throw "The local ML/explainability artifact verifier did not report a verified model."
        }
        Write-LaunchLog "Model and explanation artifacts verified without training. Model version: $($artifactReport.model_version)."
    } finally {
        foreach ($key in $overrides.Keys) {
            [Environment]::SetEnvironmentVariable($key, $oldEnvironment[$key], "Process")
        }
    }

    foreach ($port in @($ApiPort, $FrontendPort)) {
        if (-not (Test-LoopbackPortAvailable $port)) {
            throw "Loopback port $port is already occupied. No process was changed. Close its owning application or choose another configured port."
        }
        Write-LaunchLog "Loopback port $port is available."
    }

    Write-Host "[3/5] Starting FastAPI, waiting for /api/v1/ready, then starting Next.js..." -ForegroundColor Cyan
    & $DemoScript -PythonPath $PythonPath -NodePath $NodeExecutable -ApiPort $ApiPort -FrontendPort $FrontendPort -TimeoutSeconds 120
    if (-not $?) { throw "The local demo startup script failed. See $LogDirectory for backend/frontend output logs." }

    $sessionFiles = @(Get-ChildItem -LiteralPath $DatabaseDirectory -Filter $SessionPattern -File | Sort-Object LastWriteTime -Descending)
    if ($sessionFiles.Count -ne 1) {
        throw "The demo services returned without exactly one session manifest. Inspect $LogDirectory before retrying."
    }
    $SessionFile = $sessionFiles[0]
    $Session = Get-Content -LiteralPath $SessionFile.FullName -Raw | ConvertFrom-Json
    $readiness = Get-ServiceReadiness
    $frontendReady = Test-FrontendReady
    if (-not ($readiness.backend -and $readiness.database -and $readiness.model -and $frontendReady)) {
        throw "Post-start readiness verification failed. The dashboard was not opened; inspect $LogDirectory and use STOP_AI_FRAUD.bat to stop only the recorded processes."
    }

    $Session.event_log_path = $EventLog
    $Session | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $SessionFile.FullName -Encoding UTF8
    Write-LaunchLog "Backend ready; PID $($Session.api.process_id), port $ApiPort."
    Write-LaunchLog "Database ready at $databasePath; migration and live readiness checks succeeded."
    Write-LaunchLog "Model ready: $($readiness.model_version)."
    Write-LaunchLog "Frontend ready; PID $($Session.frontend.process_id), HTTP 200 at $DashboardUrl."
    Open-DashboardAndReport -ServiceState $readiness -FrontendReady $frontendReady -ActiveSessionPath $SessionFile.FullName
} catch {
    try { Write-LaunchLog "Startup failed: $($_.Exception.Message)" "ERROR" } catch { }
    Write-Host ""
    Write-Host "AI Fraud Detection did not start. No unrelated process or persistent data was removed." -ForegroundColor Red
    Write-Host "Log folder: $LogDirectory" -ForegroundColor Yellow
    throw
} finally {
    if ($null -ne $LockStream) { $LockStream.Dispose() }
}
