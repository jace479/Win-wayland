<#
.SYNOPSIS
    Restores the standard Windows Explorer shell and restarts Explorer if necessary.

.DESCRIPTION
    Removes the user-level 'Shell' override under HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon,
    restoring Windows to its default shell (explorer.exe in HKLM).
    If Explorer is not currently running, it starts it immediately.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$StartExplorer = $true
)

$ErrorActionPreference = 'Stop'
$winlogonKey = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon'

if (Test-Path $winlogonKey) {
    $shellProp = Get-ItemProperty -Path $winlogonKey -Name 'Shell' -ErrorAction SilentlyContinue
    if ($shellProp) {
        if ($PSCmdlet.ShouldProcess($winlogonKey, 'Remove Shell override')) {
            Remove-ItemProperty -Path $winlogonKey -Name 'Shell' -ErrorAction SilentlyContinue
            Write-Output "Removed HKCU Winlogon Shell override."
        }
    }
    else {
        Write-Output "No user-level Shell override found in HKCU."
    }

    # Clean up backup property if present
    Remove-ItemProperty -Path $winlogonKey -Name 'ntKDE_OriginalShell' -ErrorAction SilentlyContinue
}

# Ensure Explorer is running
if ($StartExplorer) {
    $explorerRunning = @(Get-Process -Name explorer -ErrorAction SilentlyContinue).Count -gt 0
    if (-not $explorerRunning) {
        Write-Output "Starting explorer.exe..."
        Start-Process explorer.exe
    }
    else {
        Write-Output "Explorer is already running."
    }
}

Write-Output "Windows shell restored to default (explorer.exe)."
