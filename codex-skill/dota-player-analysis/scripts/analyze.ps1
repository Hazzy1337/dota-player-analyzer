param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AnalyzerArgs
)

$projectRoot = $env:DOTA_PLAYER_ANALYZER_HOME
if (-not $projectRoot) {
    $projectRoot = 'P:\dota-player-analyzer'
}
if (-not (Test-Path -LiteralPath $projectRoot)) {
    throw "Dota Player Analyzer project not found. Set DOTA_PLAYER_ANALYZER_HOME."
}
Push-Location $projectRoot
try {
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $projectPython) {
        & $projectPython -m dota_analyzer @AnalyzerArgs
    }
    else {
        & python -m dota_analyzer @AnalyzerArgs
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
