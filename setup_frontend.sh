#!/bin/bash
# Frontend Setup Script
# Initializes React + TypeScript frontend project

echo "=========================================="
echo "Frontend Setup - React + TypeScript"
echo "=========================================="

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js version: $NODE_VERSION"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm."
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "✅ npm version: $NPM_VERSION"

# Navigate to frontend directory
cd frontend || exit 1

# Initialize Vite + React + TypeScript project
echo ""
echo "📦 Initializing Vite + React + TypeScript project..."
npm create vite@latest . -- --template react-ts

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Install additional dependencies
echo ""
echo "📦 Installing additional dependencies (MUI, Redux, Router, etc.)..."
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install @reduxjs/toolkit react-redux
npm install react-router-dom
npm install axios
npm install recharts
npm install @types/react @types/react-dom

echo ""
echo "✅ Frontend setup complete!"
echo ""
echo "💡 Next steps:"
echo "  1. cd frontend"
echo "  2. npm run dev"
echo "  3. Open http://localhost:5173"
