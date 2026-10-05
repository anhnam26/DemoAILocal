param([string]$Python='python',[ValidateRange(1,65535)][int]$Port=8088)
$ErrorActionPreference='Stop'
$appRoot=(Resolve-Path -LiteralPath $PSScriptRoot).Path
. (Join-Path $appRoot 'App-Runtime.ps1')
$runtime=Get-AppRuntime $Python $appRoot
if (-not $PSBoundParameters.ContainsKey('Port')) { $Port=$runtime.port }
if ($runtime.mode -eq 'development' -and $runtime.host -notin @('127.0.0.1','localhost','::1')) {
    throw 'Development must bind loopback; configure lan/production for network access.'
}
$stateFile=Join-Path $runtime.data "app-process-$Port.json"
$listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
if ($listeners.Count) {
    if (Test-Path -LiteralPath $stateFile) {
        $state=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        $running=Get-CimInstance Win32_Process -Filter ('ProcessId = '+[int]$state.ProcessId)
        if ((Test-AppProcess $running $appRoot $Port) -and $state.ProjectRoot -eq $appRoot -and $state.Created -eq $running.CreationDate.ToFileTimeUtc().ToString() -and $listeners.OwningProcess -contains $running.ProcessId -and (Test-AppReady $runtime.host $Port)) {
            Write-Output "App is already ready on port $Port"
            exit 0
        }
    }
    throw "Port $Port is already in use. No additional process was started."
}
$pythonExe=$runtime.Python
Push-Location -LiteralPath $appRoot
try {
    & $pythonExe -B -c 'from cyberant import config,storage;storage.validate(config.data_dir(),integrity=True)'
    if ($LASTEXITCODE -ne 0) { throw 'Data validation failed. Check APP_DATA_DIR; no empty data directory was created.' }
} finally { Pop-Location }
$logDir=Join-Path $runtime.data 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stdout=Join-Path $logDir "app-$Port.stdout.log"
$stderr=Join-Path $logDir "app-$Port.stderr.log"
$appArgs=@('-B',('"'+(Join-Path $appRoot 'main.py')+'"'),'--host',$runtime.host,'--port',"$Port")
$launcher=Start-Process -FilePath $pythonExe -ArgumentList $appArgs -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
for ($attempt=0;$attempt -lt 120;$attempt++) {
    Start-Sleep -Milliseconds 500
    $listener=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $running=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$listener.OwningProcess)
        if (-not (Test-AppProcess $running $appRoot $Port)) { throw "Another process took port $Port. Inspect $stderr" }
        @{ProjectRoot=$appRoot;ProcessId=$running.ProcessId;Created=$running.CreationDate.ToFileTimeUtc().ToString();Port=$Port} | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
        if (-not (Test-AppReady $runtime.host $Port)) { continue }
        Write-Output "App ready in background: http://$($runtime.host):$Port"
        Write-Output "Stop with: powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-App.ps1 -Port $Port"
        exit 0
    }
    $launcher.Refresh()
    if ($launcher.HasExited) { throw "App could not start. Inspect $stderr" }
}
throw "Startup has not completed. Inspect $stderr before starting again."
