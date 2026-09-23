@echo off
setlocal
cd /d "%~dp0build\Release"
start "" "kwin_win.exe" %*
endlocal
