# scripts/setup_dev_env.ps1
# Создаёт root .venv и component venv'ы при наличии requirements.
# Usage: .\scripts\setup_dev_env.ps1

param()
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Write-Host "Repository root: $repoRoot"

# Create root venv if missing
$rootVenv = Join-Path $repoRoot ".venv"
$nlpReq = Join-Path $repoRoot "nlp_core\requirements.txt"

if (-not (Test-Path $rootVenv)) {
    Write-Host "Creating root venv at $rootVenv"
    python -m venv $rootVenv
    $rootPip = Join-Path $rootVenv "Scripts\pip.exe"
    Write-Host "Upgrading pip and installing nlp_core requirements into root venv..."
    & $rootPip install --upgrade pip
    if (Test-Path $nlpReq) {
        & $rootPip install -r $nlpReq
    } else {
        Write-Host "No nlp_core/requirements.txt found - root venv created without packages."
    }
} else {
    Write-Host "Root venv already exists: $rootVenv"
}

function Create-ComponentVenvIfNeeded($compDir) {
    $req = Join-Path $compDir "requirements.txt"
    $venv = Join-Path $compDir ".venv"
    if (Test-Path $req) {
        if (Test-Path $venv) {
            Write-Host "Component venv exists: $venv"
        } else {
            Write-Host "Creating venv for $compDir at $venv"
            python -m venv $venv
            $pip = Join-Path $venv "Scripts\pip.exe"
            Write-Host "Installing requirements for $compDir"
            & $pip install --upgrade pip
            & $pip install -r $req
        }
    } else {
        Write-Host "No requirements for $compDir - skip component venv."
    }
}

Create-ComponentVenvIfNeeded (Join-Path $repoRoot "nlp_core")
Create-ComponentVenvIfNeeded (Join-Path $repoRoot "bim_core")

Write-Host ""
Write-Host "NOTE: MCP requires FreeCAD. Install FreeCAD manually."
Write-Host "To run MCP with system python, set:"
Write-Host '  $env:FREECAD_PATH = "C:\Program Files\FreeCAD 1.0\bin"'
Write-Host "Setup complete."
