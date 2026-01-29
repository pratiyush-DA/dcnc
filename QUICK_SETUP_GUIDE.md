# Quick Setup Guide - Fixing Dependencies Issue

## Issue
You're getting `ModuleNotFoundError: No module named 'sqlalchemy'` because:
1. The virtual environment may not be properly activated
2. Dependencies need to be installed in the venv

## Solution

### Option 1: Use Docker Compose (Recommended)

You already have `docker-compose.yml` for PostgreSQL. Let's use it:

```powershell
# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps
```

### Option 2: Activate Virtual Environment Properly

```powershell
# Navigate to project directory
cd "C:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Verify you're in venv (should show (venv) in prompt)
python -c "import sys; print(sys.executable)"

# Install dependencies
python -m pip install --upgrade pip
python -m pip install sqlalchemy psycopg2-binary fastapi uvicorn pydantic python-multipart pyjwt bcrypt python-jose[cryptography] redis pandas numpy
```

### Option 3: Install in System Python (if venv doesn't work)

```powershell
# Install directly to system Python
python -m pip install --user sqlalchemy psycopg2-binary fastapi uvicorn pydantic python-multipart pyjwt bcrypt python-jose[cryptography] redis pandas numpy
```

### Option 4: Use pip with explicit index (if network issue)

```powershell
python -m pip install --index-url https://pypi.org/simple/ sqlalchemy psycopg2-binary
```

## After Installing Dependencies

1. **Set Environment Variables** (from your `.env` file):
```powershell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/dcnc_db"
$env:JWT_SECRET_KEY="key"
```

2. **Start PostgreSQL** (if using Docker):
```powershell
docker-compose up -d
```

3. **Initialize Database**:
```powershell
python setup_database.py
```

4. **Test**:
```powershell
python test_auth_endpoints.py
```

## Troubleshooting

### If pip still can't find packages:
1. Check internet connection
2. Try: `python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org sqlalchemy`
3. Check firewall/proxy settings

### If virtual environment isn't working:
1. Recreate venv: `python -m venv venv`
2. Activate: `.\venv\Scripts\Activate.ps1`
3. Install packages

### If PostgreSQL connection fails:
1. Check if PostgreSQL is running: `docker ps` or `pg_isready`
2. Verify DATABASE_URL matches your setup
3. Check PostgreSQL logs: `docker logs dcnc_postgres`
