<#
.SYNOPSIS
    Configures ntKDE as the user-level Windows Shell in Winlogon.

.DESCRIPTION
    Sets the 'Shell' value under HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon
    to point to the ntKDE shell supervisor or host executable.
    Does NOT require administrative privileges because it operates in the user hive (HKCU).
    Automatically saves the previous shell setting for safe restoration.

.PARAMETER ShellExecutable
    The absolute or relative path to the shell host executable.
    Defaults to host/DesktopSurfaceHost/bin/Debug/net8.0-windows/DesktopSurfaceHost.exe.

.PARAMETER Force
    Overwrites any existing ntKDE shell configuration without prompting.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ShellExecutable = (Join-Path $PSScriptRoot '..\host\DesktopSurfaceHost\bin\Debug\net8.0-windows\DesktopSurfaceHost.exe'),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ShellExecutable)) {
    throw "ntKDE shell executable was not found: $ShellExecutable. Build it first with 'dotnet build host/DesktopSurfaceHost'."
}

$ShellExecutable = (Resolve-Path -LiteralPath $ShellExecutable).Path
$winlogonKey = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon'

if (-not (Test-Path $winlogonKey)) {
    New-Item -Path $winlogonKey -Force | Out-Null
}

$currentShell = (Get-ItemProperty -Path $winlogonKey -Name 'Shell' -ErrorAction SilentlyContinue).Shell

# Backup original shell if not already backed up
$backupShell = (Get-ItemProperty -Path $winlogonKey -Name 'ntKDE_OriginalShell' -ErrorAction SilentlyContinue).ntKDE_OriginalShell
if ([string]::IsNullOrWhiteSpace($backupShell)) {
    $originalToSave = if ([string]::IsNullOrWhiteSpace($currentShell)) { 'explorer.exe' } else { $currentShell }
    Set-ItemProperty -Path $winlogonKey -Name 'ntKDE_OriginalShell' -Value $originalToSave
    Write-Verbose "Saved original shell as '$originalToSave'"
}

if ($PSCmdlet.ShouldProcess($winlogonKey, "Set Shell to '$ShellExecutable'")) {
    Set-ItemProperty -Path $winlogonKey -Name 'Shell' -Value $ShellExecutable
    Write-Output "ntKDE configured as Windows Shell: $ShellExecutable"
    Write-Output "To restore Explorer at any time, run: powershell/Restore-WindowsShell.ps1"
}
