$root=$PSScriptRoot
Get-Content -LiteralPath (Join-Path $root 'logs\processes.json')
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like ($root+'\*') -or $_.CommandLine -like '*uvicorn app:app*' } | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json
foreach ($r in @(Get-Content -LiteralPath (Join-Path $root 'logs\processes.json') -Raw | ConvertFrom-Json)) {
    $p=Get-Process -Id $r.id -ErrorAction SilentlyContinue
    if ($p) { Write-Output ($p.Id.ToString()+' '+$p.StartTime.ToUniversalTime().ToString('o')+' '+$p.Path) }
}
