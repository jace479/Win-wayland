Get-Process | Where-Object { $_.ProcessName -match 'msrdc|wsl|weston|plasma|xwayland' } | Select-Object Id, ProcessName, MainWindowTitle, MainWindowHandle | Format-Table -AutoSize
