$ErrorActionPreference = 'Stop'
$demoRoot = $PSScriptRoot
$logRoot = Join-Path $demoRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$modelExe = Join-Path $demoRoot 'runtime\llama-server.exe'
$modelFile = Join-Path $demoRoot 'models\Qwen3.5-9B-Q4_K_M.gguf'
$pythonExe = Join-Path $demoRoot '.venv-runtime\Scripts\python.exe'
$keyFile = Join-Path $demoRoot 'data\model-api-key.txt'
$runtimeSettings = @{ context=4096; gpu_layers=99; cache_ram=256; parallel=2 }
$settingsFile = Join-Path $demoRoot 'data\runtime-config.json'
if (Test-Path -LiteralPath $settingsFile) {
    $savedSettings = Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($savedSettings.parallel) { $runtimeSettings.parallel = [int]$savedSettings.parallel }
    $runtimeSettings.context = [int]$savedSettings.context
    $runtimeSettings.gpu_layers = [int]$savedSettings.gpu_layers
    $runtimeSettings.cache_ram = [int]$savedSettings.cache_ram
    if ($runtimeSettings.parallel -lt 1 -or $runtimeSettings.parallel -gt 2 -or $runtimeSettings.context -lt 2048 -or $runtimeSettings.context -gt 8192 -or $runtimeSettings.gpu_layers -lt 0 -or $runtimeSettings.gpu_layers -gt 99 -or $runtimeSettings.cache_ram -lt 0 -or $runtimeSettings.cache_ram -gt 512) { throw 'Runtime settings outside supported demo limits.' }
}
foreach ($requiredFile in @($modelExe,$modelFile,$pythonExe)) {
    if (-not (Test-Path -LiteralPath $requiredFile)) { throw "Missing: $requiredFile. See README.md for setup." }
}
if (-not (Test-Path -LiteralPath $keyFile)) {
    & $pythonExe -c "import secrets,pathlib,sys; pathlib.Path(sys.argv[1]).write_text(secrets.token_urlsafe(48),encoding='utf8')" $keyFile
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate model API key. Run this script from its directory.' }
}
function Test-DemoEndpoint($url) {
    try { return (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2).StatusCode -eq 200 } catch { return $false }
}
$records = @()
$pidFile = Join-Path $logRoot 'processes.json'
if (-not (Test-DemoEndpoint 'http://127.0.0.1:1234/health')) {
    $listener = Get-NetTCPConnection -LocalPort 1234 -State Listen -ErrorAction SilentlyContinue
    if ($listener) { Write-Output 'Port 1234 is already starting or occupied. Existing process left unchanged.' }
    else {
        $modelArgs = @('-m',('"'+$modelFile+'"'),'--alias','cyberant-qwen3.5-9b','--device','Vulkan0','--gpu-layers',([string]$runtimeSettings.gpu_layers),'--ctx-size',([string]($runtimeSettings.context * $runtimeSettings.parallel)),'--parallel',([string]$runtimeSettings.parallel),'--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0','--batch-size','256','--ubatch-size','128','--cache-ram',([string]$runtimeSettings.cache_ram),'--host','127.0.0.1','--port','1234','--api-key-file',('"'+$keyFile+'"'),'--cors-origins','http://127.0.0.1:8088','--no-webui','--log-verbosity','4')
        $modelProcess = Start-Process -FilePath $modelExe -ArgumentList $modelArgs -WorkingDirectory $demoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'model.stdout.log') -RedirectStandardError (Join-Path $logRoot 'model.stderr.log') -PassThru
        $records += @{id=$modelProcess.Id;path=$modelExe;started=$modelProcess.StartTime.ToUniversalTime().ToString('o')}
        Write-Output ('Starting GPU model, PID '+$modelProcess.Id)
    }
}
if (-not (Test-DemoEndpoint 'http://127.0.0.1:8088/api/health')) {
    if (Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8088 is occupied. Existing service was not stopped.' }
    $appProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','app:app','--host','127.0.0.1','--port','8088') -WorkingDirectory $demoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'app.stdout.log') -RedirectStandardError (Join-Path $logRoot 'app.stderr.log') -PassThru
    $records += @{id=$appProcess.Id;path=$pythonExe;started=$appProcess.StartTime.ToUniversalTime().ToString('o')}
    Write-Output ('Starting web app, PID '+$appProcess.Id)
}
ConvertTo-Json -InputObject $records -Depth 4 | Set-Content -LiteralPath $pidFile -Encoding UTF8
Write-Output 'Demo: http://127.0.0.1:8088'
Write-Output 'Model may need 1-3 minutes for initial load. Logs are in TestSystem\logs.'
