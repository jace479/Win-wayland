<#
.SYNOPSIS
    Launches KDE Dolphin File Manager in Ubuntu WSL2 via WSLg.
.DESCRIPTION
    Runs strictly over local UNIX domain sockets and Hyper-V VSOCK via WSLg (Zero TCP/IP).
    Supports opening specific Windows or WSL folders.
.PARAMETER Path
    Optional directory path to open in Dolphin.
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string]$Path
)

$Host.UI.RawUI.WindowTitle = "Launching KDE Dolphin (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KDE Dolphin File Manager - WSLg Launcher" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if ($Path) {
    $normalizedPath = $Path.Replace('\', '/')
    Write-Host "Launching Dolphin for directory: $Path" -ForegroundColor Yellow
    $wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "dolphin", $normalizedPath)
    & wsl.exe $wslArgs
} else {
    Write-Host "Launching Dolphin at default home directory..." -ForegroundColor Yellow
    $wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "dolphin")
    & wsl.exe $wslArgs
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Dolphin launched in background." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to launch Dolphin. Exit code: $LASTEXITCODE" -ForegroundColor Red
}
Write-Host ""
