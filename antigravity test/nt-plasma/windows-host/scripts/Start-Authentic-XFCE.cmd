@echo off
setlocal
echo ========================================================
echo   Authentic XFCE4 Desktop - WSLg Session Launcher
echo ========================================================
echo Distro   : Ubuntu
echo User     : jace479
echo Protocol : Native Wayland/X11 UNIX Domain Socket (ZERO TCP/IP)
echo Session  : Authentic XFCE 4.18
echo ========================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Authentic-XFCE.ps1" %*
endlocal
