# Complete Setup Instructions

## Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 12+
- Redis (optional, for caching)

---

## Step 1: PostgreSQL Setup

1. **Install PostgreSQL** (if not installed)
   - Windows: Download from https://www.postgresql.org/download/windows/
   - macOS: `brew install postgresql`
   - Linux: `sudo apt-get install postgresql`

2. **Create Database**
   ```bash
   psql -U postgres
   CREATE DATABASE dcnc_db;
   \q
   ```

3. **Set Environment Variables**
   ```bash
   # Windows PowerShell
   $env:DATABASE_URL="postgresql://postgres:password@localhost:5432/dcnc_db"
   $env:JWT_SECRET_KEY="your-secret-key-change-this"
   
   # Linux/macOS
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/dcnc_db"
   export JWT_SECRET_KEY="your-secret-key-change-this"
   ```

---

## Step 2: Install Backend Dependencies

```bash
pip install -r requirements-api.txt
```

If that fails, install individually:
```bash
pip install fastapi uvicorn pydantic python-multipart pandas numpy
pip install sqlalchemy psycopg2-binary pyjwt bcrypt python-jose[cryptography] redis
```

---

## Step 3: Initialize Database

```bash
python setup_database.py
```

This will create all necessary tables.

---

## Step 4: Start Backend API

```bash
python run_api.py
```

Or with uvicorn:
```bash
uvicorn DCNC.api.app:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at: http://localhost:8000

---

## Step 5: Test Authentication

In a new terminal:
```bash
python test_auth_endpoints.py
```

Or test manually:
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Client", "email": "admin@test.com", "password": "Test123!@#"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "Test123!@#"}'
```

---

## Step 6: Setup Frontend

### Windows
```powershell
.\setup_frontend.ps1
```

### Linux/macOS
```bash
chmod +x setup_frontend.sh
./setup_frontend.sh
```

### Or Manually
```bash
cd frontend
npm install
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material
npm install @reduxjs/toolkit react-redux react-router-dom axios recharts
```

---

## Step 7: Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## Step 8: Test Full Stack

1. Open http://localhost:5173
2. Click "Register" to create a new client
3. Login with your credentials
4. You should see the dashboard

---

## Troubleshooting

### Database Connection Error
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL is correct
- Check database exists: `psql -l | grep dcnc_db`

### Import Errors
- Make sure all dependencies are installed
- Check Python version: `python --version` (should be 3.10+)
- Try: `pip install --upgrade pip`

### Frontend Build Errors
- Check Node.js version: `node -v` (should be 18+)
- Delete `node_modules` and `package-lock.json`, then `npm install`
- Check for TypeScript errors: `npm run build`

### Authentication Errors
- Verify JWT_SECRET_KEY is set
- Check token expiration (15 min for access, 7 days for refresh)
- Clear browser localStorage and try again

---

## Next Steps

1. ✅ Backend API running
2. ✅ Frontend running
3. ⏭️ Complete Dashboard features
4. ⏭️ Implement Classification UI
5. ⏭️ Implement Correction UI
6. ⏭️ Add Jobs history
7. ⏭️ Add Settings page

---

**Status**: ✅ Setup scripts ready  
**Next**: Complete frontend features (Week 2-3)
