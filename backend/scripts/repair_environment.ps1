# Phoenix Protocol: Final Dependency Repair
$ErrorActionPreference = "Stop"

Write-Host "--- Purging & Rebuilding Dependencies ---" -ForegroundColor Cyan

# 1. Force remove existing LangChain artifacts
Write-Host "Removing existing LangChain versions..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip uninstall -y langchain langchain-community langchain-core langchain-openai langchain-text-splitters

# 2. Re-install from requirements
Write-Host "Installing stable pinned dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r backend/requirements.txt

Write-Host "--- Repair Complete ---" -ForegroundColor Green