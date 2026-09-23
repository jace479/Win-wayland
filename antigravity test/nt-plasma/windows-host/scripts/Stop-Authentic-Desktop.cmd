@echo off
setlocal
echo ========================================================
echo   Stop Authentic Desktop Session - WSLg
echo ========================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-Authentic-Desktop.ps1" %*
endlocal
