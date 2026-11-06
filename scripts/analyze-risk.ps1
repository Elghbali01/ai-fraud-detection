param(
    [Parameter(Mandatory = $true)][string]$InputPath,
    [string]$PythonPath = ".venv-isolated\Scripts\python.exe",
    [string]$OutputPath,
    [switch]$IncludeAnomaly,
    [switch]$IncludeExplanations,
    [int]$TopK = -1,
    [double]$BudgetPercent = -1
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$PythonCandidate = if ([IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $ProjectRoot $PythonPath }
$VenvPython = (Resolve-Path -LiteralPath $PythonCandidate).Path
$ResolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$CliArgs = @()
if ($TopK -ge 0 -or $BudgetPercent -ge 0) {
    if ($TopK -ge 0 -and $BudgetPercent -ge 0) { throw "Choose either TopK or BudgetPercent." }
    $CliArgs += "prioritize"
    $CliArgs += $ResolvedInput
    if ($TopK -ge 0) { $CliArgs += @("--top-k", "$TopK") } else { $CliArgs += @("--budget-percent", "$BudgetPercent") }
} else {
    $CliArgs += "score"
    $CliArgs += $ResolvedInput
    if ($IncludeAnomaly) { $CliArgs += "--anomaly" }
    if ($IncludeExplanations) { $CliArgs += "--explain" }
}
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $CliArgs += @("--output", [IO.Path]::GetFullPath($OutputPath)) }
& $VenvPython -m fraud_detection.explainability.cli @CliArgs
exit $LASTEXITCODE
