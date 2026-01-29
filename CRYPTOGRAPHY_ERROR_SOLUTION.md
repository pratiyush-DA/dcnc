# Cryptography Error - Complete Solution

**Error**: `ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process`

---

## Root Cause

This error occurs when:
1. **Cryptography was compiled for Python 3.8** but you're running **Python 3.10**
2. **Python subinterpreters** are being used (like with uvicorn workers)
3. The cryptography package needs to be **rebuilt for your Python version**

**Your Setup**:
- Python: 3.10.0rc2
- Cryptography: 46.0.3 (installed, but wrong build)

---

## Solution Options

### **Option 1: Reinstall Cryptography (Recommended)**

**If pip network is working:**

```powershell
# Activate venv
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"
.\venv\Scripts\Activate.ps1

# Reinstall cryptography
python -m pip install cryptography --upgrade --force-reinstall --no-cache-dir

# Verify
python -c "import cryptography; print('✅ OK')"
```

**If pip can't find packages (network issue):**

1. **Check internet connection**
2. **Try different pip index:**
   ```powershell
   python -m pip install cryptography --upgrade --force-reinstall --index-url https://pypi.org/simple/
   ```

3. **Or use pip with trusted hosts:**
   ```powershell
   python -m pip install cryptography --upgrade --force-reinstall --trusted-host pypi.org --trusted-host files.pythonhosted.org
   ```

---

### **Option 2: Recreate Virtual Environment (Nuclear Option)**

If reinstalling doesn't work, create a fresh venv:

```powershell
# 1. Deactivate current venv (if active)
deactivate

# 2. Remove old venv
Remove-Item -Recurse -Force .\venv

# 3. Create new venv
python -m venv venv

# 4. Activate new venv
.\venv\Scripts\Activate.ps1

# 5. Upgrade pip
python -m pip install --upgrade pip

# 6. Install all dependencies
python -m pip install -r requirements-api.txt

# 7. Verify
python -c "import cryptography; print('✅ OK')"
```

---

### **Option 3: Use Single Worker (Temporary Workaround)**

If you can't fix cryptography immediately, run API with 1 worker:

```powershell
# In .env file, set:
API_WORKERS=1

# Or run directly:
python run_api.py
# (This already defaults to 1 worker)
```

This avoids subinterpreter issues but limits scalability.

---

### **Option 4: Download Wheel Manually**

If pip completely fails:

1. **Download wheel from**: https://pypi.org/project/cryptography/#files
2. **Find wheel for Python 3.10 Windows 64-bit**: `cryptography-46.0.4-cp310-cp310-win_amd64.whl`
3. **Install manually**:
   ```powershell
   python -m pip install path\to\downloaded\cryptography-46.0.4-cp310-cp310-win_amd64.whl --force-reinstall
   ```

---

## Verification Steps

After applying any fix:

```powershell
# 1. Test cryptography import
python -c "import cryptography; print(f'✅ Cryptography {cryptography.__version__} OK')"

# 2. Test JWT (uses cryptography)
python -c "import jwt; print('✅ JWT OK')"

# 3. Test API startup
python run_api.py
# Should see: "Uvicorn running on http://0.0.0.0:8000" without errors
```

---

## Why Pip Can't Find Packages

If you're getting `ERROR: Could not find a version that satisfies the requirement`, it's likely:

1. **Network/Firewall issue** - Check internet connection
2. **Corporate proxy** - May need proxy settings
3. **DNS issue** - Try: `python -m pip install cryptography --index-url https://pypi.org/simple/`
4. **Pip cache corruption** - Clear cache: `python -m pip cache purge`

---

## Quick Diagnostic

Run this to check your setup:

```powershell
# Check Python version
python --version
# Should be: Python 3.10.x

# Check pip version
python -m pip --version

# Check cryptography
python -c "import cryptography; print(cryptography.__version__)"

# Test pip connectivity
python -m pip search cryptography
# (If this fails, pip can't reach PyPI)
```

---

## Recommended Action Plan

1. **First**: Try Option 1 (reinstall cryptography)
2. **If that fails**: Try Option 2 (recreate venv) - This is most reliable
3. **If still failing**: Check network/proxy settings
4. **Temporary**: Use Option 3 (single worker) to get API running

---

## After Fixing

Once cryptography is fixed:

```powershell
# 1. Initialize database
python setup_database.py

# 2. Start API
python run_api.py

# 3. Test in browser
# Open: http://localhost:8000/docs
```

---

**Last Updated**: 2026-01-28  
**Status**: Waiting for pip network connectivity or manual wheel installation
