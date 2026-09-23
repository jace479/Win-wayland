@echo off
setlocal enabledelayedexpansion
title Launching KDE System Settings (WSLg - Zero TCP/IP)

echo ========================================================
echo   KDE System Settings - WSLg Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)
echo ========================================================
echo.
echo Launching KDE System Settings control center...

wsl.exe -d Ubuntu -u jace479 /opt/nt-plasma/wsl/launch-app.sh systemsettings %*

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] KDE System Settings launched in background.
) else (
    echo [ERROR] Failed to launch KDE System Settings. Exit code: %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
