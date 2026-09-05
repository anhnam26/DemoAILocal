$ErrorActionPreference = 'Stop'
$modelExe = Join-Path $PSScriptRoot 'runtime\llama-server.exe'
$pythonExe = Join-Path $PSScriptRoot '.venv-runtime\Scripts\python.exe'
$owned = @(Get-CimInstance Win32_Process | Where-Object { ($_.ExecutablePath -eq $modelExe -and $_.CommandLine -like '*cyberant-qwen3.5-9b*') -or ($_.ExecutablePath -eq $pythonExe -and $_.CommandLine -like '*uvicorn app:app*') })
foreach ($demoProcess in $owned) {
        $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $demoProcess.ProcessId -and $_.CommandLine -like '*uvicorn app:app*' })
        foreach ($child in $children) { Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $demoProcess.ProcessId -ErrorAction SilentlyContinue
        Write-Output ('Stopped demo process '+$demoProcess.ProcessId)
}
Write-Output 'Demo stopped. Data and model files are retained.'
