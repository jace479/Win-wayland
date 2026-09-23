<#
.SYNOPSIS
    Launches KDE Konsole Terminal in Ubuntu WSL2 via WSLg.
.DESCRIPTION
    Runs strictly over local UNIX domain sockets and Hyper-V VSOCK via WSLg (Zero TCP/IP).
    Supports specifying a working directory.
.PARAMETER WorkingDirectory
    Optional directory path to open in Konsole.
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string]$WorkingDirectory
)

$Host.UI.RawUI.WindowTitle = "Launching KDE Konsole (WSLg - Zero TCP/IP)"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KDE Konsole Terminal - WSLg Launcher" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Distro   : Ubuntu" -ForegroundColor Gray
Write-Host "User     : jace479" -ForegroundColor Gray
Write-Host "Protocol : Native Wayland UNIX Domain Socket (Zero TCP/IP)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if ($WorkingDirectory) {
    $normalizedPath = $WorkingDirectory.Replace('\', '/')
    Write-Host "Launching Konsole in directory: $WorkingDirectory" -ForegroundColor Yellow
    $wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "konsole", $normalizedPath)
    & wsl.exe $wslArgs
} else {
    Write-Host "Launching Konsole terminal..." -ForegroundColor Yellow
    $wslArgs = @("-d", "Ubuntu", "-u", "jace479", "/opt/nt-plasma/wsl/launch-app.sh", "konsole")
    & wsl.exe $wslArgs
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Konsole launched in background." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to launch Konsole. Exit code: $LASTEXITCODE" -ForegroundColor Red
}
Write-Host ""
