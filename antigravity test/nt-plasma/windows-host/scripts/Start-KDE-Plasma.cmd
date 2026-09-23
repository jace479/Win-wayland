@echo off
setlocal enabledelayedexpansion
title Starting KDE Plasma Desktop (WSLg - Zero TCP/IP)

echo ========================================================
echo   KDE Plasma Desktop Shell - WSLg Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)
echo Backend  : WSLg / Hyper-V VSOCK
echo ========================================================
echo.
echo Starting plasmashell, kded5, and krunner in the background...

start "" "%~dp0build\Release\kwin_win.exe"
if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] KDE Plasma desktop environment launched successfully!
    echo Running components: plasmashell, kded5, krunner.
    echo Log file: ~/.local/state/nt-plasma/plasma.log
) else (
    echo.
    echo [ERROR] Failed to start KDE Plasma. Exit code: %ERRORLEVEL%
)

echo.
exit /b %ERRORLEVEL%
