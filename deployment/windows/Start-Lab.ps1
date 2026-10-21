$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $projectPath
$pythonPath = (Get-Command python.exe -ErrorAction Stop).Source
& $pythonPath -m backend.server --lab --ensure-admin
