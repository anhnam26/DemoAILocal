param([ValidateRange(1,65535)][int]$Port=8088)
$ErrorActionPreference='Stop'
$appRoot=(Resolve-Path -LiteralPath $PSScriptRoot).Path
$stateFile=Join-Path $appRoot "data\app-process-$Port.json"
$running=$null
if (Test-Path -LiteralPath $stateFile) {
    $state=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if ($state.ProjectRoot -ne $appRoot -or $state.Port -ne $Port) { throw 'Process record belongs to a different project or port.' }
    $candidate=Get-CimInstance Win32_Process -Filter ('ProcessId = '+[int]$state.ProcessId)
    if ($candidate -and $state.Created -eq $candidate.CreationDate.ToFileTimeUtc().ToString()) { $running=$candidate }
}
if (-not $running) {
    $listener=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $candidate=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$listener.OwningProcess)
        $rootPattern='--app-dir\s+"?'+[regex]::Escape($appRoot)+'"?(?=\s|$)'
        if ($candidate.CommandLine -notmatch $rootPattern) { throw "Port $Port belongs to an unrecognized process. Nothing was stopped." }
        $running=$candidate
    }
}
if (-not $running) {
    if (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile }
    Write-Output 'App is already stopped.'
    exit 0
}
if ($running.CommandLine -notmatch '\buvicorn\s+app:app\b' -or $running.CommandLine -notmatch ('--port\s+'+$Port+'(?=\s|$)')) {
    throw 'Process is not the expected application. Nothing was stopped.'
}
# Stop only this app; never terminate all Python processes.
Stop-Process -Id $running.ProcessId -ErrorAction Stop
Wait-Process -Id $running.ProcessId -Timeout 15 -ErrorAction SilentlyContinue
$remaining=Get-Process -Id $running.ProcessId -ErrorAction SilentlyContinue
if ($remaining -and -not $remaining.HasExited) { throw 'Application process did not stop.' }
if (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile }
Write-Output "App stopped (port $Port)."
