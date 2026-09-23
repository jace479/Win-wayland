$d = Get-Item 'C:\Users\jace.zorn\Desktop' -ErrorAction SilentlyContinue
if ($d -and $d.LinkType -eq 'Junction') {
    $d.Delete()
    Write-Host "Removed Desktop junction."
}

$p = Get-Item 'C:\Users\jace.zorn\Pictures' -ErrorAction SilentlyContinue
if ($p -and $p.LinkType -eq 'Junction') {
    $p.Delete()
    Write-Host "Removed Pictures junction."
}
