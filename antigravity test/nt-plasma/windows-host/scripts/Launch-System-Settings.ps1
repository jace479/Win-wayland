<#
.SYNOPSIS
    Launches KDE System Settings in Ubuntu WSL2 via WSLg.
.DESCRIPTION
    Runs strictly over local UNIX domain sockets and Hyper-V VSOCK via WSLg (Zero TCP/IP).
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$Host.UI.RawUI.WindowTitle = "Launching KDE System Settings (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KDE System Settings - WSLg Launcher" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Launching KDE System Settings control center..." -ForegroundColor Yellow

$wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "systemsettings")
if ($Arguments) {
    $wslArgs += $Arguments
}
& wsl.exe $wslArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] KDE System Settings launched in background." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to launch KDE System Settings. Exit code: $LASTEXITCODE" -ForegroundColor Red
}
Write-Host ""
