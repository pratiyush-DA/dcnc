"""
Detection Cache
===============
Wrapper around unified db_manager for detection caching.
DEPRECATED: Use backend.database.db_manager directly.
"""

import hashlib
import logging
from typing import Optional, List, Any

from ..interfaces import DetectionResult, DetectionSource

# Use unified database manager
try:
    from backend.database import get_db_manager
except ImportError:
    # Fallback for circular imports
    get_db_manager = None

logger = logging.getLogger(__name__)


class DetectionCache:
    """
    Detection cache using unified db_manager.
    
    This class is a FACADE over db_manager for backward compatibility.
    New code should use db_manager directly.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize cache.
        
        Args:
            db_path: Ignored - uses unified_cache.db
        """
        self._db = None
        if get_db_manager is not None:
            try:
                self._db = get_db_manager()
                logger.debug("DetectionCache using unified db_manager")
            except Exception as e:
                logger.warning(f"Could not initialize unified db_manager: {e}")
    
    def _compute_hash(self, column_name: str, sample_values: Optional[List[Any]] = None) -> str:
        """Compute hash for column identification."""
        hash_data = column_name.lower()
        if sample_values:
            hash_data += ":" + ",".join(str(v)[:20] for v in sample_values[:5])
        return hashlib.sha256(hash_data.encode()).hexdigest()[:32]
    
    def get(self, column_name: str) -> Optional[DetectionResult]:
        """
        Get cached detection result.
        
        Args:
            column_name: Column name to look up
            
        Returns:
            Cached DetectionResult or None
        """
        if self._db is None:
            return None
        
        column_hash = self._compute_hash(column_name)
        cached = self._db.get_detection(column_hash)
        
        if cached:
            return DetectionResult(
                workflow=cached["workflow"],
                subtype=cached["subtype"],
                confidence=cached.get("confidence", 0.9),
                source=DetectionSource.CACHE,
                matched_rule=None,
            )
        
        return None
    
    def save(
        self,
        column_name: str,
        result: DetectionResult,
        sample_values: Optional[List[Any]] = None
    ):
        """
        Save detection result to cache.
        
        Args:
            column_name: Column name
            result: Detection result to cache
            sample_values: Optional sample values
        """
        if self._db is None:
            return
        
        column_hash = self._compute_hash(column_name, sample_values)
        
        self._db.save_detection(
            column_hash=column_hash,
            column_name=column_name,
            workflow=result.workflow,
            subtype=result.subtype,
            confidence=result.confidence,
            detection_source=result.source.value if result.source else "cache",
            sample_values=sample_values,
        )
        
        logger.debug(f"Cached: {column_name} -> {result.workflow}/{result.subtype}")
    
    def add_alias(self, alias: str, canonical: str):
        """
        Add a column name alias.
        
        Args:
            alias: Alias name
            canonical: Canonical column name
        """
        if self._db is None:
            return
        
        self._db.save_alias(alias.lower(), canonical.lower())
    
    def resolve_alias(self, name: str) -> str:
        """
        Resolve column name alias.
        
        Args:
            name: Column name or alias
            
        Returns:
            Canonical column name
        """
        if self._db is None:
            return name
        
        canonical = self._db.get_alias(name.lower())
        return canonical if canonical else name
    
    def clear(self):
        """Clear all cached data - NOT RECOMMENDED"""
        logger.warning("clear() called on DetectionCache - use db_manager.clear_all() instead")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if self._db is None:
            return {"error": "db_manager not initialized"}
        
        stats = self._db.get_stats()
        return {
            "cached_columns": stats.get("detection_cache", 0),
            "aliases": stats.get("column_aliases", 0),
            "db_path": "unified_cache.db",
        }
