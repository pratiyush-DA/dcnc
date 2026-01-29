"""
Authentication Routes
API endpoints for client registration, login, and token management
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.database.models import Base
from backend.database.session import get_db
from backend.services.auth_service import AuthService
from backend.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    """Request model for client registration"""
    name: str = Field(..., min_length=1, max_length=255, description="Client name")
    email: EmailStr = Field(..., description="Client email (will be admin user email)")
    password: str = Field(..., min_length=8, description="Password for admin user")
    slug: Optional[str] = Field(None, max_length=100, description="URL-friendly slug (auto-generated if not provided)")


class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/register")
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new client and create admin user.
    
    Creates:
    - New client record
    - Admin user for that client
    - Returns JWT tokens
    
    Returns:
        Client info, user info, and tokens
    """
    try:
        auth_service = AuthService(db)
        result = auth_service.register_client(
            name=request.name,
            email=request.email,
            password=request.password,
            slug=request.slug
        )
        
        return {
            "status": "success",
            "client": {
                "id": str(result["client"].id),
                "name": result["client"].name,
                "slug": result["client"].slug,
                "email": result["client"].email
            },
            "user": {
                "id": str(result["user"].id),
                "email": result["user"].email,
                "role": result["user"].role,
                "first_name": result["user"].first_name,
                "last_name": result["user"].last_name
            },
            "tokens": result["tokens"]
        }
    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user.
    
    Returns:
        User info and JWT tokens
    """
    try:
        auth_service = AuthService(db)
        result = auth_service.login(request.email, request.password)
        
        if not result:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        return {
            "status": "success",
            "user": {
                "id": str(result["user"].id),
                "email": result["user"].email,
                "role": result["user"].role,
                "client_id": str(result["user"].client_id),
                "first_name": result["user"].first_name,
                "last_name": result["user"].last_name
            },
            "tokens": result["tokens"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token.
    
    Returns:
        New access token
    """
    try:
        auth_service = AuthService(db)
        result = auth_service.refresh_token(request.refresh_token)
        
        if not result:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )
        
        return {
            "status": "success",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking refresh token.
    """
    try:
        auth_service = AuthService(db)
        success = auth_service.revoke_refresh_token(request.refresh_token)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Invalid refresh token"
            )
        
        return {
            "status": "success",
            "message": "Logged out successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    
    Requires authentication.
    """
    from backend.database.models import User
    
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "status": "success",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "client_id": str(user.client_id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status,
            "last_login": user.last_login.isoformat() if user.last_login else None
        },
        "client": {
            "id": str(user.client.id),
            "name": user.client.name,
            "slug": user.client.slug,
            "subscription_tier": user.client.subscription_tier
        }
    }
