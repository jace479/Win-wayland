@echo off
setlocal
echo ========================================================
echo   Authentic KDE Plasma Desktop - WSLg Session Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland/X11 UNIX Domain Socket (ZERO TCP/IP)
echo Session  : Authentic KDE Plasma 5.27 LTS
echo ========================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Authentic-Plasma.ps1" %*
endlocal
