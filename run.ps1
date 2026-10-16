param(
    [switch]$Demo,
    [switch]$Mcp,
    [string]$Workbook = '',
    [string]$Root = '',
    [ValidateSet('ko','en')][string]$Language = 'ko'
)
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.runtime\python315\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { & (Join-Path $PSScriptRoot 'prepare.ps1') }
Push-Location $PSScriptRoot
try {
    if (-not $Workbook) { $Workbook = Join-Path $PSScriptRoot 'data\Workbook.texel' }
    $workbookPath = [IO.Path]::GetFullPath($Workbook)
    $ErrorActionPreference = 'Continue'
    if ($Mcp) {
        if (-not $Root) { $Root = [IO.Path]::GetDirectoryName($workbookPath) }
        & $pythonPath -m texel mcp --workbook $workbookPath --root ([IO.Path]::GetFullPath($Root))
    } else {
        $arguments = @('-m','texel','tui','--workbook',$workbookPath,'--language',$Language)
        if ($Demo) { $arguments += '--demo' }
        & $pythonPath @arguments
    }
    $result = $LASTEXITCODE
} finally { Pop-Location }
exit $result
