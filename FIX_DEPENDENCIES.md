# Fix Dependencies Installation Issue

## Problem
You're getting `ModuleNotFoundError: No module named 'sqlalchemy'` when running `setup_database.py`.

## Root Cause
The dependencies haven't been installed yet, or the virtual environment isn't properly activated.

## Solution - Step by Step

### Step 1: Activate Virtual Environment

In your PowerShell terminal, run:

```powershell
# Navigate to project (if not already there)
cd "C:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` in your prompt.

### Step 2: Verify Python Path

```powershell
python -c "import sys; print(sys.executable)"
```

This should show a path with `venv` in it, not `C:\Program Files\Python310`.

### Step 3: Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### Step 4: Install Core Dependencies

Try installing one at a time to see which ones work:

```powershell
# Install SQLAlchemy first (needed for setup_database.py)
python -m pip install sqlalchemy

# If that works, install the rest
python -m pip install psycopg2-binary
python -m pip install fastapi
python -m pip install uvicorn
python -m pip install pydantic
python -m pip install python-multipart
python -m pip install pyjwt
python -m pip install bcrypt
python -m pip install "python-jose[cryptography]"
python -m pip install redis
python -m pip install pandas
python -m pip install numpy
```

### Alternative: Install All at Once

If individual installs work, try:

```powershell
python -m pip install sqlalchemy psycopg2-binary fastapi uvicorn pydantic python-multipart pyjwt bcrypt "python-jose[cryptography]" redis pandas numpy
```

### Step 5: Verify Installation

```powershell
python -c "import sqlalchemy; print('SQLAlchemy OK')"
python -c "import fastapi; print('FastAPI OK')"
```

### Step 6: Set Environment Variables

From your `.env` file, set these in PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/dcnc_db"
$env:JWT_SECRET_KEY="key"
```

### Step 7: Start PostgreSQL (if using Docker)

```powershell
# Start PostgreSQL container
docker-compose up -d

# Check if it's running
docker ps
```

### Step 8: Run Database Setup

```powershell
python setup_database.py
```

## If pip Still Can't Find Packages

### Option A: Use Trusted Hosts

```powershell
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org sqlalchemy
```

### Option B: Check Network/Firewall

1. Check if you can access https://pypi.org in browser
2. Check if firewall is blocking pip
3. Check if you're behind a corporate proxy

### Option C: Use System Python (Last Resort)

If venv doesn't work, install to system Python:

```powershell
# Deactivate venv first
deactivate

# Install to user directory
python -m pip install --user sqlalchemy psycopg2-binary fastapi uvicorn pydantic python-multipart pyjwt bcrypt "python-jose[cryptography]" redis pandas numpy
```

## Quick Test After Installation

```powershell
# Test imports
python -c "from sqlalchemy import create_engine; print('SQLAlchemy works!')"
python -c "from fastapi import FastAPI; print('FastAPI works!')"
python -c "import psycopg2; print('PostgreSQL driver works!')"
```

## Next Steps After Dependencies Are Installed

1. ✅ Dependencies installed
2. ⏭️ Set environment variables
3. ⏭️ Start PostgreSQL (docker-compose up -d)
4. ⏭️ Run: `python setup_database.py`
5. ⏭️ Test: `python test_auth_endpoints.py`

---

**Note**: If you continue having issues, the problem might be:
- Network connectivity to PyPI
- Corporate firewall/proxy
- Python/pip installation issues

In that case, you may need to:
- Configure pip to use a proxy
- Use an internal package mirror
- Reinstall Python/pip
