param([switch]$Dev)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime\python315'
$pythonPath = Join-Path $runtimeDir 'python.exe'
$downloadDir = Join-Path $projectRoot '.runtime\downloads'
$archivePath = Join-Path $downloadDir 'python-3.15.0-embed-amd64.zip'
$expectedHash = 'a6999bcbcbe56f937159ef79c2630260eca99f65f7860bc5cd20430324079a44'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    New-Item -ItemType Directory -Force -Path $downloadDir,$runtimeDir | Out-Null
    if (-not (Test-Path -LiteralPath $archivePath)) {
        Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.15.0/python-3.15.0-embed-amd64.zip' -OutFile $archivePath
    }
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
        throw 'Python archive SHA256 mismatch'
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDir
}
@('python315.zip','.','Lib\site-packages','..\..','import site') | Set-Content -LiteralPath (Join-Path $runtimeDir 'python315._pth') -Encoding ASCII
$lockPath = Join-Path $projectRoot $(if ($Dev) { 'requirements.lock' } else { 'requirements-runtime.lock' })
$markerPath = Join-Path $runtimeDir $(if ($Dev) { '.dependencies-dev.sha256' } else { '.dependencies.sha256' })
$lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
$needsInstall = -not (Test-Path -LiteralPath $markerPath)
if (-not $needsInstall) { $needsInstall = (Get-Content -LiteralPath $markerPath -Raw).Trim() -ne $lockHash }
if ($needsInstall) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv, then run prepare.ps1 again. See BUILD_GUIDE.md.' }
    $ErrorActionPreference = 'Continue'
    & uv --cache-dir (Join-Path $projectRoot '.cache\uv') pip install --python $pythonPath --target (Join-Path $runtimeDir 'Lib\site-packages') --only-binary :all: -r $lockPath 2>&1 | ForEach-Object { Write-Host $_ }
    $installExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($installExitCode -ne 0) { throw 'Dependency installation failed' }
    $lockHash | Set-Content -LiteralPath $markerPath -Encoding ASCII
}
& $pythonPath --version
if ($LASTEXITCODE -ne 0) { throw 'Python runtime failed' }
