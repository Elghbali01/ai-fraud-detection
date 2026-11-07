param(
    [Parameter(Mandatory = $true)]
    [string]$SessionPath
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DatabaseDirectory = (Resolve-Path (Join-Path $ProjectRoot "data\backend")).Path
$SessionFile = (Resolve-Path -LiteralPath $SessionPath).Path
$SessionParent = Split-Path -Parent $SessionFile
$SessionName = Split-Path -Leaf $SessionFile
if (
    -not $SessionParent.Equals($DatabaseDirectory, [StringComparison]::OrdinalIgnoreCase) -or
    $SessionName -notmatch '^mission06-demo-session-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\.json$'
) {
    throw "Refusing to use a session file outside the project Mission 06 demo directory."
}

$Session = Get-Content -LiteralPath $SessionFile -Raw | ConvertFrom-Json
if (-not $Session.project_root.Equals($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "The session file belongs to a different project root. No processes were changed."
}

$targets = @()
foreach ($role in @("api", "frontend")) {
    $identity = $Session.$role
    if ($null -eq $identity -or $identity.process_id -lt 1) {
        throw "The $role process identity is invalid. No processes were changed."
    }

    $process = Get-Process -Id ([int]$identity.process_id) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Write-Output "$role process $($identity.process_id) is already stopped."
        continue
    }

    $processPath = (Resolve-Path -LiteralPath $process.Path).Path
    $expectedPath = (Resolve-Path -LiteralPath $identity.executable).Path
    $startedAtUtc = $process.StartTime.ToUniversalTime().Ticks
    $expectedStartTicks = ([datetime]$identity.started_at_utc).ToUniversalTime().Ticks
    if (
        -not $processPath.Equals($expectedPath, [StringComparison]::OrdinalIgnoreCase) -or
        $startedAtUtc -ne $expectedStartTicks
    ) {
        throw "PID $($identity.process_id) no longer matches the recorded $role process. No processes were changed."
    }
    $targets += $process
}

foreach ($process in $targets) {
    Stop-Process -Id $process.Id -ErrorAction Stop
    Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue
    Write-Output "Stopped Mission 06 demo process $($process.Id)."
}

Remove-Item -LiteralPath $SessionFile -Force
Write-Output "Demo database and uploads were preserved."
