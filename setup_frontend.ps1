# Frontend Setup Script (PowerShell)
# Initializes React + TypeScript frontend project

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Frontend Setup - React + TypeScript" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check Node.js
try {
    $nodeVersion = node -v
    Write-Host "✅ Node.js version: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Check npm
try {
    $npmVersion = npm -v
    Write-Host "✅ npm version: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ npm not found. Please install npm." -ForegroundColor Red
    exit 1
}

# Navigate to frontend directory
if (-not (Test-Path "frontend")) {
    New-Item -ItemType Directory -Path "frontend"
}
Set-Location frontend

# Initialize Vite + React + TypeScript project
Write-Host ""
Write-Host "📦 Initializing Vite + React + TypeScript project..." -ForegroundColor Yellow
npm create vite@latest . -- --template react-ts

# Install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Install additional dependencies
Write-Host ""
Write-Host "📦 Installing additional dependencies (MUI, Redux, Router, etc.)..." -ForegroundColor Yellow
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install @reduxjs/toolkit react-redux
npm install react-router-dom
npm install axios
npm install recharts
npm install @types/react @types/react-dom

Write-Host ""
Write-Host "✅ Frontend setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Next steps:" -ForegroundColor Cyan
Write-Host "  1. cd frontend"
Write-Host "  2. npm run dev"
Write-Host "  3. Open http://localhost:5173"
