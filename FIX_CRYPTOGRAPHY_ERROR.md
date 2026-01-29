# Fix Cryptography Import Error

**Error**: `ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process`

---

## Quick Fix

Run these commands in PowerShell:

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 2. Uninstall and reinstall cryptography
pip uninstall cryptography -y
pip install cryptography --upgrade --force-reinstall --no-cache-dir

# 3. Verify it works
python -c "import cryptography; print('✅ Cryptography OK')"
```

---

## Alternative Fix (If Above Doesn't Work)

```powershell
# Reinstall all authentication packages
pip uninstall cryptography pyjwt python-jose bcrypt -y
pip install cryptography --upgrade --force-reinstall --no-cache-dir
pip install pyjwt>=2.8.0 bcrypt>=4.0.0 "python-jose[cryptography]>=3.3.0"
```

---

## Why This Happens

The `cryptography` package contains compiled Rust code that must match your Python version. If it was compiled for Python 3.8 but you're running Python 3.10, you'll get this error.

**Solution**: Force reinstall so it compiles for your current Python version.

---

## After Fix

1. ✅ Run `python setup_database.py` (should work now)
2. ✅ Run `python run_api.py` (should start without errors)

---

**Last Updated**: 2026-01-28
