# Phoenix Protocol: Advocatus Hardware-Aware Launcher
# Optimized for: 8GB RAM / Windows AMD64
$ErrorActionPreference = "Stop"

Write-Host "--- Initializing Memory-Optimized Boot ---" -ForegroundColor Cyan

# 1. Ensure Environment is active
if ($null -eq $env:VIRTUAL_ENV) {
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        Write-Host "Activating local environment..." -ForegroundColor Gray
        . .\.venv\Scripts\Activate.ps1
    } else {
        Write-Host "ERROR: .venv not found. Run repair_environment.ps1" -ForegroundColor Red
        exit
    }
}

# 2. Path Integrity
$env:PYTHONPATH = "$(Get-Location)\backend"
Write-Host "PYTHONPATH aligned to backend source." -ForegroundColor Gray

# 3. Launch with Resource Constraints
# --no-use-colors: Reduces terminal buffer load
# --workers 1: Prevents multi-process RAM exhaustion
# --log-level info: Keeps memory clear of debug bloat
Write-Host "Starting FastAPI on http://127.0.0.1:8000" -ForegroundColor Green
python -m uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --app-dir backend `
    --workers 1 `
    --no-use-colors `
    --log-level info