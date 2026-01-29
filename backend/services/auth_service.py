"""
Authentication Service
Handles client registration, user login, and JWT token management
"""

import os
import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database.models import Client, User, RefreshToken

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
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
        """
        Register new client and create admin user.
        
        Args:
            name: Client name
            email: Client email (will be admin user email)
            password: Password for admin user
            slug: Optional URL-friendly slug (auto-generated if not provided)
            
        Returns:
            Dictionary with client, user, and tokens
        """
        # Validate password
        if not self._validate_password(password):
            raise ValueError("Password does not meet requirements")
        
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Generate slug if not provided
        if not slug:
            slug = self._generate_slug(name)
        
        # Check if slug already exists
        existing_client = self.db.query(Client).filter(Client.slug == slug).first()
        if existing_client:
            raise ValueError(f"Slug '{slug}' already taken")
        
        # Create client
        client = Client(
            name=name,
            slug=slug,
            email=email,
            status='active',
            subscription_tier='basic'
        )
        self.db.add(client)
        self.db.flush()  # Get client.id
        
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
        self.db.flush()  # Get user.id
        
        # Generate tokens
        tokens = self._generate_tokens(admin_user)
        
        self.db.commit()
        
        logger.info(f"Client registered: {client.name} (ID: {client.id})")
        
        return {
            "client": client,
            "user": admin_user,
            "tokens": tokens
        }
    
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Login user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary with user and tokens, or None if invalid
        """
        # Find user
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return None
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for email: {email}")
            return None
        
        # Check user status
        if user.status != 'active':
            logger.warning(f"Login attempt for inactive user: {email}")
            return None
        
        # Check client status
        if user.client.status != 'active':
            logger.warning(f"Login attempt for inactive client: {user.client.name}")
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Generate tokens
        tokens = self._generate_tokens(user)
        
        logger.info(f"User logged in: {email} (Client: {user.client.name})")
        
        return {
            "user": user,
            "tokens": tokens
        }
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh access token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Dictionary with new access_token, or None if invalid
        """
        # Verify refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
        
        # Check token type
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None
        
        # Check if token exists in DB
        token_hash = self._hash_token(refresh_token)
        db_token = self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None)
            )
        ).first()
        
        if not db_token:
            logger.warning("Refresh token not found in database")
            return None
        
        if db_token.expires_at < datetime.utcnow():
            logger.warning("Refresh token expired in database")
            return None
        
        # Get user
        user = self.db.query(User).filter(User.id == db_token.user_id).first()
        if not user or user.status != 'active':
            logger.warning("User not found or inactive")
            return None
        
        # Check client status
        if user.client.status != 'active':
            logger.warning("Client is inactive")
            return None
        
        # Generate new access token
        access_token = self._create_access_token(user)
        
        logger.debug(f"Access token refreshed for user: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
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
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug"""
        # Convert to lowercase
        slug = name.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Limit length
        if len(slug) > 100:
            slug = slug[:100]
        return slug
    
    def _validate_password(self, password: str) -> bool:
        """
        Validate password requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        token_hash = self._hash_token(refresh_token)
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash
        ).first()
        
        if db_token and db_token.revoked_at is None:
            db_token.revoked_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
