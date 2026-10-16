param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'prepare.ps1') -Dev
if (-not $SkipTests) {
    & (Join-Path $PSScriptRoot 'test.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
}
$pythonPath = Join-Path $PSScriptRoot '.runtime\python315\python.exe'
Push-Location $PSScriptRoot
try {
    $ErrorActionPreference = 'Continue'
    & $pythonPath -m hatchling build -t wheel
    if ($LASTEXITCODE -ne 0) { throw 'Wheel build failed' }
    & $pythonPath scripts\package.py
    if ($LASTEXITCODE -ne 0) { throw 'Portable bundle failed' }
} finally { Pop-Location }
