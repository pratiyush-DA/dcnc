# Quick Start Guide - API & Frontend with Docker

**Date**: 2026-01-28  
**Estimated Time**: 10-15 minutes

---

## 🚀 Quick Start (Step-by-Step)

### **Step 1: Start PostgreSQL with Docker** (2 minutes)

```powershell
# Navigate to project directory
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"

# Start PostgreSQL container
docker-compose up -d

# Verify it's running
docker ps
```

✅ **Expected Output**: You should see `dcnc_postgres` container running

---

### **Step 2: Update Environment Variables** (1 minute)

Your `.env` file already exists! Just verify it has these values:

```env
# Database (must match docker-compose.yml)
DATABASE_URL=postgresql://postgres:password@localhost:5432/dcnc_db

# JWT Secret (you have "key" - consider changing for production)
JWT_SECRET_KEY=key

# API Settings (add these if missing)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Your existing LLM config (keep as is)
GROQ_API_KEY=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
ENABLE_LLM_VERIFICATION=true
```

**Note**: Your `.env` already has `DATABASE_URL` and `JWT_SECRET_KEY` ✅

---

### **Step 3: Activate Python Environment** (30 seconds)

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Verify activation (should show (venv) in prompt)
```

---

### **Step 4: Install/Verify Backend Dependencies** (2-3 minutes)

```powershell
# Install API dependencies
pip install -r requirements-api.txt

# Verify key packages
python -c "import fastapi, uvicorn, sqlalchemy; print('✅ Dependencies OK')"
```

---

### **Step 5: Initialize Database** (1 minute)

```powershell
# Create database tables
python setup_database.py
```

✅ **Expected Output**: "✅ Database tables created successfully!"

---

### **Step 6: Start Backend API** (Terminal 1) 🚀

```powershell
# Make sure you're in project root and venv is activated
python run_api.py
```

✅ **Expected Output**: 
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**API is now running at**: http://localhost:8000

**Test it**: Open http://localhost:8000/docs in browser

---

### **Step 7: Start Frontend** (Terminal 2) 🎨

**Open a NEW terminal window**:

```powershell
# Navigate to frontend
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc\frontend"

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

✅ **Expected Output**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Frontend is now running at**: http://localhost:5173

---

### **Step 8: Test Everything** ✅

1. **Test API Health**:
   - Open: http://localhost:8000/api/v1/health
   - Should see: `{"status": "healthy", "version": "1.0.0"}`

2. **Test API Docs**:
   - Open: http://localhost:8000/docs
   - Should see Swagger UI

3. **Test Frontend**:
   - Open: http://localhost:5173
   - Should see login/registration page

4. **Register a Test Account**:
   - Use the frontend UI to register
   - Or use API:
     ```powershell
     curl -X POST http://localhost:8000/api/v1/auth/register `
       -H "Content-Type: application/json" `
       -d '{\"name\": \"Test Client\", \"email\": \"admin@test.com\", \"password\": \"Test123!@#\"}'
     ```

---

## 📋 Complete Checklist

### ✅ **Backend**:
- [ ] Docker Desktop running
- [ ] PostgreSQL container started (`docker-compose up -d`)
- [ ] `.env` file has `DATABASE_URL` and `JWT_SECRET_KEY`
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements-api.txt`)
- [ ] Database initialized (`python setup_database.py`)
- [ ] API running (`python run_api.py`)
- [ ] API accessible at http://localhost:8000/docs

### ✅ **Frontend**:
- [ ] Node.js installed (check: `node --version`)
- [ ] Dependencies installed (`npm install` in frontend/)
- [ ] Frontend running (`npm run dev`)
- [ ] Frontend accessible at http://localhost:5173

---

## 🔧 Troubleshooting

### **Problem: Docker container won't start**

```powershell
# Check Docker is running
docker ps

# Check container logs
docker logs dcnc_postgres

# Restart container
docker-compose restart
```

---

### **Problem: Database connection error**

**Error**: `could not connect to server` or `connection refused`

**Solution**:
1. Verify PostgreSQL is running: `docker ps`
2. Check DATABASE_URL in `.env` matches docker-compose.yml:
   - User: `postgres`
   - Password: `password`
   - Database: `dcnc_db`
   - Port: `5432`

---

### **Problem: Port 8000 already in use**

**Solution**:
```powershell
# Option 1: Change port in .env
API_PORT=8001

# Option 2: Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

### **Problem: Frontend can't connect to API**

**Error**: CORS error or network error

**Solution**:
1. Check `CORS_ORIGINS` in backend `.env`:
   ```env
   CORS_ORIGINS=http://localhost:5173
   ```

2. Restart API after changing `.env`

3. Check frontend proxy in `vite.config.ts` (already configured ✅)

---

### **Problem: Module not found**

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```powershell
# Make sure venv is activated (should see (venv) in prompt)
.\venv\Scripts\Activate.ps1

# Reinstall
pip install -r requirements-api.txt
```

---

### **Problem: npm install fails**

**Solution**:
```powershell
# Clear cache
npm cache clean --force

# Delete and reinstall
cd frontend
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json -ErrorAction SilentlyContinue
npm install
```

---

## 🎯 Quick Command Reference

### **Start Everything**:

**Terminal 1 (Backend)**:
```powershell
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"
docker-compose up -d
.\venv\Scripts\Activate.ps1
python run_api.py
```

**Terminal 2 (Frontend)**:
```powershell
cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc\frontend"
npm run dev
```

### **Stop Everything**:

```powershell
# Stop PostgreSQL
docker-compose down

# Stop API: Ctrl+C in Terminal 1
# Stop Frontend: Ctrl+C in Terminal 2
```

---

## 📍 Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/api/v1/health
- **Frontend**: http://localhost:5173
- **PostgreSQL**: `localhost:5432` (user: `postgres`, password: `password`)

---

## ✅ Success Indicators

You'll know everything is working when:

1. ✅ **PostgreSQL**: `docker ps` shows `dcnc_postgres` running
2. ✅ **API**: http://localhost:8000/docs shows Swagger UI
3. ✅ **Frontend**: http://localhost:5173 shows login page
4. ✅ **Registration**: You can create an account via frontend
5. ✅ **Login**: You can login with your credentials

---

## 🎉 Next Steps

Once everything is running:

1. **Register a client** via frontend or API
2. **Upload a test CSV** file for classification
3. **Test the correction** endpoint
4. **Explore the dashboard** features

---

**Need Help?** Check `DOCKER_SETUP_GUIDE.md` for detailed troubleshooting.

**Last Updated**: 2026-01-28
