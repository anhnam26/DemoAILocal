$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$archiveRoot='D:\CyberAnt-Local-Archive-20260928'
if ($taskRoot -ne 'D:\TestSystem' -or -not (Test-Path -LiteralPath $archiveRoot)) { throw 'Unexpected paths' }
$targets=@('system_runtime.py','runtime_limits.py','download_model.py','check_local_mode.py','check_memory.ps1','inspect_processes.ps1','Start-Demo.ps1','Stop-Demo.ps1','Restart-App.ps1','Backup-Data.py','test_runtime_limits.py','audit_knowledge.py','evaluate_rag.py','check_unified.py','testing_accounts.py','LUONG_HOAT_DONG.txt','examples','docs','logs','__pycache__','.pytest_cache','data/sources','data/demo.sqlite3','data/initial-accounts.json','data/knowledge_documents.json','data/knowledge_manifest.json','data/model-api-key.txt','data/runtime-config.json')
foreach ($relative in $targets) {
    $target=[IO.Path]::GetFullPath((Join-Path $taskRoot $relative))
    if (-not $target.StartsWith($taskRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Target outside workspace' }
    if (Test-Path -LiteralPath $target) {
        $resolved=(Resolve-Path -LiteralPath $target).Path
        if (-not $resolved.StartsWith($taskRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid resolved path' }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
Write-Output 'Removed obsolete runtime, derived duplicates, legacy docs and generated files. Local copy is outside the project.'
