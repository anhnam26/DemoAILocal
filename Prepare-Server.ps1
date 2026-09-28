$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$archiveRoot='D:\CyberAnt-Local-Archive-20260928'
if (Test-Path -LiteralPath $archiveRoot) { throw 'Archive already exists; refusing overwrite.' }
if ($taskRoot -ne 'D:\TestSystem' -or [IO.Path]::GetFullPath($archiveRoot) -ne $archiveRoot) { throw 'Unexpected paths.' }
& (Join-Path $taskRoot 'Stop-Demo.ps1')
New-Item -ItemType Directory -Path $archiveRoot | Out-Null
# Preserve the functioning local application before changing the server code.
Get-ChildItem -LiteralPath $taskRoot -File | Where-Object { $_.Extension -in @('.py','.ps1','.txt','.md') -or $_.Name -eq '.env' } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $archiveRoot }
foreach ($relative in @('static','data','docs','examples')) {
    Copy-Item -LiteralPath (Join-Path $taskRoot $relative) -Destination $archiveRoot -Recurse
}
foreach ($relative in @('models','runtime','DataReal','NewData','artifacts','.venv','.venv-runtime')) {
    $source=[IO.Path]::GetFullPath((Join-Path $taskRoot $relative))
    $target=[IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
    if (-not $source.StartsWith($taskRoot+'\') -or -not $target.StartsWith($archiveRoot+'\')) { throw 'Invalid move path' }
    if (Test-Path -LiteralPath $target) { throw 'Destination exists' }
    if (Test-Path -LiteralPath $source) { Move-Item -LiteralPath $source -Destination $target }
}
Write-Output ('Local application archived at '+$archiveRoot)
