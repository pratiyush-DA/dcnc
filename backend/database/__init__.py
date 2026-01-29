"""
Database Package
================
Centralized database operations for the data quality pipeline.

For multi-tenant system:
- PostgreSQL with Row-Level Security (RLS)
- SQLAlchemy ORM models
- Session management

Usage:
    from backend.database import get_db, init_db
    from backend.database.models import Client, User, Job
    
    # Initialize database (create tables)
    init_db()
    
    # Get session
    from backend.database.session import get_db
    db = next(get_db())
"""

# Import models (with try/except for optional PostgreSQL)
try:
    from .models import (
        Base,
        Client,
        User,
        RefreshToken,
        Job,
        Fingerprint,
        DetectionCache,
        CorrectionCache,
        AuditLog,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    Base = None
    Client = None
    User = None
    RefreshToken = None
    Job = None
    Fingerprint = None
    DetectionCache = None
    CorrectionCache = None
    AuditLog = None

# Import session management (with try/except)
try:
    from .session import (
        get_db,
        get_db_context,
        init_db,
        set_client_context,
        SessionLocal,
        engine,
    )
    SESSION_AVAILABLE = True
except ImportError:
    SESSION_AVAILABLE = False
    get_db = None
    get_db_context = None
    init_db = None
    set_client_context = None
    SessionLocal = None
    engine = None

# Legacy imports (for backward compatibility)
from .db_manager import (
    UnifiedDBManager,
    get_db_manager,
)

__all__ = [
    # Models (if available)
    "Base",
    "Client",
    "User",
    "RefreshToken",
    "Job",
    "Fingerprint",
    "DetectionCache",
    "CorrectionCache",
    "AuditLog",
    # Session (if available)
    "get_db",
    "get_db_context",
    "init_db",
    "set_client_context",
    "SessionLocal",
    "engine",
    # Legacy
    "UnifiedDBManager",
    "get_db_manager",
]
