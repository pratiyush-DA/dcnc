# Fix Setup Issues

**Date**: 2026-01-28  
**Issues Found**: Database connection error + Cryptography import error

---

## Issues Identified

### **Issue 1: Database Connection Error** 🔴

**Error**: `password authentication failed for user "user"`

**Root Cause**: 
- `setup_database.py` doesn't load `.env` file
- Uses default `postgresql://user:password@...` instead of `postgresql://postgres:password@...`
- Your `.env` file has correct URL, but script doesn't read it

**Fix Applied**: ✅ Added `load_dotenv()` to `setup_database.py`

---

### **Issue 2: Cryptography Import Error** 🔴

**Error**: `ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process`

**Root Cause**: 
- `cryptography` package version mismatch
- Compiled for Python 3.8 but running on Python 3.10
- Needs to be reinstalled/upgraded

**Fix Required**: Reinstall cryptography package

---

## Fixes to Apply

### **Fix 1: Database Connection** ✅ (Already Fixed)

The `setup_database.py` has been updated to load `.env` file.

### **Fix 2: Cryptography Package** ⚠️ (Action Required)

Run these commands:

```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Uninstall old cryptography
pip uninstall cryptography -y

# Reinstall cryptography (will compile for Python 3.10)
pip install cryptography --upgrade --force-reinstall

# Verify installation
python -c "import cryptography; print('✅ Cryptography OK')"
```

**Alternative** (if above doesn't work):

```powershell
# Reinstall all dependencies
pip install --upgrade --force-reinstall -r requirements-api.txt
```

---

## Step-by-Step Fix

### **Step 1: Fix Cryptography** (2 minutes)

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Reinstall cryptography
pip uninstall cryptography -y
pip install cryptography --upgrade --force-reinstall
```

### **Step 2: Verify PostgreSQL is Running** (30 seconds)

```powershell
# Check Docker container
docker ps

# Should see dcnc_postgres running
# If not, start it:
docker-compose up -d
```

### **Step 3: Verify .env File** (30 seconds)

Check your `.env` file has:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/dcnc_db
```

### **Step 4: Initialize Database** (1 minute)

```powershell
# Now this should work (reads from .env)
python setup_database.py
```

✅ **Expected Output**: "✅ Database tables created successfully!"

### **Step 5: Start API** (1 minute)

```powershell
# Start API (cryptography error should be fixed)
python run_api.py
```

✅ **Expected Output**: API running on http://localhost:8000

---

## Verification

After fixes, verify everything works:

```powershell
# 1. Test database connection
python -c "from backend.database.session import engine; print('✅ Database connection OK')"

# 2. Test cryptography
python -c "import cryptography; print('✅ Cryptography OK')"

# 3. Test API startup
python run_api.py
# Should see: "Uvicorn running on http://0.0.0.0:8000"
```

---

## Summary

✅ **Fixed**: `setup_database.py` now loads `.env` file  
⚠️ **Action Required**: Reinstall `cryptography` package

**Next Steps**:
1. Reinstall cryptography (see commands above)
2. Run `python setup_database.py` again
3. Start API with `python run_api.py`

---

**Last Updated**: 2026-01-28
