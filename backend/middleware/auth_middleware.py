"""
Authentication Middleware
Handles JWT token validation and sets tenant context
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    
    Sets request.state with:
    - user_id
    - client_id
    - user_role
    
    Args:
        request: FastAPI request
        credentials: HTTP Bearer credentials
        
    Returns:
        JWT payload with user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Get token from Authorization header
    if credentials is None:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ")[1]
    else:
        token = credentials.credentials
    
    # Verify token
    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set request state
    request.state.user_id = payload.get("user_id")
    request.state.client_id = payload.get("client_id")
    request.state.user_role = payload.get("role")
    request.state.user_email = payload.get("email")
    
    return payload


async def tenant_middleware(request: Request, call_next):
    """
    Set client_id in database session for Row-Level Security (RLS).
    
    This middleware sets the client_id context that will be used
    by database queries to enforce data isolation.
    """
    # If user is authenticated, set client_id context
    if hasattr(request.state, 'client_id'):
        client_id = request.state.client_id
        # Store in request state for database session
        # The database session will use this for RLS
        request.state.db_client_id = client_id
        logger.debug(f"Tenant context set: client_id={client_id}")
    
    response = await call_next(request)
    return response


def require_role(allowed_roles: list[str]):
    """
    Dependency to require specific user roles.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: dict = Depends(require_role(["admin"]))
        ):
            ...
    """
    async def role_checker(
        current_user: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        
        return current_user
    
    return role_checker
