@echo off
setlocal enabledelayedexpansion
title Launching KDE Dolphin (WSLg - Zero TCP/IP)

echo ========================================================
echo   KDE Dolphin File Manager - WSLg Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)
echo ========================================================
echo.

set "TARGET_PATH=%~1"

if "%TARGET_PATH%"=="" (
    echo Launching Dolphin at default home directory...
    wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh dolphin
) else (
    set "TARGET_PATH=!TARGET_PATH:\=/!"
    echo Launching Dolphin for directory: %~1
    wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh dolphin "!TARGET_PATH!"
)

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Dolphin launched in background.
) else (
    echo [ERROR] Failed to launch Dolphin. Exit code: %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
