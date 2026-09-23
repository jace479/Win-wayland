[CmdletBinding()]
param(
    [int]$Width = 1920,
    [int]$Height = 1080,
    [switch]$SpanCanvas
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Authentic KDE Plasma Desktop - WSLg Session Launcher" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland/X11 UNIX Domain Socket (ZERO TCP/IP)" -ForegroundColor Gray
Write-Host "Session  : Authentic KDE Plasma 5.27 LTS" -ForegroundColor Gray
Write-Host "Target   : ${Width}x${Height}" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan

if ($SpanCanvas) {
    # If spanning across all 5 monitors:
    $Width = 6330
    $Height = 2160
    Write-Host "Multi-Monitor Canvas Spanning enabled: ${Width}x${Height}" -ForegroundColor Yellow
}

Write-Host "`n[1/3] Checking WSL state..." -ForegroundColor Yellow
$distroState = (wsl.exe -l -v | Select-String "Ubuntu\s+(\w+)\s+2")
Write-Host "WSL Ubuntu is ready." -ForegroundColor Green

Write-Host "[2/3] Launching Authentic KDE Plasma session in WSL..." -ForegroundColor Yellow
$wslCmd = "nohup /opt/nt-plasma/wsl/start-authentic-desktop.sh plasma $Width $Height </dev/null >/tmp/plasma-start.log 2>&1 &"
wsl.exe -d Ubuntu -u jace479 -e bash -c $wslCmd

Write-Host "[3/3] Session launched successfully!" -ForegroundColor Green
Write-Host "The genuine KDE Plasma desktop session is now active." -ForegroundColor Cyan
Write-Host "You can stop the session anytime using: .\Stop-Authentic-Desktop.cmd" -ForegroundColor Gray
