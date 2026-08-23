$ErrorActionPreference = "Stop"
$locationPushed = $false
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv/Scripts/python.exe"

$python = if (Test-Path $venvPython -PathType Leaf) {
    $venvPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    "python3"
} else {
    throw "Python was not found. Install Python and ensure python or python3 is available in PATH."
}

try {
    $env:DISCORD_TOKEN = Read-Host "Discord Bot Token" -MaskInput

    if ([string]::IsNullOrWhiteSpace($env:DISCORD_TOKEN)) {
        throw "A Discord bot token is required."
    }

    Push-Location $projectRoot
    $locationPushed = $true
    & $python main.py
} finally {
    Remove-Item Env:DISCORD_TOKEN -ErrorAction SilentlyContinue

    if ($locationPushed) {
        Pop-Location
    }
}
