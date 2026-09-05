$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{TotalRAM_GB=[math]::Round($os.TotalVisibleMemorySize/1MB,2);FreeRAM_GB=[math]::Round($os.FreePhysicalMemory/1MB,2);UsedRAM_GB=[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/1MB,2)} | ConvertTo-Json
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Name,Id,@{N='WorkingSet_MB';E={[math]::Round($_.WorkingSet64/1MB)}},@{N='Private_MB';E={[math]::Round($_.PrivateMemorySize64/1MB)}} | ConvertTo-Json
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|llama|ollama' } | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath | ConvertTo-Json
& nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv
