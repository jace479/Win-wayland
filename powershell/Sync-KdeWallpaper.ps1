<#
.SYNOPSIS
    Syncs the KDE Plasma desktop background / wallpaper to the Windows desktop.
.DESCRIPTION
    Reads the active KDE Plasma wallpaper from plasma-org.kde.plasma.desktop-appletsrc,
    resolves the highest-resolution image (including dark/light mode variants),
    caches it to %LOCALAPPDATA%\nt-plasma\wallpaper.jpg, and applies it to Windows
    via SystemParametersInfo(SPI_SETDESKWALLPAPER).
#>
param(
    [string]$DistroName = "Ubuntu",
    [string]$SpecificWallpaperPath = ""
)

$ErrorActionPreference = "SilentlyContinue"

$targetDir = "$env:LOCALAPPDATA\nt-plasma"
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}
$targetFile = "$targetDir\wallpaper.jpg"

$resolvedImage = ""

if ($SpecificWallpaperPath -and (Test-Path $SpecificWallpaperPath)) {
    $resolvedImage = $SpecificWallpaperPath
} else {
    # 1. Query WSL for the configured wallpaper path
    $wslOutput = wsl -d $DistroName -u jace479 -- bash -c "grep -E '^Image=' ~/.config/plasma-org.kde.plasma.desktop-appletsrc 2>/dev/null | head -n 1"
    if ($wslOutput -match "Image=(.+)") {
        $rawPath = $matches[1].Trim()
        if ($rawPath -match "^file://(.+)") {
            $rawPath = $matches[1]
        }
        
        # Convert WSL Linux path to UNC path
        $uncPath = "\\wsl.localhost\$DistroName$rawPath"
        $uncPath = $uncPath.Replace('/', '\')
        
        if (Test-Path $uncPath) {
            if ((Get-Item $uncPath) -is [System.IO.DirectoryInfo]) {
                # Look for contents/images_dark or contents/images
                $imgDirDark = Join-Path $uncPath "contents\images_dark"
                $imgDir = Join-Path $uncPath "contents\images"
                $chosenDir = $imgDir
                if (Test-Path $imgDirDark) {
                    $chosenDir = $imgDirDark
                }
                if (Test-Path $chosenDir) {
                    $imgs = Get-ChildItem -Path $chosenDir -Filter "*.jpg" | Sort-Object Length -Descending
                    if ($imgs.Count -gt 0) {
                        $resolvedImage = $imgs[0].FullName
                    }
                }
            } else {
                $resolvedImage = $uncPath
            }
        }
    }
    
    # Fallback to standard Flow dark wallpaper if not found
    if (-not $resolvedImage -or -not (Test-Path $resolvedImage)) {
        $flowDark = "\\wsl.localhost\$DistroName\usr\share\wallpapers\Flow\contents\images_dark\5120x2880.jpg"
        $flowLight = "\\wsl.localhost\$DistroName\usr\share\wallpapers\Flow\contents\images\5120x2880.jpg"
        if (Test-Path $flowDark) {
            $resolvedImage = $flowDark
        } elseif (Test-Path $flowLight) {
            $resolvedImage = $flowLight
        }
    }
}

if (-not $resolvedImage -or -not (Test-Path $resolvedImage)) {
    Write-Warning "[ntKDE] Could not find KDE wallpaper image."
    exit 1
}

Write-Host "[ntKDE] Syncing KDE wallpaper from: $resolvedImage"
Copy-Item -Path $resolvedImage -Destination $targetFile -Force

# Set registry values for desktop wallpaper style: Fill (10)
Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name Wallpaper -Value $targetFile -Force
Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name WallpaperStyle -Value "10" -Force
Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name TileWallpaper -Value "0" -Force

# Use compiled ApplyWallpaper helper for IDesktopWallpaper multi-monitor application
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$applierExe = Join-Path $scriptDir "ApplyWallpaper.exe"
if (Test-Path $applierExe) {
    & $applierExe $targetFile
    Write-Host "[ntKDE] Successfully applied KDE desktop background via IDesktopWallpaper: $targetFile"
} else {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class DesktopWallpaperSync {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
    
    public const int SPI_SETDESKWALLPAPER = 0x0014;
    public const int SPIF_UPDATEINIFILE = 0x01;
    public const int SPIF_SENDCHANGE = 0x02;
    
    public static bool ApplyWallpaper(string path) {
        return SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
    }
}
"@ -ErrorAction SilentlyContinue

    $success = [DesktopWallpaperSync]::ApplyWallpaper($targetFile)
    if ($success) {
        Write-Host "[ntKDE] Successfully applied KDE desktop background: $targetFile"
    } else {
        Write-Warning "[ntKDE] SystemParametersInfo returned false while setting wallpaper."
    }
}
