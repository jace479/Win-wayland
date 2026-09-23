@echo off
setlocal enabledelayedexpansion
title Launching KDE Konsole (WSLg - Zero TCP/IP)

echo ========================================================
echo   KDE Konsole Terminal - WSLg Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)
echo ========================================================
echo.

set "TARGET_PATH=%~1"

if "%TARGET_PATH%"=="" (
    echo Launching Konsole terminal...
    wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh konsole
) else (
    set "TARGET_PATH=!TARGET_PATH:\=/!"
    echo Launching Konsole terminal in: %~1
    wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh konsole "!TARGET_PATH!"
)

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Konsole launched in background.
) else (
    echo [ERROR] Failed to launch Konsole. Exit code: %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
