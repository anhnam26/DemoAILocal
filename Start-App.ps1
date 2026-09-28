param([string]$Python='python')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try { & $Python -m uvicorn app:app --host 127.0.0.1 --port 8088 --workers 1 --no-proxy-headers }
finally { Pop-Location }
