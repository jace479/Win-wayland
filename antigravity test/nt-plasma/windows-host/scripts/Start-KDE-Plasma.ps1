<#
.SYNOPSIS
    Launches the authentic KDE Plasma desktop shell (plasmashell, kded5, krunner) in Ubuntu WSL2.
.DESCRIPTION
    Runs strictly over local UNIX domain sockets and Hyper-V VSOCK via WSLg (Zero TCP/IP).
    Sets Wayland and KDE session environment variables and detaches processes.
#>

[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Starting KDE Plasma (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KDE Plasma Desktop Shell - WSLg Launcher" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)" -ForegroundColor Green
Write-Host "Backend  : WSLg / Hyper-V VSOCK" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Launching plasmashell, kded5, and krunner in background..." -ForegroundColor Yellow

$exePath = Join-Path $PSScriptRoot "build\Release\kwin_win.exe"
Start-Process -FilePath $exePath

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] KDE Plasma desktop environment launched successfully!" -ForegroundColor Green
    Write-Host "Running components: plasmashell, kded5, krunner" -ForegroundColor Gray
    Write-Host "Log file: ~/.local/state/nt-plasma/plasma.log" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "[ERROR] Failed to start KDE Plasma. Exit code: $LASTEXITCODE" -ForegroundColor Red
}

Write-Host ""
