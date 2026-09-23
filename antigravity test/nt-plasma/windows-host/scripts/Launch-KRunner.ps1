<#
.SYNOPSIS
    Launches or triggers KRunner (KDE Quick Launcher / Search) in Ubuntu WSL2 via WSLg.
.DESCRIPTION
    Runs strictly over local UNIX domain sockets and Hyper-V VSOCK via WSLg (Zero TCP/IP).
#>

[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Launching KRunner (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KRunner Quick Launcher - WSLg" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Activating KRunner search overlay..." -ForegroundColor Yellow

$wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "krunner")
& wsl.exe $wslArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] KRunner activated in background." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to launch KRunner. Exit code: $LASTEXITCODE" -ForegroundColor Red
}
Write-Host ""
