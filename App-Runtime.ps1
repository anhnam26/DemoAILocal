# Shared configuration and process identity for the Windows launchers.
function Get-AppRuntime([string]$Python, [string]$Root) {
    $pythonExe=(Get-Command $Python -CommandType Application -ErrorAction Stop).Source
    Push-Location -LiteralPath $Root
    try {
        $code=@'
import json
from cyberant import config
v=config.env();s=config.security()
print(json.dumps(dict(data=str(config.data_dir()),host=v.get('APP_HOST','127.0.0.1'),port=config.integer('APP_PORT',8088,1,65535),mode=s['mode'])))
'@
        $json=$code | & $pythonExe -B -
        if ($LASTEXITCODE -ne 0) { throw 'Invalid application configuration; no process was started.' }
        $runtime=$json | ConvertFrom-Json
        $runtime | Add-Member -NotePropertyName Python -NotePropertyValue $pythonExe
        return $runtime
    } finally { Pop-Location }
}

function Test-AppProcess($Process, [string]$Root, [int]$Port) {
    if (-not $Process) { return $false }
    $command=$Process.CommandLine
    $portPattern='--port\s+'+$Port+'(?=\s|$)'
    $mainPattern='"?'+[regex]::Escape((Join-Path $Root 'main.py'))+'"?(?=\s|$)'
    $legacyPattern='--app-dir\s+"?'+[regex]::Escape($Root)+'"?(?=\s|$)'
    return ($command -match $portPattern -and ($command -match $mainPattern -or
        ($command -match '\buvicorn\s+cyberant\.app:app\b' -and $command -match $legacyPattern)))
}

function Test-AppReady([string]$HostName, [int]$Port) {
    $address=if ($HostName -in @('0.0.0.0','::')) { '127.0.0.1' } else { $HostName }
    if ($address.Contains(':')) { $address="[$address]" }
    try {
        $ready=Invoke-RestMethod "http://${address}:$Port/api/ready" -TimeoutSec 2
        return ($ready.status -eq 'ready' -and $ready.layout_version -eq 1)
    } catch { return $false }
}