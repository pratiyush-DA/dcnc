# Run and Test Frontend + Backend Together
# Run this script from the project root in PowerShell.
# Use two terminals: one for backend, one for frontend (or run backend in background).

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$TestOnly
)

$ProjectRoot = $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DCNC - Run and Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($TestOnly) {
    Write-Host "Testing endpoints (backend and frontend should already be running)..." -ForegroundColor Yellow
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -ErrorAction Stop
        Write-Host "[OK] Backend health: $($health.status)" -ForegroundColor Green
        Write-Host "     $($health | ConvertTo-Json -Compress)" -ForegroundColor Gray
    } catch {
        Write-Host "[FAIL] Backend not reachable at http://localhost:8000 - is it running?" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor Gray
    }
    try {
        $root = Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get -ErrorAction Stop
        Write-Host "[OK] Backend root: $($root.service) v$($root.version)" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Backend root not reachable" -ForegroundColor Red
    }
    try {
        $fe = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "[OK] Frontend reachable at http://localhost:5173 (status: $($fe.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Frontend not reachable at http://localhost:5173 - is it running?" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Done. Open http://localhost:5173 (frontend) and http://localhost:8000/api/docs (API docs)" -ForegroundColor Cyan
    exit 0
}

if (-not $FrontendOnly) {
    Write-Host "Backend (Terminal 1):" -ForegroundColor Yellow
    Write-Host "  cd `"$ProjectRoot`"" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  `$env:DATABASE_URL='postgresql://postgres:password@localhost:5432/dcnc_db'" -ForegroundColor White
    Write-Host "  `$env:JWT_SECRET_KEY='key'" -ForegroundColor White
    Write-Host "  python run_api.py" -ForegroundColor White
    Write-Host ""
}

if (-not $BackendOnly) {
    Write-Host "Frontend (Terminal 2):" -ForegroundColor Yellow
    Write-Host "  cd `"$FrontendDir`"" -ForegroundColor White
    Write-Host "  npm run dev" -ForegroundColor White
    Write-Host ""
}

Write-Host "After both are running, run:" -ForegroundColor Cyan
Write-Host "  .\run_and_test.ps1 -TestOnly" -ForegroundColor White
Write-Host ""
Write-Host "Or open in browser:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API docs:  http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  Health:    http://localhost:8000/api/v1/health" -ForegroundColor White
