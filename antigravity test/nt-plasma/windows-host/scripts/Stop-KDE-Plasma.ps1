<#
.SYNOPSIS
    Gracefully stops all running KDE Plasma processes and applications in Ubuntu WSL2.
.DESCRIPTION
    Sends SIGTERM and ensures clean termination of plasmashell, krunner, kded5, dolphin, konsole, etc.
    Protocol: Local Signal IPC (Zero TCP/IP).
#>

[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Stopping KDE Plasma (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "  KDE Plasma Desktop Shell - Graceful Shutdown" -ForegroundColor White -BackgroundColor DarkMagenta
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Local Signal IPC (Zero TCP/IP)" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Stopping all running KDE processes and applications..." -ForegroundColor Yellow

$wslArgs = @("-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", "/opt/nt-plasma/wsl/plasma-stop.sh")
& wsl.exe $wslArgs
Stop-Process -Name kwin_win -Force -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] All KDE Plasma processes stopped cleanly." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Failed to cleanly stop all KDE processes. Exit code: $LASTEXITCODE" -ForegroundColor Red
}

Write-Host ""
