"""
Database Models for Multi-Tenant System
PostgreSQL models using SQLAlchemy ORM
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class Client(Base):
    """Client/Tenant model"""
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default='active')  # active, suspended, cancelled
    subscription_tier = Column(String(50), default='basic')  # basic, pro, enterprise
    max_jobs_per_month = Column(Integer, default=1000)
    max_file_size_mb = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="client", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="client", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_clients_slug', 'slug'),
        Index('idx_clients_status', 'status'),
    )


class User(Base):
    """User model (client-specific)"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), default='user')  # admin, user, viewer
    status = Column(String(50), default='active')  # active, inactive, suspended
    last_login = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="users")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('client_id', 'email', name='uq_users_client_email'),
        Index('idx_users_client_id', 'client_id'),
        Index('idx_users_email', 'email'),
        Index('idx_users_status', 'status'),
    )


class RefreshToken(Base):
    """Refresh token model"""
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    __table_args__ = (
        Index('idx_refresh_tokens_user_id', 'user_id'),
        Index('idx_refresh_tokens_expires_at', 'expires_at'),
    )


class Job(Base):
    """Job model (client-specific)"""
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    job_type = Column(String(50), nullable=False)  # 'classification', 'correction'
    status = Column(String(50), default='pending')  # pending, running, completed, failed, cancelled
    input_file_name = Column(String(255))
    input_file_size = Column(Integer)  # in bytes
    input_file_path = Column(Text)
    output_files = Column(JSON)  # {good_data: path, bad_data: path, ...}
    statistics = Column(JSON)
    error_message = Column(Text)
    progress = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
    fingerprints = relationship("Fingerprint", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_jobs_client_id', 'client_id'),
        Index('idx_jobs_user_id', 'user_id'),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_job_type', 'job_type'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_client_created', 'client_id', 'created_at'),
    )


class Fingerprint(Base):
    """Fingerprint model (client-specific, fresh per file but cached)"""
    __tablename__ = "fingerprints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    column_name = Column(String(255), nullable=False)
    workflow = Column(String(50), nullable=False)
    subtype = Column(String(50), nullable=False)
    method = Column(String(50), nullable=False)
    fingerprint_data = Column(JSON, nullable=False)
    detection_confidence = Column(Float)
    clustering_confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="fingerprints")
    
    __table_args__ = (
        UniqueConstraint('client_id', 'job_id', 'column_name', name='uq_fingerprints_client_job_column'),
        Index('idx_fingerprints_client_id', 'client_id'),
        Index('idx_fingerprints_job_id', 'job_id'),
        Index('idx_fingerprints_client_job', 'client_id', 'job_id'),
    )


class DetectionCache(Base):
    """Detection cache model (client-specific)"""
    __tablename__ = "detection_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    column_name = Column(String(255), nullable=False)
    sample_hash = Column(String(64), nullable=False)  # SHA256 hash
    workflow = Column(String(50), nullable=False)
    subtype = Column(String(50), nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('client_id', 'column_name', 'sample_hash', name='uq_detection_cache_client_column_hash'),
        Index('idx_detection_cache_client_id', 'client_id'),
        Index('idx_detection_cache_column_name', 'column_name'),
        Index('idx_detection_cache_expires_at', 'expires_at'),
        Index('idx_detection_cache_last_used', 'last_used'),
    )


class CorrectionCache(Base):
    """Correction cache model (client-specific)"""
    __tablename__ = "correction_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    value_hash = Column(String(64), nullable=False)
    subtype = Column(String(50), nullable=False)
    original_value = Column(Text, nullable=False)
    corrected_value = Column(Text, nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('client_id', 'value_hash', 'subtype', name='uq_correction_cache_client_hash_subtype'),
        Index('idx_correction_cache_client_id', 'client_id'),
        Index('idx_correction_cache_subtype', 'subtype'),
        Index('idx_correction_cache_expires_at', 'expires_at'),
        Index('idx_correction_cache_last_used', 'last_used'),
    )


class AuditLog(Base):
    """Audit log model (for compliance)"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False)  # login, logout, file_upload, job_create, etc.
    resource_type = Column(String(50))  # job, user, client, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSON)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_logs_client_id', 'client_id'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )
