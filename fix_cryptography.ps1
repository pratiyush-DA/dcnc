# Fix Cryptography Import Error
# Run this script in PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Cryptography Import Error" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version
Write-Host "Python: $pythonVersion" -ForegroundColor Green

# Try to reinstall cryptography
Write-Host ""
Write-Host "Attempting to reinstall cryptography..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Yellow

# Method 1: Try with specific version
Write-Host ""
Write-Host "Method 1: Installing cryptography 46.0.4 (latest)..." -ForegroundColor Yellow
python -m pip install cryptography==46.0.4 --upgrade --force-reinstall --no-cache-dir

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Cryptography reinstalled successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Method 1 failed. Trying Method 2..." -ForegroundColor Yellow
    Write-Host "Method 2: Installing from requirements..." -ForegroundColor Yellow
    python -m pip install "python-jose[cryptography]>=3.3.0" --upgrade --force-reinstall --no-cache-dir
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
python -c "import cryptography; print(f'✅ Cryptography {cryptography.__version__} OK')"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ Fix Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Run: python setup_database.py" -ForegroundColor White
    Write-Host "2. Run: python run_api.py" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "⚠️  Manual Fix Required" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please try these commands manually:" -ForegroundColor Yellow
    Write-Host "  pip uninstall cryptography -y" -ForegroundColor White
    Write-Host "  pip install cryptography --upgrade --force-reinstall" -ForegroundColor White
    Write-Host ""
    Write-Host "Or reinstall all dependencies:" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements-api.txt --upgrade --force-reinstall" -ForegroundColor White
}
