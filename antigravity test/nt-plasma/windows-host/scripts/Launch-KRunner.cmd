@echo off
setlocal enabledelayedexpansion
title Launching KRunner (WSLg - Zero TCP/IP)

echo ========================================================
echo   KRunner Quick Launcher - WSLg
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)
echo ========================================================
echo.
echo Activating KRunner search overlay...

wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh krunner

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] KRunner activated in background.
) else (
    echo [ERROR] Failed to launch KRunner. Exit code: %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
