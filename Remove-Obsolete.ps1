$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$relativeTargets = @(
    '.local-internal','backups','logs','__pycache__','.pytest_cache',
    'data/company_documents','data/finance_documents','data/security_documents',
    'data/demo_documents.json','data/company_operations.json','data/company_manifest.json',
    'data/finance_documents.json','data/finance_manifest.json','data/service_catalog.json',
    'data/workflow_documents.json','data/security_documents.json','data/security_manifest.json',
    'NewData/data/indexes','NewData/data/legacy',
    'NewData/data/processed/example_customers.json','NewData/data/processed/example_customers.csv',
    'NewData/data/processed/example_requirements.json','NewData/data/processed/example_requirements.csv',
    'NewData/data/processed/example_bom.json','NewData/data/processed/example_bom.csv','NewData/data/processed/examples.jsonl',
    'seed_data.py','company_data.py','finance_data.py','finance_logic.py','workflow_data.py','security_data.py','business.py',
    'static/finance.js','test_company.py','test_finance.py','test_security.py',
    'check_company_ui.py','check_finance_ui.py','check_management_ui.py','check_ui.py','check_workspace_ui.py',
    'check_concurrent_chat.py','check_four_slots.py','check_readability.py','check_admin_budgets_ui.py',
    'benchmark_context.py','smoke_demo.py','check_model_control.py','check_runtime.py','check_documentation.py',
    'verify_clean_setup.py','validate_public_export.py','export_public.py','audit_public_secrets.py'
)
# Old reports/screenshots may embed the customer corpus. Keep only this migration's reports.
Get-ChildItem -LiteralPath (Join-Path $workspace 'artifacts') -Force | Where-Object { $_.Name -notin @('workspace_inventory.json','customer_cleanup.json') } | ForEach-Object { $relativeTargets += 'artifacts/'+$_.Name }
$removed = @()
foreach ($relativeTarget in $relativeTargets) {
    $target = [IO.Path]::GetFullPath((Join-Path $workspace $relativeTarget))
    if (-not $target.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Outside workspace: $target" }
    if (Test-Path -LiteralPath $target) {
        $resolved = (Resolve-Path -LiteralPath $target).Path
        if (-not $resolved.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Invalid resolved path: $resolved" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
        $removed += $relativeTarget
    }
}
$removed | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workspace 'artifacts/removed_obsolete.json') -Encoding UTF8
Write-Output ('Removed '+$removed.Count+' obsolete files/directories within '+$workspace)
