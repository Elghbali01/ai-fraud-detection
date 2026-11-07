@echo off
setlocal EnableExtensions
title AI Fraud Detection - Stop
cd /d "%~dp0"

echo ========================================
echo  AI FRAUD DETECTION
echo  Safe local shutdown
echo ========================================

set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL_EXE%" (
    echo ERROR: Windows PowerShell was not found at the standard Windows path.
    echo No services or data were changed.
    pause
    exit /b 1
)

"%POWERSHELL_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-demo.ps1"
set "STOP_EXIT=%ERRORLEVEL%"
if not "%STOP_EXIT%"=="0" (
    echo.
    echo Shutdown did not complete. Review data\backend\mission06-demo-logs.
    pause
    exit /b %STOP_EXIT%
)

echo.
echo The SQLite database, model artifacts, uploads, and source data were preserved.
pause
exit /b 0
