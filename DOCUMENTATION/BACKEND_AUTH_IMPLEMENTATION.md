# Backend Authentication & Multi-Tenant Implementation

**Date**: 2026-01-27  
**Status**: 📋 **PLANNING PHASE**

---

## 🔐 Authentication Flow

### Registration Flow
1. Client registers with name, email, password
2. System creates client record
3. System creates admin user for that client
4. Returns JWT tokens

### Login Flow
1. User provides email and password
2. System verifies credentials
3. System generates JWT access token (15 min) and refresh token (7 days)
4. Returns tokens + user info

### Token Refresh Flow
1. Client sends refresh token
2. System validates refresh token
3. System generates new access token
4. Returns new access token

---

## 📁 New Backend Files

### 1. Authentication Service

```python
# backend/services/auth_service.py
from datetime import datetime, timedelta
import jwt
import bcrypt
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=15)
        self.refresh_token_expire = timedelta(days=7)
    
    def register_client(
        self,
        name: str,
        email: str,
        password: str,
        slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register new client and create admin user"""
        # Create client
        client = Client(
            name=name,
            slug=slug or self._generate_slug(name),
            email=email,
            status='active'
        )
        self.db.add(client)
        self.db.flush()
        
        # Create admin user
        password_hash = self._hash_password(password)
        admin_user = User(
            client_id=client.id,
            email=email,
            password_hash=password_hash,
            role='admin',
            status='active',
            email_verified=False
        )
        self.db.add(admin_user)
        self.db.commit()
        
        # Generate tokens
        tokens = self._generate_tokens(admin_user)
        
        return {
            "client": client,
            "user": admin_user,
            "tokens": tokens
        }
    
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Login user"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self._verify_password(password, user.password_hash):
            return None
        
        if user.status != 'active':
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Generate tokens
        tokens = self._generate_tokens(user)
        
        return {
            "user": user,
            "tokens": tokens
        }
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh access token"""
        # Verify refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            return None
        
        # Check if token exists in DB
        token_hash = self._hash_token(refresh_token)
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None)
        ).first()
        
        if not db_token or db_token.expires_at < datetime.utcnow():
            return None
        
        # Get user
        user = self.db.query(User).filter(User.id == db_token.user_id).first()
        if not user or user.status != 'active':
            return None
        
        # Generate new access token
        access_token = self._create_access_token(user)
        
        return {
            "access_token": access_token
        }
    
    def _generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens"""
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)
        
        # Save refresh token to DB
        token_hash = self._hash_token(refresh_token)
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + self.refresh_token_expire
        )
        self.db.add(db_token)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def _create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        payload = {
            "user_id": str(user.id),
            "client_id": str(user.client_id),
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + self.access_token_expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        payload = {
            "user_id": str(user.id),
            "client_id": str(user.client_id),
            "type": "refresh",
            "exp": datetime.utcnow() + self.refresh_token_expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug"""
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
        return slug.strip('-')
```

### 2. Authentication Middleware

```python
# backend/middleware/auth_middleware.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional

security = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = security
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Set client_id in request state
    request.state.user_id = payload["user_id"]
    request.state.client_id = payload["client_id"]
    request.state.user_role = payload["role"]
    
    return payload

async def tenant_middleware(request: Request, call_next):
    """Set client_id in database session for RLS"""
    if hasattr(request.state, 'client_id'):
        # Set client_id for RLS
        # This will be used by database queries
        # Example: SET app.current_client_id = request.state.client_id
        pass
    
    response = await call_next(request)
    return response
```

### 3. Auth Routes

```python
# DCNC/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from ..services.auth_service import AuthService
from ..middleware.auth_middleware import get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    slug: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(request: RegisterRequest):
    """Register new client"""
    auth_service = AuthService(db_session)
    result = auth_service.register_client(
        name=request.name,
        email=request.email,
        password=request.password,
        slug=request.slug
    )
    return {
        "client": {
            "id": str(result["client"].id),
            "name": result["client"].name,
            "slug": result["client"].slug
        },
        "user": {
            "id": str(result["user"].id),
            "email": result["user"].email,
            "role": result["user"].role
        },
        "tokens": result["tokens"]
    }

@router.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    auth_service = AuthService(db_session)
    result = auth_service.login(request.email, request.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "user": {
            "id": str(result["user"].id),
            "email": result["user"].email,
            "role": result["user"].role,
            "client_id": str(result["user"].client_id)
        },
        "tokens": result["tokens"]
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    auth_service = AuthService(db_session)
    result = auth_service.refresh_token(refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return result

@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current user info"""
    return current_user
```

### 4. Modified Pipeline Service

```python
# backend/services/pipeline_service_v2.py
class PipelineServiceV2:
    def __init__(
        self,
        client_id: str,  # NEW: Client ID for multi-tenancy
        output_dir: str,
        enable_cache: bool = True,
        fresh_fingerprints_only: bool = False,
        **kwargs
    ):
        self.client_id = client_id
        self.output_dir = output_dir
        
        # Client-specific cache
        self.cache_service = CacheService(client_id=client_id)
        
        # Client-specific DB connection with RLS
        self._db = self._init_db_with_client(client_id)
        
        # ... rest of initialization
    
    def _init_db_with_client(self, client_id: str):
        """Initialize DB with client context for RLS"""
        db = get_db_manager()
        # Set client_id in session for RLS
        db.set_client_id(client_id)
        return db
```

---

## 🔒 Security Best Practices

1. **Password Requirements**: Min 8 chars, uppercase, lowercase, number, special char
2. **Token Storage**: HttpOnly cookies (recommended) or secure localStorage
3. **HTTPS Only**: All API calls over HTTPS in production
4. **Rate Limiting**: Limit login attempts (5 per 15 min)
5. **CORS**: Configure allowed origins properly
6. **Input Validation**: Validate all inputs
7. **SQL Injection**: Use parameterized queries
8. **XSS Protection**: Sanitize user inputs

---

## 📝 Next Steps

1. Implement authentication service
2. Add auth routes to API
3. Update existing routes to require authentication
4. Add tenant middleware
5. Update pipeline service for multi-tenancy
6. Test authentication flow
7. Update frontend to use auth

---

**Status**: 📋 Ready for Implementation
