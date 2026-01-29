# Docker Setup Guide - API & Frontend

**Date**: 2026-01-28  
**Purpose**: Step-by-step guide to get API and Frontend running with Docker

---

## Prerequisites

✅ **Docker Desktop** installed and running  
✅ **Python 3.10+** installed  
✅ **Node.js 18+** installed  
✅ **Git** (optional, for cloning)

---

## Step-by-Step Setup

### **Step 1: Start PostgreSQL with Docker** 🐘

1. **Navigate to project directory**:
   ```powershell
   cd "c:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"
   ```

2. **Start PostgreSQL container**:
   ```powershell
   docker-compose up -d
   ```

3. **Verify PostgreSQL is running**:
   ```powershell
   docker ps
   ```
   You should see `dcnc_postgres` container running.

4. **Test connection** (optional):
   ```powershell
   docker exec -it dcnc_postgres psql -U postgres -d dcnc_db -c "SELECT version();"
   ```

**PostgreSQL Details**:
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `dcnc_db`
- **User**: `postgres`
- **Password**: `password`

---

### **Step 2: Create Environment File** 📝

1. **Create `.env` file** in project root:
   ```powershell
   # Create .env file
   New-Item -Path ".env" -ItemType File -Force
   ```

2. **Add environment variables** to `.env`:
   ```env
   # Database (matches docker-compose.yml)
   DATABASE_URL=postgresql://postgres:password@localhost:5432/dcnc_db
   
   # JWT Secret (CHANGE THIS IN PRODUCTION!)
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-12345
   
   # API Settings
   API_HOST=0.0.0.0
   API_PORT=8000
   API_WORKERS=1
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   
   # Optional: Redis (for caching - skip if not using)
   # REDIS_HOST=localhost
   # REDIS_PORT=6379
   # REDIS_PASSWORD=
   
   # Optional: LLM (if using Groq API)
   # GROQ_API_KEY=your-groq-api-key-here
   ```

3. **Save the file**

---

### **Step 3: Set Up Python Virtual Environment** 🐍

1. **Create virtual environment** (if not exists):
   ```powershell
   python -m venv venv
   ```

2. **Activate virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Upgrade pip**:
   ```powershell
   python -m pip install --upgrade pip
   ```

---

### **Step 4: Install Backend Dependencies** 📦

1. **Install API requirements**:
   ```powershell
   pip install -r requirements-api.txt
   ```

2. **Install additional requirements** (if needed):
   ```powershell
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```powershell
   python -c "import fastapi; print('FastAPI installed')"
   python -c "import uvicorn; print('Uvicorn installed')"
   ```

---

### **Step 5: Initialize Database** 🗄️

1. **Run database setup script**:
   ```powershell
   python setup_database.py
   ```

2. **Verify tables created**:
   ```powershell
   docker exec -it dcnc_postgres psql -U postgres -d dcnc_db -c "\dt"
   ```

   You should see tables like:
   - `clients`
   - `users`
   - `jobs`
   - `fingerprints`
   - etc.

---

### **Step 6: Start Backend API** 🚀

1. **Start API server**:
   ```powershell
   python run_api.py
   ```

   Or with uvicorn directly:
   ```powershell
   uvicorn DCNC.api.app:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Verify API is running**:
   - Open browser: http://localhost:8000/docs
   - You should see Swagger/OpenAPI documentation

3. **Test health endpoint**:
   ```powershell
   curl http://localhost:8000/api/v1/health
   ```

   Or in browser: http://localhost:8000/api/v1/health

**API will be available at**: http://localhost:8000

---

### **Step 7: Set Up Frontend** 🎨

1. **Navigate to frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```powershell
   npm install
   ```

   **Note**: This may take a few minutes on first run.

3. **Create frontend `.env` file** (optional):
   ```powershell
   # In frontend directory
   New-Item -Path ".env" -ItemType File -Force
   ```

   Add to `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. **Verify installation**:
   ```powershell
   npm list --depth=0
   ```

---

### **Step 8: Start Frontend** 🎨

1. **Start development server**:
   ```powershell
   npm run dev
   ```

2. **Frontend will be available at**: http://localhost:5173

   (Vite default port is 5173)

3. **Open in browser**: http://localhost:5173

---

### **Step 9: Test the Setup** ✅

#### **A. Test API Health**:
```powershell
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{"status": "healthy", "version": "1.0.0"}
```

#### **B. Test API Registration**:
```powershell
curl -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"name\": \"Test Client\", \"email\": \"admin@test.com\", \"password\": \"Test123!@#\"}'
```

#### **C. Test Frontend**:
1. Open http://localhost:5173 in browser
2. You should see the login/registration page
3. Register a new account
4. Login with credentials

---

## Complete Setup Checklist

### ✅ **Backend Setup**:
- [ ] Docker Desktop running
- [ ] PostgreSQL container started (`docker-compose up -d`)
- [ ] `.env` file created with correct variables
- [ ] Python virtual environment activated
- [ ] Backend dependencies installed (`pip install -r requirements-api.txt`)
- [ ] Database initialized (`python setup_database.py`)
- [ ] API server running (`python run_api.py`)
- [ ] API accessible at http://localhost:8000/docs

### ✅ **Frontend Setup**:
- [ ] Node.js 18+ installed
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Frontend `.env` file created (optional)
- [ ] Frontend dev server running (`npm run dev`)
- [ ] Frontend accessible at http://localhost:5173

---

## Troubleshooting

### **Issue 1: PostgreSQL Connection Failed**

**Error**: `could not connect to server`

**Solution**:
1. Check Docker is running: `docker ps`
2. Check PostgreSQL container: `docker ps | findstr postgres`
3. Check logs: `docker logs dcnc_postgres`
4. Verify DATABASE_URL in `.env` matches docker-compose.yml

---

### **Issue 2: Port Already in Use**

**Error**: `Address already in use` or `port 8000 is already in use`

**Solution**:
1. **Change API port** in `.env`:
   ```env
   API_PORT=8001
   ```

2. **Or stop the process using port 8000**:
   ```powershell
   # Find process using port 8000
   netstat -ano | findstr :8000
   # Kill the process (replace PID with actual process ID)
   taskkill /PID <PID> /F
   ```

---

### **Issue 3: Frontend Can't Connect to API**

**Error**: `Network Error` or `CORS error`

**Solution**:
1. **Check CORS_ORIGINS** in backend `.env`:
   ```env
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

2. **Check VITE_API_BASE_URL** in `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Restart both API and Frontend** after changing `.env` files

---

### **Issue 4: Database Tables Not Created**

**Error**: `relation "clients" does not exist`

**Solution**:
1. **Re-run database setup**:
   ```powershell
   python setup_database.py
   ```

2. **Check database connection**:
   ```powershell
   docker exec -it dcnc_postgres psql -U postgres -d dcnc_db -c "\dt"
   ```

---

### **Issue 5: Module Not Found Errors**

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
1. **Verify virtual environment is activated**:
   ```powershell
   # Should show (venv) in prompt
   ```

2. **Reinstall dependencies**:
   ```powershell
   pip install -r requirements-api.txt
   ```

3. **Check Python version**:
   ```powershell
   python --version  # Should be 3.10+
   ```

---

### **Issue 6: Frontend Dependencies Fail**

**Error**: `npm ERR!` or installation fails

**Solution**:
1. **Clear npm cache**:
   ```powershell
   npm cache clean --force
   ```

2. **Delete node_modules and reinstall**:
   ```powershell
   Remove-Item -Recurse -Force node_modules
   Remove-Item package-lock.json
   npm install
   ```

3. **Check Node.js version**:
   ```powershell
   node --version  # Should be 18+
   ```

---

## Quick Start Commands (Summary)

```powershell
# 1. Start PostgreSQL
docker-compose up -d

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install backend dependencies
pip install -r requirements-api.txt

# 4. Initialize database
python setup_database.py

# 5. Start API (in one terminal)
python run_api.py

# 6. Start Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

---

## Environment Variables Reference

### **Backend `.env`** (Required):

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/dcnc_db

# JWT Secret
JWT_SECRET_KEY=your-secret-key-change-in-production

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### **Frontend `.env`** (Optional):

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Access Points

- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/api/v1/health
- **Frontend**: http://localhost:5173
- **PostgreSQL**: `localhost:5432`

---

## Next Steps

1. ✅ **Register a client** via API or Frontend
2. ✅ **Upload a test CSV file** for classification
3. ✅ **Test correction endpoint** with classified data
4. ✅ **Explore the dashboard** in the frontend

---

## Production Deployment

For production, you'll need to:
1. Change `JWT_SECRET_KEY` to a secure random string
2. Use environment-specific database credentials
3. Set up proper CORS origins
4. Use production build for frontend: `npm run build`
5. Use production server (nginx, etc.) for frontend
6. Set up SSL/HTTPS
7. Configure proper logging and monitoring

---

**Last Updated**: 2026-01-28  
**Status**: ✅ Ready to use
