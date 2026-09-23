[CmdletBinding()]
param(
    [string[]] $StartMenuRoots = @(
        (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs')
    ),

    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'

function Get-StableApplicationId {
    param([Parameter(Mandatory)][string] $Path)

    $normalized = [System.IO.Path]::GetFullPath($Path).ToLowerInvariant()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $hash = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($hash.ComputeHash($bytes)) -replace '-').ToLowerInvariant()
    }
    finally {
        $hash.Dispose()
    }
}

function Get-ShortcutCatalogEntry {
    param(
        [Parameter(Mandatory)]
        [System.IO.FileInfo] $Shortcut,
        [Parameter(Mandatory)]
        [object] $Shell
    )

    $link = $Shell.CreateShortcut($Shortcut.FullName)
    $relativeCategory = $Shortcut.DirectoryName.Substring($script:CatalogRoot.Length).TrimStart('\')
    if ([string]::IsNullOrWhiteSpace($relativeCategory)) {
        $relativeCategory = 'Other'
    }

    [pscustomobject]@{
        id = Get-StableApplicationId -Path $Shortcut.FullName
        name = [System.IO.Path]::GetFileNameWithoutExtension($Shortcut.Name)
        category = $relativeCategory
        arguments = if ($null -eq $link.Arguments) { @() } else { @([string] $link.Arguments) }
        source = $Shortcut.FullName
        target = [string] $link.TargetPath
        icon = if ([string]::IsNullOrWhiteSpace($link.IconLocation)) { $null } else { ($link.IconLocation -split ',', 2)[0] }
        kind = 'windows-shortcut'
    }
}

$shell = New-Object -ComObject WScript.Shell
$entries = [System.Collections.Generic.List[object]]::new()

foreach ($root in $StartMenuRoots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        continue
    }

    $script:CatalogRoot = (Resolve-Path -LiteralPath $root).Path
    foreach ($shortcut in Get-ChildItem -LiteralPath $root -Filter '*.lnk' -File -Recurse) {
        try {
            $entry = Get-ShortcutCatalogEntry -Shortcut $shortcut -Shell $shell
            if ([string]::IsNullOrWhiteSpace($entry.target)) {
                Write-Verbose "Skipping non-launchable shell link '$($shortcut.FullName)'"
                continue
            }
            $entries.Add($entry)
        }
        catch {
            Write-Verbose "Skipping shortcut '$($shortcut.FullName)': $($_.Exception.Message)"
        }
    }
}

$catalog = @($entries | Sort-Object name, id)
if ($OutputPath) {
    $json = if ($catalog.Count -eq 0) { '[]' } else { $catalog | ConvertTo-Json -Depth 4 }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
else {
    if ($catalog.Count -eq 0) { '[]' } else { $catalog | ConvertTo-Json -Depth 4 }
}