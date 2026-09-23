<#
.SYNOPSIS
    Discovers installed Windows Win32 and UWP/MSIX applications for ntKDE.

.DESCRIPTION
    Scans:
    1. Start Menu shortcuts (.lnk files) across ProgramData and User AppData.
    2. UWP / Modern packaged applications via Get-StartApps and Get-AppxPackage.
    Filters out circular WSL/Ubuntu links, uninstallers, and broken shortcuts.
    Classifies applications into standard freedesktop / KDE categories.
    Emits a structured JSON catalog suitable for KDE application launcher integration.

.PARAMETER OutputPath
    File path where the JSON catalog should be saved.

.PARAMETER IconDirectory
    Directory where extracted PNG icons should be placed.
    Defaults to $env:LOCALAPPDATA\nt-plasma\icons.
#>
[CmdletBinding()]
param(
    [string[]] $StartMenuRoots = @(
        (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs')
    ),

    [string] $OutputPath = (Join-Path $env:LOCALAPPDATA 'nt-plasma\windows-catalog.json'),
    [string] $IconDirectory = (Join-Path $env:LOCALAPPDATA 'nt-plasma\icons')
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

function Get-StableId {
    param([Parameter(Mandatory)][string] $Text)

    $normalized = $Text.Trim().ToLowerInvariant()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($hasher.ComputeHash($bytes)) -replace '-').ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
    }
}

function Classify-Application {
    param(
        [string] $Name,
        [string] $Target,
        [string] $HintCategory
    )

    $lowerName = $Name.ToLowerInvariant()
    $lowerTarget = $Target.ToLowerInvariant()

    # Development
    if ($lowerName -match 'visual studio|vs code|code|git|terminal|powershell|pycharm|intellij|rider|sublime|clion|webstorm|neovim|developer|compiler') {
        return 'Development'
    }
    # Games
    if ($lowerName -match 'steam|epic games|battle\.net|gog galaxy|riot|ubisoft|ea |xbox|minecraft|game') {
        return 'Game'
    }
    # Office
    if ($lowerName -match 'word|excel|powerpoint|outlook|onenote|access|acrobat|pdf|office|document|teams|slack') {
        return 'Office'
    }
    # Network / Internet
    if ($lowerName -match 'firefox|chrome|edge|brave|opera|discord|browser|ftp|vpn|web|remote desktop|mstsc') {
        return 'Network'
    }
    # AudioVideo
    if ($lowerName -match 'spotify|vlc|media player|audacity|obs|sound|audio|video|camera|music|streaming') {
        return 'AudioVideo'
    }
    # Graphics
    if ($lowerName -match 'paint|photoshop|gimp|illustrator|blender|photo|image|drawing|inkscape') {
        return 'Graphics'
    }
    # Settings
    if ($lowerName -match 'settings|control panel|preferences|options|config') {
        return 'Settings'
    }
    # System
    if ($lowerName -match 'task manager|sysinternals|registry|regedit|powershell|cmd|command prompt|disk management|device manager|event viewer|services|computer management|resource monitor|defrag|system information') {
        return 'System'
    }
    # Utility
    if ($lowerName -match 'calculator|notepad|snipping tool|snip|character map|magnifier|steps recorder|quick assist|wordpad') {
        return 'Utility'
    }

    if (-not [string]::IsNullOrWhiteSpace($HintCategory) -and $HintCategory -ne 'Other') {
        return $HintCategory
    }

    return 'Utility'
}

function Extract-Win32IconToPng {
    param(
        [string] $SourcePath,
        [string] $DestinationPng
    )

    try {
        if (-not (Test-Path -LiteralPath $SourcePath)) {
            return $false
        }

        $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($SourcePath)
        if ($null -eq $icon) {
            return $false
        }

        $bitmap = $icon.ToBitmap()
        try {
            $destDir = Split-Path -Parent $DestinationPng
            if (-not (Test-Path -LiteralPath $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            $bitmap.Save($DestinationPng, [System.Drawing.Imaging.ImageFormat]::Png)
            return $true
        }
        finally {
            $bitmap.Dispose()
            $icon.Dispose()
        }
    }
    catch {
        return $false
    }
}

function Find-UwpIconPng {
    param(
        [string] $InstallLocation
    )

    if (-not (Test-Path -LiteralPath $InstallLocation)) {
        return $null
    }

    # Search for candidate square logos in package assets
    $candidates = @(Get-ChildItem -Path $InstallLocation -Recurse -Filter '*.png' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'Square44x44Logo|Square150x150Logo|Logo|icon' -and $_.Name -notmatch 'targetsize-16|targetsize-24' } |
        Sort-Object -Property Length -Descending)

    if ($candidates.Count -gt 0) {
        return $candidates[0].FullName
    }

    return $null
}

if (-not (Test-Path -LiteralPath $IconDirectory)) {
    New-Item -ItemType Directory -Path $IconDirectory -Force | Out-Null
}

$entries = [System.Collections.Generic.List[object]]::new()
$seenNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

# 1. Scan Win32 Start Menu Shortcuts
$shell = New-Object -ComObject WScript.Shell
foreach ($root in $StartMenuRoots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        continue
    }

    $catalogRoot = (Resolve-Path -LiteralPath $root).Path
    foreach ($shortcut in Get-ChildItem -LiteralPath $root -Filter '*.lnk' -File -Recurse) {
        try {
            $link = $shell.CreateShortcut($shortcut.FullName)
            $target = [string]$link.TargetPath

            # Filter non-launchable or circular WSL/Linux shortcuts
            if ([string]::IsNullOrWhiteSpace($target)) { continue }
            if ($target -match 'wslg\.exe|wsl\.exe|ubuntu.*\.exe|bash\.exe') { continue }
            if ($target -match 'uninstall|unins[0-9]*\.exe') { continue }

            $appName = [System.IO.Path]::GetFileNameWithoutExtension($shortcut.Name)
            if ($seenNames.Contains($appName)) { continue }

            $category = Classify-Application -Name $appName -Target $target -HintCategory 'Other'
            $id = Get-StableId -Text "${appName}:${target}"
            $iconPng = Join-Path $IconDirectory "$id.png"

            $iconExtracted = $false
            if (-not [string]::IsNullOrWhiteSpace($link.IconLocation) -and (Test-Path -LiteralPath ($link.IconLocation -split ',', 2)[0])) {
                $iconExtracted = Extract-Win32IconToPng -SourcePath ($link.IconLocation -split ',', 2)[0] -DestinationPng $iconPng
            }
            if (-not $iconExtracted -and (Test-Path -LiteralPath $target)) {
                $iconExtracted = Extract-Win32IconToPng -SourcePath $target -DestinationPng $iconPng
            }

            $entries.Add([pscustomobject]@{
                id = $id
                name = $appName
                category = $category
                arguments = if ($null -eq $link.Arguments) { @() } else { @([string]$link.Arguments) }
                source = $shortcut.FullName
                target = $target
                icon = if ($iconExtracted) { $iconPng } else { $null }
                kind = 'windows-win32'
            })
            $seenNames.Add($appName) | Out-Null
        }
        catch {
            Write-Verbose "Skipping shortcut '$($shortcut.FullName)': $($_.Exception.Message)"
        }
    }
}

# 2. Scan UWP / Packaged Applications
try {
    $uwpApps = Get-StartApps -ErrorAction SilentlyContinue | Where-Object { $_.AppID -like '*!*' }
    if ($uwpApps) {
        # Build cache of AppX package install locations
        $packageCache = @{}
        foreach ($pkg in (Get-AppxPackage -ErrorAction SilentlyContinue)) {
            $packageCache[$pkg.PackageFamilyName] = $pkg.InstallLocation
        }

        foreach ($app in $uwpApps) {
            $appName = $app.Name
            $appId = $app.AppID

            if ($seenNames.Contains($appName)) { continue }
            if ($appId -match 'wsl|ubuntu') { continue }

            $family = ($appId -split '!')[0]
            $installLoc = $packageCache[$family]

            $category = Classify-Application -Name $appName -Target $appId -HintCategory 'Utility'
            $id = Get-StableId -Text "uwp:$appId"
            $iconPng = Join-Path $IconDirectory "$id.png"

            $iconExtracted = $false
            if ($installLoc) {
                $sourceLogo = Find-UwpIconPng -InstallLocation $installLoc
                if ($sourceLogo) {
                    try {
                        Copy-Item -LiteralPath $sourceLogo -Destination $iconPng -Force
                        $iconExtracted = $true
                    }
                    catch {
                        $iconExtracted = $false
                    }
                }
            }

            $entries.Add([pscustomobject]@{
                id = $id
                name = $appName
                category = $category
                arguments = @()
                source = $appId
                target = $appId
                icon = if ($iconExtracted) { $iconPng } else { $null }
                kind = 'windows-uwp'
            })
            $seenNames.Add($appName) | Out-Null
        }
    }
}
catch {
    Write-Verbose "UWP enumeration failed: $($_.Exception.Message)"
}

$catalog = @($entries | Sort-Object name, id)
$outDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$json = if ($catalog.Count -eq 0) { '[]' } else { $catalog | ConvertTo-Json -Depth 5 }
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Output "Discovered $($catalog.Count) Windows applications (Win32 & UWP). Catalog written to $OutputPath."
