# ==============================================================================
# Kill-NtKde.ps1 - Immediate Recovery & Termination of ntKDE
# ==============================================================================
[CmdletBinding()]
param()

$repoRoot = Split-Path -Parent $PSScriptRoot
$ntkdeExe = Join-Path $repoRoot "bin\ntkde.exe"

if (Test-Path $ntkdeExe) {
    & $ntkdeExe kill
} else {
    Write-Host "[ntKDE] Running standalone emergency kill..." -ForegroundColor Yellow
    
    # 1. Unhide Explorer
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class QuickUnhide {
        [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
"@ -ErrorAction SilentlyContinue

    $h = [QuickUnhide]::FindWindow("Shell_TrayWnd", $null)
    if ($h -ne [IntPtr]::Zero) { [QuickUnhide]::ShowWindow($h, 5) }

    # 2. Kill WSL plasma
    wsl.exe -d Ubuntu -u jace479 bash -c "pkill -u \$(id -u) -9 -f 'plasmashell|kwin|start-panels|kde-task-bridge' 2>/dev/null || true"

    # 3. Kill host processes
    Get-Process -Name "ntkde", "DesktopSurfaceHost" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "[ntKDE] Done." -ForegroundColor Green
}
