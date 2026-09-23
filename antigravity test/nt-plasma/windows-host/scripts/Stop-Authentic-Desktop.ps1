[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping authentic Linux desktop session in WSL..." -ForegroundColor Yellow

$stopCmd = "/opt/nt-plasma/wsl/stop-authentic-desktop.sh"
wsl.exe -d Ubuntu -u jace479 -e bash -c $stopCmd

Write-Host "Session terminated cleanly. Sockets cleared." -ForegroundColor Green
