$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Output "Project: $ProjectRoot"
Write-Output "Python:"
python --version
Write-Output "Python launcher registrations:"
$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PythonLauncher) {
    py -0p
} else {
    Write-Output "Python launcher is not installed; python is available on PATH."
}
Write-Output "Node:"
node --version
Write-Output "Git:"
git --version
Write-Output "Git branch and status:"
git status --short --branch
Write-Output "Disk:"
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free, Root | Format-Table -AutoSize
Write-Output "Dataset:"
$DatasetPath = Join-Path $ProjectRoot "data\raw\creditcard.csv"
if (Test-Path -LiteralPath $DatasetPath) {
    Get-Item -LiteralPath $DatasetPath | Select-Object Name, Length, LastWriteTime | Format-List
} else {
    Write-Output "Not present: $DatasetPath"
}
$KaggleCommand = Get-Command kaggle -ErrorAction SilentlyContinue
if ($KaggleCommand) {
    Write-Output "Kaggle CLI: available"
} else {
    Write-Output "Kaggle CLI: unavailable"
}
