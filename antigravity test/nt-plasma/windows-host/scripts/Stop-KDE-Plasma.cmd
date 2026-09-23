@echo off
setlocal enabledelayedexpansion
title Stopping KDE Plasma Desktop (WSLg - Zero TCP/IP)

echo ========================================================
echo   KDE Plasma Desktop Shell - Graceful Shutdown
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Local Signal IPC (Zero TCP/IP)
echo ========================================================
echo.
echo Gracefully stopping all running KDE processes and applications...

wsl.exe -d Ubuntu -u jace479 -e bash -c "/opt/nt-plasma/wsl/plasma-stop.sh"
taskkill /IM kwin_win.exe /F >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] All KDE Plasma desktop components and apps stopped cleanly.
) else (
    echo.
    echo [ERROR] Encountered an error stopping KDE Plasma. Exit code: %ERRORLEVEL%
)

echo.
exit /b %ERRORLEVEL%
