# Manual Fix for Cryptography Error

**Error**: `ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process`

---

## Quick Fix (Recommended)

### Option 1: Run the Fix Script

```powershell
# Navigate to project directory
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"

# Run the fix script
.\fix_cryptography.ps1
```

---

### Option 2: Manual Commands

If the script doesn't work, run these commands **one at a time**:

```powershell
# 1. Navigate to project
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Check Python version (should be 3.10+)
python --version

# 4. Try to reinstall cryptography
python -m pip install cryptography --upgrade --force-reinstall --no-cache-dir

# 5. If that fails, try installing specific version
python -m pip install cryptography==46.0.4 --upgrade --force-reinstall --no-cache-dir

# 6. Verify it works
python -c "import cryptography; print('✅ Cryptography OK')"
```

---

### Option 3: Reinstall All Auth Packages

If Options 1 and 2 don't work:

```powershell
# Activate venv first
.\venv\Scripts\Activate.ps1

# Reinstall all authentication-related packages
python -m pip uninstall cryptography pyjwt python-jose bcrypt -y
python -m pip install cryptography --upgrade --force-reinstall --no-cache-dir
python -m pip install pyjwt>=2.8.0 bcrypt>=4.0.0 "python-jose[cryptography]>=3.3.0"
```

---

### Option 4: Reinstall All Dependencies

**Last resort** - reinstall everything:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Reinstall all API dependencies
python -m pip install -r requirements-api.txt --upgrade --force-reinstall --no-cache-dir
```

**Note**: This will take longer but ensures everything is compatible.

---

## Why This Happens

The `cryptography` package contains compiled Rust code (PyO3) that must match your Python version exactly. If it was installed for Python 3.8 but you're running Python 3.10, you'll get this error.

**Solution**: Force reinstall so it compiles/installs the correct version for Python 3.10.

---

## After Fixing

Once cryptography is fixed:

1. **Initialize Database**:
   ```powershell
   python setup_database.py
   ```

2. **Start API**:
   ```powershell
   python run_api.py
   ```

3. **Verify API is running**:
   - Open browser: http://localhost:8000/docs
   - Should see FastAPI Swagger UI

---

## Troubleshooting

### If pip can't find cryptography:

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Then try again
python -m pip install cryptography --upgrade --force-reinstall
```

### If you get permission errors:

- Close any Python processes (IDEs, terminals)
- Run PowerShell as Administrator
- Try again

### If OneDrive is syncing:

- Wait for OneDrive sync to complete
- Or temporarily pause OneDrive sync
- Then try the fix

---

## Verification

After fixing, verify everything works:

```powershell
# Test cryptography import
python -c "import cryptography; print('✅ Cryptography OK')"

# Test JWT import (uses cryptography)
python -c "import jwt; print('✅ JWT OK')"

# Test API startup
python run_api.py
# Should see: "Uvicorn running on http://0.0.0.0:8000"
```

---

**Last Updated**: 2026-01-28
