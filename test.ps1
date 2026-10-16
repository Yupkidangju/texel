param([switch]$SkipLint)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'prepare.ps1') -Dev
$pythonPath = Join-Path $PSScriptRoot '.runtime\python315\python.exe'
Push-Location $PSScriptRoot
try {
    & $pythonPath -m pytest -q --basetemp .cache\pytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not $SkipLint) {
        & $pythonPath -m ruff check texel tests scripts
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $pythonPath -m ruff format --check texel tests scripts
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} finally { Pop-Location }
