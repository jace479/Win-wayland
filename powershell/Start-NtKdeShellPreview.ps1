[CmdletBinding()]
param(
    [string]$HostExecutable = (Join-Path $PSScriptRoot '..\host\DesktopSurfaceHost\bin\Debug\net8.0-windows\DesktopSurfaceHost.exe'),
    [switch]$HideExplorer,
    [switch]$StopExplorer,
    [switch]$NoRestartExplorer,
    [int]$ReadyTimeoutSeconds = 10
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $HostExecutable)) {
    throw "ntKDE host executable was not found: $HostExecutable"
}
$HostExecutable = (Resolve-Path -LiteralPath $HostExecutable).Path

$hostProcess = $null
$explorerWasRunning = @(Get-Process -Name explorer -ErrorAction SilentlyContinue).Count -gt 0
$hideScript = Join-Path $PSScriptRoot 'Hide-ExplorerComponents.ps1'

try {
    if ($HideExplorer -and (Test-Path $hideScript)) {
        & $hideScript -Action Hide
    }

    $hostProcess = Start-Process -FilePath $HostExecutable -WorkingDirectory (Split-Path -Parent $HostExecutable) -PassThru
    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
    while ($hostProcess.HasExited -eq $false -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
        $hostProcess.Refresh()
    }

    if ($hostProcess.HasExited) {
        throw "ntKDE host exited before readiness: $($hostProcess.ExitCode)"
    }

    if ($StopExplorer) {
        Get-Process -Name explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    }
    elseif ($HideExplorer) {
        Write-Output 'Preview started with Explorer components hidden.'
    }
    else {
        Write-Output 'Preview started without stopping Explorer. Use -HideExplorer or -StopExplorer to conceal Explorer.'
    }

    Wait-Process -Id $hostProcess.Id
}
finally {
    if ($hostProcess -and -not $hostProcess.HasExited) {
        Stop-Process -Id $hostProcess.Id -Force
    }

    if ($HideExplorer -and (Test-Path $hideScript)) {
        & $hideScript -Action Show
    }

    if ($explorerWasRunning -and -not $NoRestartExplorer) {
        if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) {
            Start-Process explorer.exe
        }
    }
}