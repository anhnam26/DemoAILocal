param([string]$Python='python',[ValidateRange(1,65535)][int]$Port=8088)
$ErrorActionPreference='Stop'
$appRoot=(Resolve-Path -LiteralPath $PSScriptRoot).Path
$stateFile=Join-Path $appRoot "data\app-process-$Port.json"
$listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
if ($listeners.Count) {
    if (Test-Path -LiteralPath $stateFile) {
        $state=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        $running=Get-CimInstance Win32_Process -Filter ('ProcessId = '+[int]$state.ProcessId)
        if ($running -and $state.ProjectRoot -eq $appRoot -and $state.Created -eq $running.CreationDate.ToFileTimeUtc().ToString() -and $listeners.OwningProcess -contains $running.ProcessId) {
            Write-Output "App is already running at http://127.0.0.1:$Port"
            exit 0
        }
    }
    throw "Port $Port is already in use. No additional process was started."
}
$pythonExe=(Get-Command $Python -CommandType Application -ErrorAction Stop).Source
$logDir=Join-Path $appRoot 'data\logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stdout=Join-Path $logDir "app-$Port.stdout.log"
$stderr=Join-Path $logDir "app-$Port.stderr.log"
$appArgs=@('-m','uvicorn','app:app','--app-dir',('"'+$appRoot+'"'),'--host','127.0.0.1','--port',"$Port",'--workers','1','--no-proxy-headers')
$launcher=Start-Process -FilePath $pythonExe -ArgumentList $appArgs -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
for ($attempt=0;$attempt -lt 120;$attempt++) {
    Start-Sleep -Milliseconds 500
    $listener=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $running=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$listener.OwningProcess)
        $rootPattern='--app-dir\s+"?'+[regex]::Escape($appRoot)+'"?(?=\s|$)'
        if ($running.CommandLine -notmatch $rootPattern) { throw "Another process took port $Port. Inspect $stderr" }
        @{ProjectRoot=$appRoot;ProcessId=$running.ProcessId;Created=$running.CreationDate.ToFileTimeUtc().ToString();Port=$Port} | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
        Write-Output "App started in background: http://127.0.0.1:$Port"
        Write-Output "Stop with: powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-App.ps1 -Port $Port"
        exit 0
    }
    $launcher.Refresh()
    if ($launcher.HasExited) { throw "App could not start. Inspect $stderr" }
}
throw "Startup has not completed. Inspect $stderr before starting again."
