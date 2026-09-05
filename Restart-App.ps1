$ErrorActionPreference = 'Stop'
$demoRoot = $PSScriptRoot
$pythonExe = Join-Path $demoRoot '.venv-runtime\Scripts\python.exe'
$processes = @(Get-CimInstance Win32_Process)
$parents = @($processes | Where-Object { $_.ExecutablePath -eq $pythonExe -and $_.CommandLine -match 'uvicorn\s+app:app' })
foreach ($parent in $parents) {
    $children = @($processes | Where-Object { $_.ParentProcessId -eq $parent.ProcessId -and $_.CommandLine -match 'uvicorn\s+app:app' })
    foreach ($child in $children) { Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 800
& (Join-Path $demoRoot 'Start-Demo.ps1')
