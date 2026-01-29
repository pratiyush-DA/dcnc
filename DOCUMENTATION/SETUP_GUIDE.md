# Multi-Tenant System Setup Guide

**Date**: 2026-01-27  
**Status**: ✅ **READY FOR SETUP**

---

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements-api.txt

# Install PostgreSQL (if not already installed)
# Windows: Download from postgresql.org
# macOS: brew install postgresql
# Linux: sudo apt-get install postgresql
```

### 2. Set Up PostgreSQL Database

```bash
# Create database
createdb dcnc_db

# Or using psql
psql -U postgres
CREATE DATABASE dcnc_db;
\q
```

### 3. Set Environment Variables

Create `.env` file or set environment variables:

```bash
# Database
export DATABASE_URL="postgresql://user:password@localhost:5432/dcnc_db"

# JWT Secret (CHANGE IN PRODUCTION!)
export JWT_SECRET_KEY="your-super-secret-key-change-this-in-production"

# Redis (optional, for caching)
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""

# API
export API_HOST="0.0.0.0"
export API_PORT="8000"
export CORS_ORIGINS="*"
```

### 4. Initialize Database

**Option A: Using Python (Recommended)**
```bash
python setup_database.py
```

**Option B: Using SQL Script**
```bash
psql -U user -d dcnc_db -f DOCUMENTATION/MULTI_TENANT_DATABASE_SCHEMA.sql
```

### 5. Start Redis (Optional, for caching)

```bash
# Windows: Download Redis from redis.io
# macOS: brew install redis && brew services start redis
# Linux: sudo apt-get install redis-server && sudo systemctl start redis
```

### 6. Run API Server

```bash
# Development
python run_api.py

# Or with uvicorn
uvicorn DCNC.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Test Authentication

### 1. Register a Client

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "email": "admin@test.com",
    "password": "Test123!@#"
  }'
```

Response:
```json
{
  "status": "success",
  "client": {
    "id": "uuid",
    "name": "Test Client",
    "slug": "test-client"
  },
  "user": {
    "id": "uuid",
    "email": "admin@test.com",
    "role": "admin"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "Test123!@#"
  }'
```

### 3. Use Protected Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/classify/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@data.csv" \
  -F "has_header=true"
```

### 4. Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

---

## 🔍 Verify Setup

### Check Database Tables

```bash
psql -U user -d dcnc_db -c "\dt"
```

Should show:
- clients
- users
- refresh_tokens
- jobs
- fingerprints
- detection_cache
- correction_cache
- audit_logs

### Check API Health

```bash
curl http://localhost:8000/api/v1/health
```

---

## 🐛 Troubleshooting

### Database Connection Error
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL is correct
- Check database exists: `psql -l`

### JWT Token Errors
- Verify JWT_SECRET_KEY is set
- Check token expiration (15 min for access, 7 days for refresh)
- Ensure token is in Authorization header: `Bearer <token>`

### Redis Connection Error
- Redis is optional (cache will be disabled if not available)
- Check Redis is running: `redis-cli ping`
- Verify REDIS_HOST and REDIS_PORT

---

## 📝 Next Steps

1. ✅ Database setup complete
2. ✅ Authentication working
3. ⏭️ Start frontend development (Week 2-3)
4. ⏭️ Test multi-tenancy (create multiple clients)

---

**Status**: ✅ Ready for Testing
