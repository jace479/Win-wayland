[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $CatalogPath,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $ApplicationId
)

$ErrorActionPreference = 'Stop'
$ApplicationId = $ApplicationId -replace '[^A-Za-z0-9:_-]', ''
$catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
$application = $null
foreach ($candidate in $catalog) {
    if ([string] $candidate.id -eq $ApplicationId) {
        $application = $candidate
        break
    }
}
if ($null -eq $application -or [string]::IsNullOrWhiteSpace($application.target)) {
    throw "Application ID is not present in the host catalog: $ApplicationId"
}

$target = [string] $application.target
$auditPath = Join-Path $env:ProgramData 'nt-plasma\launch.log'
try {
    New-Item -ItemType Directory -Path (Split-Path $auditPath) -Force | Out-Null
    Add-Content -LiteralPath $auditPath -Value "$(Get-Date -Format o) id=$ApplicationId name=$($application.name) target=$target"
}
catch {
    # Launch must continue if the optional audit location is unavailable.
}
$safeTarget = $target.Replace("'", "''")
if ($application.kind -eq 'windows-uwp') {
    # Launch UWP Application via AppsFolder
    $childCommand = "Start-Process 'shell:AppsFolder\$safeTarget'"
}
else {
    $workingDir = if (Test-Path -LiteralPath $target) { Split-Path -Parent $target } else { 'C:\Windows' }
    $safeWorkingDir = $workingDir.Replace("'", "''")
    $argsList = if ($application.arguments) {
        $joined = ($application.arguments | ForEach-Object { "'$($_ -replace "'", "''")'" }) -join ', '
        "-ArgumentList @($joined)"
    } else { "" }

    $childCommand = "Start-Process -FilePath '$safeTarget' $argsList -WorkingDirectory '$safeWorkingDir'"
}

& powershell.exe -NoProfile -Command $childCommand
if ($LASTEXITCODE -ne 0) {
    throw "Windows failed to launch application: $ApplicationId"
}

