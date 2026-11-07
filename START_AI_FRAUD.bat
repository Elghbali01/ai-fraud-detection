@echo off
setlocal EnableExtensions
title AI Fraud Detection - Start
cd /d "%~dp0"

echo ========================================
echo  AI FRAUD DETECTION
echo  Explainable Intelligence Platform
echo ========================================

set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL_EXE%" (
    echo ERROR: Windows PowerShell was not found at the standard Windows path.
    echo No services or data were changed.
    pause
    exit /b 1
)

"%POWERSHELL_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-one-click.ps1"
set "LAUNCH_EXIT=%ERRORLEVEL%"
if not "%LAUNCH_EXIT%"=="0" (
    echo.
    echo Startup failed. Review data\backend\mission06-demo-logs.
    pause
    exit /b %LAUNCH_EXIT%
)

echo.
echo The dashboard and API remain running until STOP_AI_FRAUD.bat is used.
pause
exit /b 0
