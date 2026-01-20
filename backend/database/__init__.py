"""
Database Package
================
Centralized database operations for the data quality pipeline.

Usage:
    from backend.database import get_db_manager
    
    db = get_db_manager()
    db.save_fingerprint(...)
    db.export_fingerprints_json("output/fingerprints.json")
"""

from .db_manager import (
    UnifiedDBManager,
    get_db_manager,
    CachedPattern,
    ColumnFingerprint,
)

__all__ = [
    "UnifiedDBManager",
    "get_db_manager",
    "CachedPattern",
    "ColumnFingerprint",
]
