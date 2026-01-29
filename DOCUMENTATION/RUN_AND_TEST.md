# Run and Test Frontend + Backend Together

## Automated Test (when both are running)

From project root in PowerShell:

```powershell
.\run_and_test.ps1 -TestOnly
```

This checks:
- Backend health: http://localhost:8000/api/v1/health
- Backend root: http://localhost:8000/
- Frontend: http://localhost:5173

---

## Quick Start

### 1. Activate virtual environment

```powershell
cd "C:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc"
.\venv\Scripts\Activate.ps1
```

### 2. Set environment variables

```powershell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/dcnc_db"
$env:JWT_SECRET_KEY="key"
```

### 3. Start PostgreSQL (if using Docker)

```powershell
docker-compose up -d
```

### 4. Start backend (Terminal 1)

```powershell
python run_api.py
```

Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

### 5. Start frontend (Terminal 2)

Open a **new** PowerShell window:

```powershell
cd "C:\Users\pkumar2\OneDrive - Data Axle\Documents\HIGHER_GEAR\DATA_CLUSTERING_V3\dcnc\frontend"
npm run dev
```

Wait until you see: `Local: http://localhost:5173/`

### 6. Test

- **Backend health**: Open http://localhost:8000/api/v1/health  
- **API docs**: Open http://localhost:8000/api/docs  
- **Frontend**: Open http://localhost:5173  

---

## Test Checklist

| Test | URL | Expected |
|------|-----|----------|
| Backend root | http://localhost:8000/ | JSON with service, version, status |
| Backend health | http://localhost:8000/api/v1/health | JSON with status "healthy" |
| API docs | http://localhost:8000/api/docs | Swagger UI |
| Frontend | http://localhost:5173 | Login page |
| Register | http://localhost:5173/register | Registration form |
| Login | http://localhost:5173/login | Login form |

---

## If Backend Fails to Start

### "No module named 'uvicorn'" or "No module named 'sqlalchemy'"

Install dependencies (with venv activated):

```powershell
pip install -r requirements-api.txt
```

Or install core packages:

```powershell
pip install uvicorn fastapi sqlalchemy psycopg2-binary pyjwt bcrypt "python-jose[cryptography]" pandas numpy redis
```

### "ImportError: PyO3 modules compiled for CPython 3.8 or older"

Upgrade cryptography:

```powershell
pip install --upgrade cryptography
```

### Frontend: "vite is not recognized"

Install dependencies (from project root):

```powershell
cd frontend
npm install
npm run dev
```

### "Connection refused" to PostgreSQL

- Start PostgreSQL: `docker-compose up -d`
- Or install and start PostgreSQL locally
- Check `DATABASE_URL` in `.env` or environment

---

## Frontend proxy

The frontend is configured to proxy `/api` to `http://localhost:8000`, so:

- Frontend: http://localhost:5173  
- API calls from the app go to http://localhost:5173/api/... and are proxied to http://localhost:8000/api/...

No CORS issues when using the dev server.
