param(
    [string]$SessionPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DatabaseDirectory = Join-Path $ProjectRoot "data\backend"
$LogDirectory = Join-Path $DatabaseDirectory "mission06-demo-logs"
$LockPath = Join-Path $DatabaseDirectory "mission06-demo-start.lock"

if (-not (Test-Path -LiteralPath $DatabaseDirectory)) {
    Write-Output "No Mission 06 demo session exists. The application is already stopped."
    return
}
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$fallbackLog = Join-Path $LogDirectory "mission06-stop-$stamp-$suffix.log"

function Write-StopLog([string]$Path, [string]$Message) {
    $line = "{0} [STOP] {1}" -f (Get-Date).ToUniversalTime().ToString("o"), $Message
    Add-Content -LiteralPath $Path -Value $line -Encoding UTF8
}

$lockStream = $null
try {
    $lockStream = [IO.File]::Open(
        $LockPath,
        [IO.FileMode]::OpenOrCreate,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
} catch {
    Write-StopLog -Path $fallbackLog -Message "ERROR: Stop refused because startup holds the session lock."
    throw "A demo startup is in progress. Wait for it to finish, then run STOP_AI_FRAUD.bat again."
}

function Get-SessionLogPath([object]$Session, [string]$FallbackPath) {
    $candidate = [string]$Session.event_log_path
    if ([string]::IsNullOrWhiteSpace($candidate)) { return $FallbackPath }
    try {
        $resolvedCandidate = [IO.Path]::GetFullPath($candidate)
        $resolvedRoot = [IO.Path]::GetFullPath($LogDirectory).TrimEnd('\') + '\'
        if ($resolvedCandidate.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
            return $resolvedCandidate
        }
    } catch { }
    return $FallbackPath
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

try {
    if ([string]::IsNullOrWhiteSpace($SessionPath)) {
        $sessionFiles = @(Get-ChildItem -LiteralPath $DatabaseDirectory -Filter "mission06-demo-session-*.json" -File)
    } else {
        $resolvedSession = (Resolve-Path -LiteralPath $SessionPath).Path
        $sessionParent = Split-Path -Parent $resolvedSession
        $sessionName = Split-Path -Leaf $resolvedSession
        if (
            -not $sessionParent.Equals($DatabaseDirectory, [StringComparison]::OrdinalIgnoreCase) -or
            $sessionName -notmatch '^mission06-demo-session-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\.json$'
        ) {
            throw "Refusing a session file outside the project Mission 06 demo directory."
        }
        $sessionFiles = @((Get-Item -LiteralPath $resolvedSession))
    }

    if ($sessionFiles.Count -eq 0) {
        Write-StopLog -Path $fallbackLog -Message "Stop requested; no session manifest exists, so no process was changed."
        Write-Host "No active Mission 06 demo session was found. The application is already stopped."
        Write-Host "Log: $fallbackLog"
        return
    }

    $targets = @()
    $sessions = @()
    foreach ($file in $sessionFiles) {
        $session = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        if (-not $session.project_root.Equals($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Session '$($file.Name)' belongs to a different project root. No processes were changed."
        }
        $sessions += [pscustomobject]@{
            file = $file
            data = $session
            log = Get-SessionLogPath -Session $session -FallbackPath $fallbackLog
        }

        foreach ($role in @("api", "frontend")) {
            $identity = $session.$role
            $state = Get-RecordedProcessState -Identity $identity
            if ($state.status -eq "mismatch") {
                throw "PID $($identity.process_id) no longer matches the recorded $role process. No processes were changed."
            }
            if ($state.status -eq "match") {
                $targets += [pscustomobject]@{
                    process = $state.process
                    identity = $identity
                    role = $role
                    log = $sessions[-1].log
                }
            }
        }
    }

    foreach ($item in $sessions) {
        Write-StopLog -Path $item.log -Message "Stop requested for session $($item.file.Name)."
    }

    $stoppedIds = @{}
    foreach ($target in $targets) {
        $id = [int]$target.identity.process_id
        if ($stoppedIds.ContainsKey([string]$id)) { continue }
        $latestState = Get-RecordedProcessState -Identity $target.identity
        if ($latestState.status -eq "mismatch") {
            throw "PID $id changed identity during shutdown validation. It was not stopped."
        }
        if ($latestState.status -eq "stopped") {
            $stoppedIds[[string]$id] = $true
            Write-StopLog -Path $target.log -Message "$($target.role) process PID $id stopped before termination."
            continue
        }
        $latestState.process.Kill()
        if (-not $latestState.process.WaitForExit(10000)) {
            throw "Process $id did not stop within 10 seconds. Session files were retained for safe retry."
        }
        $stoppedIds[[string]$id] = $true
        Write-StopLog -Path $target.log -Message "Stopped owned $($target.role) process PID $id."
        Write-Output "Stopped Mission 06 $($target.role) process PID $id."
    }

    foreach ($item in $sessions) {
        foreach ($role in @("api", "frontend")) {
            $identity = $item.data.$role
            if (-not $stoppedIds.ContainsKey([string]$identity.process_id)) {
                Write-StopLog -Path $item.log -Message "$role process PID $($identity.process_id) was already stopped."
                Write-Output "$role process $($identity.process_id) was already stopped."
            }
        }
        Remove-Item -LiteralPath $item.file.FullName -Force
        Write-StopLog -Path $item.log -Message "Session stopped; SQLite database, model artifacts, and uploads were preserved."
    }

    Write-Output "Demo database, model artifacts, and uploads were preserved."
    Write-Output "Logs: $LogDirectory"
} catch {
    try { Write-StopLog -Path $fallbackLog -Message "ERROR: $($_.Exception.Message)" } catch { }
    throw
} finally {
    if ($null -ne $lockStream) { $lockStream.Dispose() }
}
