param([string]$PythonPath = ".venv-isolated\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$env:PYTHONPATH = (Join-Path $ProjectRoot "src") + ";" + $ProjectRoot
$PreviousDatabasePath = $env:FRAUD_API_DATABASE_PATH
$PreviousUploadDirectory = $env:FRAUD_API_UPLOAD_DIRECTORY
$BackendDataRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot "data\backend"))
$SmokeRoot = Join-Path $BackendDataRoot ("smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $SmokeRoot -Force | Out-Null
$env:FRAUD_API_DATABASE_PATH = Join-Path $SmokeRoot "mission04.sqlite3"
$env:FRAUD_API_UPLOAD_DIRECTORY = Join-Path $SmokeRoot "uploads"
$Process = $null
try {
    & (Join-Path $ProjectRoot "scripts\init-db.ps1") -PythonPath $VenvPython
    if ($LASTEXITCODE -ne 0) { throw "Temporary Mission 04 database initialization failed." }
    $Port = (& $VenvPython -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()").Trim()
    $StdoutLog = Join-Path $SmokeRoot "api-smoke.stdout.log"
    $StderrLog = Join-Path $SmokeRoot "api-smoke.stderr.log"
    $Process = Start-Process -FilePath $VenvPython `
        -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", $Port) `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru
    & $VenvPython (Join-Path $ProjectRoot "scripts\smoke_api.py") --url "http://127.0.0.1:$Port"
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $StderrLog) {
            Get-Content -LiteralPath $StderrLog -Tail 40 | Write-Output
        }
        throw "Live Mission 04 HTTP smoke failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $Process.WaitForExit(5000) | Out-Null
    }
    if ($null -eq $PreviousDatabasePath) { Remove-Item Env:FRAUD_API_DATABASE_PATH -ErrorAction SilentlyContinue }
    else { $env:FRAUD_API_DATABASE_PATH = $PreviousDatabasePath }
    if ($null -eq $PreviousUploadDirectory) { Remove-Item Env:FRAUD_API_UPLOAD_DIRECTORY -ErrorAction SilentlyContinue }
    else { $env:FRAUD_API_UPLOAD_DIRECTORY = $PreviousUploadDirectory }
    $ResolvedSmokeRoot = [IO.Path]::GetFullPath($SmokeRoot)
    if ($ResolvedSmokeRoot.StartsWith($BackendDataRoot + [IO.Path]::DirectorySeparatorChar) -and
        (Split-Path -Leaf $ResolvedSmokeRoot).StartsWith("smoke-")) {
        Remove-Item -LiteralPath $ResolvedSmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
