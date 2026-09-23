[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $DistroName,

    [string] $LaunchScript = '/opt/nt-plasma/wsl/plasma-launch.sh',

    [int] $DelaySeconds = 10
)

$ErrorActionPreference = 'Stop'
$taskName = 'NT-Plasma KDE Session'
$wsl = (Get-Command wsl.exe).Source
$arguments = "-d `"$DistroName`" -- `"$LaunchScript`""
$action = New-ScheduledTaskAction -Execute $wsl -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT$DelaySeconds`S"

if ($PSCmdlet.ShouldProcess($taskName, 'Register per-user Scheduled Task')) {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Description 'Starts the NT-Plasma KDE Plasma session through Ubuntu WSL2 and WSLg.' `
        -Force | Out-Null
    Write-Output "Registered $taskName for $env:USERNAME."
}
