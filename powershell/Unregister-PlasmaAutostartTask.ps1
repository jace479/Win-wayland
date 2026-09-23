[CmdletBinding(SupportsShouldProcess)]
param()

$ErrorActionPreference = 'Stop'
$taskName = 'NT-Plasma KDE Session'

if ($null -ne (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) {
    if ($PSCmdlet.ShouldProcess($taskName, 'Unregister Scheduled Task')) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output "Unregistered $taskName."
    }
}
else {
    Write-Output "$taskName is not registered."
}
