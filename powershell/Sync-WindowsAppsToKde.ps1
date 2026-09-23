[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $DistroName,

    [string] $CatalogPath = (Join-Path $env:LOCALAPPDATA 'nt-plasma\windows-catalog.json')
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$integrationPath = Join-Path $repoRoot 'integration'
$launcherPath = Join-Path $repoRoot 'wsl\launch-windows-app.sh'
$adapterPath = Join-Path $PSScriptRoot 'Start-WindowsCatalogApplication.ps1'

function ConvertTo-WslPath {
    param([Parameter(Mandatory)][string] $WindowsPath)

    $fullPath = [System.IO.Path]::GetFullPath($WindowsPath)
    if ($fullPath -notmatch '^(?<drive>[A-Za-z]):(?<path>.*)$') {
        throw "Only drive-backed Windows paths can be converted: $WindowsPath"
    }
    return "/mnt/$($Matches.drive.ToLowerInvariant())$($Matches.path -replace '\\', '/')"
}

$iconDir = Join-Path (Split-Path -Parent $CatalogPath) 'icons'
& (Join-Path $PSScriptRoot 'Get-WindowsAppCatalog.ps1') -OutputPath $CatalogPath -IconDirectory $iconDir
$wslCatalogPath = "`$HOME/.local/share/nt-plasma/windows-catalog.json"
$wslAdapterPath = "`$HOME/.local/share/nt-plasma/Start-WindowsCatalogApplication.ps1"
$wslLauncherPath = "`$HOME/.local/bin/launch-windows-app"
$wslEntriesPath = "`$HOME/.local/share/applications"
$wslIconPath = "`$HOME/.local/share/icons/ntkde"
$windowsCatalog = ConvertTo-WslPath $CatalogPath
$windowsIcons = ConvertTo-WslPath $iconDir
$windowsAdapter = ConvertTo-WslPath $adapterPath
$windowsLauncher = ConvertTo-WslPath $launcherPath
$windowsIntegration = ConvertTo-WslPath $integrationPath
$windowsHandler = ConvertTo-WslPath (Join-Path $repoRoot 'wsl\windows-executable-handler.desktop')
$windowsDriveSync = ConvertTo-WslPath (Join-Path $repoRoot 'wsl\sync-windows-drives-to-dolphin.sh')
$windowsEnsureMenu = ConvertTo-WslPath (Join-Path $repoRoot 'wsl\ensure-plasma-menu.py')
$commands = @(
    "mkdir -p `$HOME/.local/share/nt-plasma `$HOME/.local/share/applications `$HOME/.local/bin `$HOME/.local/share/icons/ntkde `$HOME/.config",
    "cp '$windowsCatalog' '$wslCatalogPath'",
    "cp '$windowsAdapter' '$wslAdapterPath'",
    "cp '$windowsLauncher' '$wslLauncherPath'",
    "chmod 755 '$wslLauncherPath'",
    "cp '$windowsHandler' `$HOME/.local/share/applications/windows-executable-handler.desktop",
    "chmod 644 `$HOME/.local/share/applications/windows-executable-handler.desktop",
    "cp -r '$windowsIcons'/* '$wslIconPath' 2>/dev/null || true",
    "cd '$windowsIntegration/..' && python3 -m integration.generate_kde_entries '$wslCatalogPath' '$wslEntriesPath' '$wslLauncherPath'",
    "bash '$windowsDriveSync'",
    "grep -q 'windows-executable-handler.desktop' `$HOME/.config/mimeapps.list 2>/dev/null || printf '%s\n' '[Default Applications]' 'application/x-ms-dos-executable=windows-executable-handler.desktop' 'application/x-msi=windows-executable-handler.desktop' 'application/x-msdownload=windows-executable-handler.desktop' 'application/x-bat=windows-executable-handler.desktop' >> `$HOME/.config/mimeapps.list",
    "python3 '$windowsEnsureMenu'",
    'export XDG_DATA_DIRS="$HOME/.local/share:/usr/local/share:/usr/share:/var/lib/snapd/desktop:/var/lib/flatpak/exports/share:$HOME/.local/share/flatpak/exports/share" && if command -v kbuildsycoca6 >/dev/null 2>&1; then XDG_MENU_PREFIX=plasma- kbuildsycoca6 --noincremental; elif command -v kbuildsycoca5 >/dev/null 2>&1; then XDG_MENU_PREFIX=plasma- kbuildsycoca5 --noincremental; fi || true',
    "update-desktop-database '$wslEntriesPath' 2>/dev/null || true"
)

$desktopFolder = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
if (Test-Path $desktopFolder) {
    $wslDesktopFolder = ConvertTo-WslPath $desktopFolder
    $commands += "if [[ ! -L `$HOME/Desktop || `$(readlink `$HOME/Desktop) != '$wslDesktopFolder' ]]; then rm -rf `$HOME/Desktop && ln -s '$wslDesktopFolder' `$HOME/Desktop; fi"
}

& wsl.exe --distribution $DistroName -- bash -lc ("set -Eeuo pipefail; " + ($commands -join '; '))
if ($LASTEXITCODE -ne 0) {
    throw "Failed to synchronize Windows applications to KDE."
}

Write-Output "Synchronized Windows applications to KDE for $DistroName."