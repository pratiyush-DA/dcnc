# Frontend & Multi-Tenant Architecture Implementation Plan

**Date**: 2026-01-27  
**Status**: 📋 **PLANNING PHASE**

---

## 🎯 Objectives

1. **Modern Frontend**: Interactive dashboard for classification and correction
2. **Multi-Tenant System**: Client-specific logins with data isolation
3. **API Integration**: Connect to existing Classification and Correction APIs
4. **Scalable Database**: Multi-tenant architecture for SaaS product
5. **Privacy & Compliance**: Client-specific caches, no data sharing

---

## 🏗️ Architecture Overview

### Frontend Stack (Recommended)

```
Frontend Framework: React 18+ with TypeScript
UI Library: Material-UI (MUI) v5 or Tailwind CSS + shadcn/ui
State Management: Redux Toolkit or Zustand
API Client: Axios with interceptors
Routing: React Router v6
Forms: React Hook Form + Zod validation
Charts: Recharts or Chart.js
File Upload: react-dropzone
Real-time: WebSockets (for job status updates)
```

### Backend Enhancements

```
Authentication: JWT tokens with refresh tokens
Multi-tenancy: Row-level security (RLS) or tenant_id in all tables
Database: PostgreSQL (scalable, supports RLS)
Cache: Redis (client-specific namespaces)
File Storage: S3-compatible storage (client-specific buckets)
```

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── assets/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── dashboard/
│   │   │   ├── DashboardHome.tsx
│   │   │   ├── StatsCards.tsx
│   │   │   ├── RecentJobs.tsx
│   │   │   └── Charts/
│   │   ├── classification/
│   │   │   ├── ClassificationUpload.tsx
│   │   │   ├── ClassificationResults.tsx
│   │   │   ├── FilePreview.tsx
│   │   │   └── ResultsTable.tsx
│   │   ├── correction/
│   │   │   ├── CorrectionUpload.tsx
│   │   │   ├── CorrectionResults.tsx
│   │   │   ├── CorrectionReport.tsx
│   │   │   └── ComparisonView.tsx
│   │   └── auth/
│   │       ├── Login.tsx
│   │       ├── Register.tsx
│   │       └── ForgotPassword.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Classification.tsx
│   │   ├── Correction.tsx
│   │   ├── Jobs.tsx
│   │   ├── Settings.tsx
│   │   └── Profile.tsx
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.ts (Axios instance)
│   │   │   ├── auth.ts
│   │   │   ├── classification.ts
│   │   │   ├── correction.ts
│   │   │   └── jobs.ts
│   │   └── websocket.ts
│   ├── store/
│   │   ├── slices/
│   │   │   ├── authSlice.ts
│   │   │   ├── classificationSlice.ts
│   │   │   ├── correctionSlice.ts
│   │   │   └── jobsSlice.ts
│   │   └── store.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useClassification.ts
│   │   ├── useCorrection.ts
│   │   └── useWebSocket.ts
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── helpers.ts
│   │   └── validators.ts
│   ├── types/
│   │   ├── api.ts
│   │   ├── classification.ts
│   │   ├── correction.ts
│   │   └── user.ts
│   ├── App.tsx
│   ├── index.tsx
│   └── routes.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts (or webpack.config.js)
└── .env.example
```

---

## 🗄️ Database Schema (Multi-Tenant)

### Core Tables

```sql
-- Clients/Tenants
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users (client-specific)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user', -- admin, user, viewer
    status VARCHAR(50) DEFAULT 'active',
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, email)
);

-- Jobs (client-specific)
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'classification', 'correction'
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    input_file_name VARCHAR(255),
    input_file_size BIGINT,
    output_files JSONB, -- {good_data: path, bad_data: path, ...}
    statistics JSONB,
    error_message TEXT,
    progress FLOAT DEFAULT 0.0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Fingerprints (client-specific, fresh per file but cached)
CREATE TABLE fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    workflow VARCHAR(50) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    method VARCHAR(50) NOT NULL,
    fingerprint_data JSONB NOT NULL,
    detection_confidence FLOAT,
    clustering_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, job_id, column_name)
);

-- Detection Cache (client-specific)
CREATE TABLE detection_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    sample_hash VARCHAR(64) NOT NULL, -- SHA256 hash of sample data
    workflow VARCHAR(50) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, column_name, sample_hash)
);

-- Correction Cache (client-specific)
CREATE TABLE correction_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value_hash VARCHAR(64) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    original_value TEXT NOT NULL,
    corrected_value TEXT NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, value_hash, subtype)
);

-- Row Level Security (RLS) Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE detection_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE correction_cache ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only see their client's data)
CREATE POLICY users_client_isolation ON users
    USING (client_id = current_setting('app.current_client_id')::UUID);

CREATE POLICY jobs_client_isolation ON jobs
    USING (client_id = current_setting('app.current_client_id')::UUID);

CREATE POLICY fingerprints_client_isolation ON fingerprints
    USING (client_id = current_setting('app.current_client_id')::UUID);

CREATE POLICY detection_cache_client_isolation ON detection_cache
    USING (client_id = current_setting('app.current_client_id')::UUID);

CREATE POLICY correction_cache_client_isolation ON correction_cache
    USING (client_id = current_setting('app.current_client_id')::UUID);
```

---

## 🔐 Authentication & Authorization

### JWT Token Structure

```typescript
interface JWTPayload {
  user_id: string;
  client_id: string;
  email: string;
  role: 'admin' | 'user' | 'viewer';
  exp: number;
  iat: number;
}
```

### API Endpoints (New)

```
POST /api/v1/auth/register - Register new client
POST /api/v1/auth/login - Login
POST /api/v1/auth/refresh - Refresh token
POST /api/v1/auth/logout - Logout
GET /api/v1/auth/me - Get current user
PUT /api/v1/auth/profile - Update profile
```

### Middleware

```python
# backend/middleware/auth.py
async def authenticate_request(request: Request, call_next):
    # Extract token from header
    # Verify JWT
    # Set current_client_id in database session
    # Continue request
```

---

## 🎨 Dashboard Features

### 1. Dashboard Home
- **Stats Cards**: Total jobs, success rate, files processed, corrections applied
- **Recent Jobs**: Last 10 jobs with status
- **Charts**: 
  - Jobs over time (line chart)
  - Success vs failure (pie chart)
  - Processing time trends (bar chart)
  - Corrections applied (area chart)

### 2. Classification Page
- **File Upload**: Drag & drop or click to upload
- **Options Panel**: 
  - Enable/disable ML clustering
  - Enable/disable ensemble detection
  - Strict mode toggle
- **Progress Indicator**: Real-time job status
- **Results View**:
  - Statistics summary
  - File preview (good_data, bad_data, reject_data)
  - Download buttons for all files
  - Fingerprint viewer (JSON tree)

### 3. Correction Page
- **File Upload**: Same as classification
- **Correction Options**:
  - Similarity threshold slider (0.0 - 1.0)
  - Max corrections per column
- **Progress Indicator**: Real-time job status
- **Results View**:
  - Statistics summary
  - Correction report (interactive)
  - Before/After comparison
  - Download buttons for all files
  - Correction details table

### 4. Jobs History
- **Table View**: All jobs with filters
- **Filters**: 
  - Job type (classification/correction)
  - Status (pending/running/completed/failed)
  - Date range
  - Client (admin only)
- **Actions**: View details, download files, retry failed jobs

### 5. Settings
- **Profile**: Update name, email, password
- **Client Settings** (admin only):
  - Client name, slug
  - Subscription tier
  - API keys
- **Preferences**: 
  - Default classification options
  - Default correction threshold
  - Notification settings

---

## 🔌 API Integration

### API Client Setup

```typescript
// src/services/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 300000, // 5 minutes for large files
});

// Request interceptor (add auth token)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle errors, refresh token)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try refresh token
      // If fails, redirect to login
    }
    return Promise.reject(error);
  }
);
```

### Classification Service

```typescript
// src/services/api/classification.ts
export const classificationService = {
  async classifyFile(file: File, options: ClassificationOptions) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('has_header', 'true');
    // ... other options
    
    const response = await apiClient.post('/api/v1/classify/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  async getJobStatus(jobId: string) {
    const response = await apiClient.get(`/api/v1/classify/status/${jobId}`);
    return response.data;
  },
};
```

---

## 🗄️ Backend Modifications

### 1. Authentication Service

```python
# backend/services/auth_service.py
class AuthService:
    def register_client(self, name, email, password):
        # Create client
        # Create admin user
        # Return tokens
    
    def login(self, email, password):
        # Verify credentials
        # Generate JWT tokens
        # Return tokens + user info
    
    def refresh_token(self, refresh_token):
        # Verify refresh token
        # Generate new access token
        # Return new tokens
```

### 2. Multi-Tenant Middleware

```python
# backend/middleware/tenant_middleware.py
async def tenant_middleware(request: Request, call_next):
    # Extract client_id from JWT token
    # Set in database session: SET app.current_client_id = client_id
    # Continue request
    response = await call_next(request)
    return response
```

### 3. Modified Pipeline Service

```python
# backend/services/pipeline_service_v2.py
class PipelineServiceV2:
    def __init__(self, client_id: str, ...):
        self.client_id = client_id
        # Use client-specific cache
        # Use client-specific DB connection
```

### 4. Cache Service (Client-Specific)

```python
# backend/services/cache_service.py
class CacheService:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.redis_client = redis.Redis()
    
    def get_cache_key(self, key: str) -> str:
        return f"client:{self.client_id}:{key}"
    
    def get(self, key: str):
        return self.redis_client.get(self.get_cache_key(key))
    
    def set(self, key: str, value: str, ttl: int = 3600):
        return self.redis_client.setex(
            self.get_cache_key(key), ttl, value
        )
```

---

## 📦 Technology Stack

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI) v5 or Tailwind CSS
- **State Management**: Redux Toolkit
- **Routing**: React Router v6
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts
- **File Upload**: react-dropzone
- **HTTP Client**: Axios
- **WebSockets**: Socket.io-client

### Backend (Enhancements)
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **File Storage**: MinIO or AWS S3
- **Authentication**: JWT (PyJWT)
- **Password Hashing**: bcrypt
- **ORM**: SQLAlchemy (optional) or raw SQL with psycopg2

---

## 🚀 Implementation Phases

### Phase 1: Backend Foundation (Week 1-2)
1. ✅ Database schema design
2. ✅ Authentication service
3. ✅ Multi-tenant middleware
4. ✅ Client-specific cache service
5. ✅ Modified pipeline service
6. ✅ API endpoints for auth

### Phase 2: Frontend Setup (Week 2-3)
1. ✅ Project initialization
2. ✅ Routing setup
3. ✅ Authentication pages (login/register)
4. ✅ Protected routes
5. ✅ API client setup
6. ✅ State management

### Phase 3: Dashboard Core (Week 3-4)
1. ✅ Dashboard layout
2. ✅ Stats cards
3. ✅ Charts
4. ✅ Recent jobs
5. ✅ Navigation

### Phase 4: Classification UI (Week 4-5)
1. ✅ File upload component
2. ✅ Options panel
3. ✅ Progress indicator
4. ✅ Results view
5. ✅ File download

### Phase 5: Correction UI (Week 5-6)
1. ✅ Correction upload
2. ✅ Correction options
3. ✅ Correction report view
4. ✅ Before/After comparison
5. ✅ Correction details

### Phase 6: Jobs & Settings (Week 6-7)
1. ✅ Jobs history page
2. ✅ Filters and search
3. ✅ Settings page
4. ✅ Profile management

### Phase 7: Polish & Testing (Week 7-8)
1. ✅ Error handling
2. ✅ Loading states
3. ✅ Responsive design
4. ✅ Testing
5. ✅ Documentation

---

## 🔒 Security & Privacy

### Data Isolation
- ✅ Row-level security (RLS) in PostgreSQL
- ✅ Client-specific cache namespaces
- ✅ Client-specific file storage buckets
- ✅ JWT tokens include client_id
- ✅ All queries filtered by client_id

### Compliance
- ✅ GDPR compliant (data deletion, export)
- ✅ SOC 2 ready (audit logs, access controls)
- ✅ HIPAA ready (encryption at rest, in transit)
- ✅ Data retention policies
- ✅ Client data export/deletion

---

## 📊 Scalability Considerations

### Database
- ✅ Partitioning by client_id (for large tables)
- ✅ Indexes on client_id, job_id, created_at
- ✅ Connection pooling (PgBouncer)
- ✅ Read replicas for analytics

### Cache
- ✅ Redis cluster for high availability
- ✅ Client-specific key prefixes
- ✅ TTL on cache entries
- ✅ Cache warming strategies

### File Storage
- ✅ Client-specific S3 buckets
- ✅ CDN for file downloads
- ✅ Lifecycle policies (auto-delete old files)

### API
- ✅ Rate limiting per client
- ✅ Background job processing
- ✅ Horizontal scaling (multiple workers)
- ✅ Load balancing

---

## 📝 Next Steps

1. **Review & Approve Plan**: Get stakeholder approval
2. **Set Up Development Environment**: 
   - PostgreSQL database
   - Redis instance
   - Frontend development server
3. **Start Phase 1**: Backend foundation
4. **Iterate**: Build, test, deploy incrementally

---

**Status**: 📋 Ready for Implementation  
**Estimated Timeline**: 8 weeks  
**Priority**: High
