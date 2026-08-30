$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataset = if ($args.Count -gt 0) { $args[0] } else { "bidmc" }
$env:PYTHONPATH = Join-Path $repoRoot "ml"
$mlPython = Join-Path $repoRoot "ml/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $mlPython)) {
    throw "Create the Python 3.12 environment first: py -3.12 -m venv ml/.venv"
}

& $mlPython -m sensor_intelligence.cli download $dataset
if ($LASTEXITCODE -ne 0) {
    throw "Dataset acquisition failed for $dataset"
}
