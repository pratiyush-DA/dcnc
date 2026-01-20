"""
Unified Database Manager
========================
Single point of contact for ALL database operations in the application.

Design Principles:
- Single Responsibility: All DB ops go through this file
- Abstraction: Easy to swap backends (SQLite → PostgreSQL → MongoDB)
- Caching: LLM patterns, bounds, detection, fingerprints
- Analytics: Track LLM usage for cost optimization

Tables:
- pattern_cache: LLM-generated validation patterns
- column_aliases: Smart column name matching
- column_bounds: Numeric min/max bounds
- detection_cache: Column type detection results
- fingerprints: Good data fingerprints for correction
- llm_calls: LLM call log for analytics

Author: Production Data Quality Pipeline
Version: 1.0.0
"""

import json
import sqlite3
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Database path - single file for all caching
DB_PATH = Path(__file__).parent / "unified_cache.db"


@dataclass
class CachedPattern:
    """Cached LLM pattern with metadata."""
    patterns: List[str]
    bounds: Optional[Dict[str, Any]]
    description: str
    workflow: str
    subtype: str
    column_name: Optional[str]
    use_count: int
    created_at: str


@dataclass
class ColumnFingerprint:
    """Standardized fingerprint for correction engine."""
    column_name: str
    workflow: str
    subtype: str
    clusterer: str
    fingerprint: Dict[str, Any]
    correction_hints: Dict[str, Any]
    sample_good_values: List[Any]
    good_count: int
    bad_count: int


class UnifiedDBManager:
    """
    Centralized database manager for all caching operations.
    
    Usage:
        db = UnifiedDBManager()
        
        # Pattern cache
        patterns = db.get_cached_patterns("string", "email", fingerprint_hash)
        db.save_patterns("string", "email", hash, patterns, bounds=None)
        
        # Column aliases
        canonical = db.get_alias("customer_name")  # Returns "name"
        db.save_alias("client_name", "name", hash)
        
        # Fingerprints
        db.save_fingerprint(column_name, fingerprint_obj)
        db.export_fingerprints_json("output/fingerprints.json")
    """
    
    _instance = None
    
    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern for shared connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager."""
        if self._initialized:
            return
            
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._initialized = True
        logger.info(f"UnifiedDBManager initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize all database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Pattern Cache - LLM-generated patterns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pattern_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint_hash TEXT UNIQUE NOT NULL,
                    workflow TEXT NOT NULL,
                    subtype TEXT NOT NULL,
                    column_name TEXT,
                    patterns TEXT NOT NULL,
                    bounds TEXT,
                    description TEXT,
                    constraints TEXT,
                    sample_values TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 1,
                    llm_model TEXT,
                    tokens_used INTEGER DEFAULT 0
                )
            """)
            
            # 2. Column Aliases - Smart name matching
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS column_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_name TEXT NOT NULL,
                    alias_name TEXT UNIQUE NOT NULL,
                    fingerprint_hash TEXT,
                    normalized_name TEXT,
                    match_confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. Column Bounds - Numeric limits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS column_bounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column_name TEXT UNIQUE NOT NULL,
                    min_value REAL,
                    max_value REAL,
                    source TEXT NOT NULL,
                    workflow TEXT,
                    subtype TEXT,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # 4. Detection Cache - Column type detection
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column_hash TEXT UNIQUE NOT NULL,
                    column_name TEXT,
                    workflow TEXT NOT NULL,
                    subtype TEXT NOT NULL,
                    confidence REAL,
                    detection_source TEXT,
                    sample_values TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 5. Fingerprints - Good data fingerprints for correction
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column_name TEXT UNIQUE NOT NULL,
                    workflow TEXT NOT NULL,
                    subtype TEXT NOT NULL,
                    clusterer TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    correction_hints TEXT,
                    sample_good_values TEXT,
                    good_count INTEGER DEFAULT 0,
                    bad_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 6. LLM Calls - Usage analytics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    purpose TEXT NOT NULL,
                    column_name TEXT,
                    workflow TEXT,
                    subtype TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    from_cache BOOLEAN DEFAULT 0,
                    model TEXT,
                    latency_ms REAL,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pattern_hash 
                ON pattern_cache(fingerprint_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pattern_workflow 
                ON pattern_cache(workflow, subtype)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alias_canonical 
                ON column_aliases(canonical_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alias_normalized 
                ON column_aliases(normalized_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprint_workflow 
                ON fingerprints(workflow, subtype)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_detection_hash 
                ON detection_cache(column_hash)
            """)
            
            logger.debug("Database tables initialized")
    
    # ==================== PATTERN CACHE ====================
    
    def compute_fingerprint_hash(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any]
    ) -> str:
        """
        Compute deterministic hash from fingerprint.
        
        Uses workflow + subtype + key properties (not sample values).
        """
        hash_data = {
            "workflow": workflow,
            "subtype": subtype,
        }
        
        if fingerprint:
            props = fingerprint.get("properties", {})
            if props:
                # Numeric: use is_integer, rough range
                if workflow == "numeric":
                    hash_data["is_integer"] = props.get("is_integer")
                    if "min" in props and props["min"] is not None:
                        hash_data["min_range"] = int(props["min"] // 100) * 100
                    if "max" in props and props["max"] is not None:
                        hash_data["max_range"] = int(props["max"] // 100) * 100
                
                # String: use length range, case style
                if workflow in ("text", "string"):
                    if "avg_length" in props:
                        hash_data["length_range"] = int(props["avg_length"] // 5) * 5
                    hash_data["case_style"] = props.get("case_style")
            
            # Include constraints
            constraints = fingerprint.get("constraints", {})
            if constraints:
                hash_data["constraints"] = json.dumps(constraints, sort_keys=True)
        
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:32]
    
    def get_cached_patterns(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any]
    ) -> Optional[CachedPattern]:
        """
        Get cached patterns for fingerprint.
        
        Returns:
            CachedPattern or None if cache miss
        """
        fp_hash = self.compute_fingerprint_hash(workflow, subtype, fingerprint)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT patterns, bounds, description, workflow, subtype,
                       column_name, use_count, created_at
                FROM pattern_cache
                WHERE fingerprint_hash = ?
            """, (fp_hash,))
            
            row = cursor.fetchone()
            if row:
                # Update usage stats
                cursor.execute("""
                    UPDATE pattern_cache 
                    SET use_count = use_count + 1, last_used_at = ?
                    WHERE fingerprint_hash = ?
                """, (datetime.now().isoformat(), fp_hash))
                
                return CachedPattern(
                    patterns=json.loads(row["patterns"]),
                    bounds=json.loads(row["bounds"]) if row["bounds"] else None,
                    description=row["description"] or "",
                    workflow=row["workflow"],
                    subtype=row["subtype"],
                    column_name=row["column_name"],
                    use_count=row["use_count"],
                    created_at=row["created_at"],
                )
        
        return None
    
    def save_patterns(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any],
        patterns: List[str],
        bounds: Optional[Dict[str, Any]] = None,
        description: str = "",
        column_name: Optional[str] = None,
        llm_model: Optional[str] = None,
        tokens_used: int = 0
    ) -> str:
        """
        Save LLM-generated patterns to cache.
        
        Returns:
            Fingerprint hash
        """
        fp_hash = self.compute_fingerprint_hash(workflow, subtype, fingerprint)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pattern_cache
                (fingerprint_hash, workflow, subtype, column_name, patterns,
                 bounds, description, sample_values, llm_model, tokens_used,
                 created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fp_hash,
                workflow,
                subtype,
                column_name,
                json.dumps(patterns),
                json.dumps(bounds) if bounds else None,
                description,
                json.dumps(fingerprint.get("sample_values", [])),
                llm_model,
                tokens_used,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ))
        
        logger.debug(f"Cached patterns for {workflow}/{subtype}: {fp_hash[:8]}...")
        return fp_hash
    
    # ==================== COLUMN ALIASES ====================
    
    @staticmethod
    def normalize_column_name(name: str) -> str:
        """Normalize column name for matching."""
        import re
        # Lowercase, remove common suffixes
        normalized = name.lower().strip()
        # Remove common prefixes/suffixes
        for suffix in ["_id", "_col", "_column", "_field", "_value"]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        for prefix in ["col_", "field_", "fld_"]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        # Replace separators with underscore
        normalized = re.sub(r"[-\s]+", "_", normalized)
        return normalized
    
    def get_alias(self, column_name: str) -> Optional[str]:
        """
        Get canonical name for column alias.
        
        Returns:
            Canonical column name or None
        """
        normalized = self.normalize_column_name(column_name)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Exact alias match
            cursor.execute("""
                SELECT canonical_name FROM column_aliases
                WHERE alias_name = ? OR normalized_name = ?
            """, (column_name, normalized))
            
            row = cursor.fetchone()
            if row:
                return row["canonical_name"]
        
        return None
    
    def save_alias(
        self,
        alias_name: str,
        canonical_name: str,
        fingerprint_hash: Optional[str] = None,
        confidence: float = 1.0
    ):
        """Save column alias mapping."""
        normalized = self.normalize_column_name(alias_name)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO column_aliases
                (canonical_name, alias_name, fingerprint_hash, normalized_name, match_confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (canonical_name, alias_name, fingerprint_hash, normalized, confidence))
        
        logger.debug(f"Saved alias: {alias_name} → {canonical_name}")
    
    def find_similar_alias(
        self,
        column_name: str,
        threshold: float = 0.85
    ) -> Optional[Tuple[str, float]]:
        """
        Find similar column by normalized name.
        
        Returns:
            (canonical_name, confidence) or None
        """
        normalized = self.normalize_column_name(column_name)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT canonical_name, normalized_name
                FROM column_aliases
            """)
            
            for row in cursor.fetchall():
                existing_normalized = row["normalized_name"]
                if existing_normalized and self._name_similarity(normalized, existing_normalized) >= threshold:
                    return (row["canonical_name"], threshold)
        
        return None
    
    @staticmethod
    def _name_similarity(name1: str, name2: str) -> float:
        """Simple similarity score between names."""
        if name1 == name2:
            return 1.0
        
        # Check if one contains the other
        if name1 in name2 or name2 in name1:
            return 0.9
        
        # Token overlap
        tokens1 = set(name1.split("_"))
        tokens2 = set(name2.split("_"))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        overlap = len(tokens1 & tokens2)
        total = len(tokens1 | tokens2)
        
        return overlap / total if total > 0 else 0.0
    
    # ==================== COLUMN BOUNDS ====================
    
    def get_bounds(self, column_name: str) -> Optional[Dict[str, Any]]:
        """Get cached bounds for column."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT min_value, max_value, source, reasoning
                FROM column_bounds
                WHERE column_name = ?
            """, (column_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "min": row["min_value"],
                    "max": row["max_value"],
                    "source": row["source"],
                    "reasoning": row["reasoning"],
                }
        
        return None
    
    def save_bounds(
        self,
        column_name: str,
        min_value: Optional[float],
        max_value: Optional[float],
        source: str,
        workflow: str = "numeric",
        subtype: str = "generic",
        reasoning: str = ""
    ):
        """Save bounds for column."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO column_bounds
                (column_name, min_value, max_value, source, workflow, subtype, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (column_name, min_value, max_value, source, workflow, subtype, reasoning))
        
        logger.debug(f"Saved bounds for {column_name}: [{min_value}, {max_value}] ({source})")
    
    # ==================== DETECTION CACHE ====================
    
    def get_detection(self, column_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached detection result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT workflow, subtype, confidence, detection_source, column_name
                FROM detection_cache
                WHERE column_hash = ?
            """, (column_hash,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "workflow": row["workflow"],
                    "subtype": row["subtype"],
                    "confidence": row["confidence"],
                    "source": row["detection_source"],
                    "column_name": row["column_name"],
                }
        
        return None
    
    def save_detection(
        self,
        column_hash: str,
        column_name: str,
        workflow: str,
        subtype: str,
        confidence: float,
        detection_source: str,
        sample_values: Optional[List[Any]] = None
    ):
        """Save detection result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO detection_cache
                (column_hash, column_name, workflow, subtype, confidence, 
                 detection_source, sample_values)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                column_hash, column_name, workflow, subtype, confidence,
                detection_source, json.dumps(sample_values[:10]) if sample_values else None
            ))
    
    # ==================== FINGERPRINTS ====================
    
    def get_fingerprint(self, column_name: str) -> Optional[ColumnFingerprint]:
        """Get stored fingerprint for column."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fingerprints WHERE column_name = ?
            """, (column_name,))
            
            row = cursor.fetchone()
            if row:
                return ColumnFingerprint(
                    column_name=row["column_name"],
                    workflow=row["workflow"],
                    subtype=row["subtype"],
                    clusterer=row["clusterer"],
                    fingerprint=json.loads(row["fingerprint"]),
                    correction_hints=json.loads(row["correction_hints"]) if row["correction_hints"] else {},
                    sample_good_values=json.loads(row["sample_good_values"]) if row["sample_good_values"] else [],
                    good_count=row["good_count"],
                    bad_count=row["bad_count"],
                )
        
        return None
    
    def save_fingerprint(
        self,
        column_name: str,
        workflow: str,
        subtype: str,
        clusterer: str,
        fingerprint: Dict[str, Any],
        correction_hints: Dict[str, Any],
        sample_good_values: List[Any],
        good_count: int = 0,
        bad_count: int = 0
    ):
        """Save fingerprint for correction engine."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO fingerprints
                (column_name, workflow, subtype, clusterer, fingerprint,
                 correction_hints, sample_good_values, good_count, bad_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                column_name,
                workflow,
                subtype,
                clusterer,
                json.dumps(fingerprint),
                json.dumps(correction_hints),
                json.dumps(sample_good_values[:20]),  # Limit samples
                good_count,
                bad_count,
                datetime.now().isoformat(),
            ))
        
        logger.debug(f"Saved fingerprint for {column_name}: {workflow}/{subtype}/{clusterer}")
    
    def export_fingerprints_json(self, output_path: str) -> Dict[str, Any]:
        """
        Export all fingerprints to JSON file for correction engine.
        
        Returns:
            Complete fingerprints dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fingerprints")
            
            columns = {}
            for row in cursor.fetchall():
                columns[row["column_name"]] = {
                    "workflow": row["workflow"],
                    "subtype": row["subtype"],
                    "clusterer": row["clusterer"],
                    "good_count": row["good_count"],
                    "bad_count": row["bad_count"],
                    "fingerprint": json.loads(row["fingerprint"]),
                    "correction_hints": json.loads(row["correction_hints"]) if row["correction_hints"] else {},
                    "sample_good_values": json.loads(row["sample_good_values"]) if row["sample_good_values"] else [],
                }
            
            result = {
                "generated_at": datetime.now().isoformat(),
                "total_columns": len(columns),
                "columns": columns,
            }
            
            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Exported {len(columns)} fingerprints to {output_path}")
            return result
    
    # ==================== LLM CALL LOG ====================
    
    def log_llm_call(
        self,
        purpose: str,
        column_name: Optional[str] = None,
        workflow: Optional[str] = None,
        subtype: Optional[str] = None,
        tokens_used: int = 0,
        from_cache: bool = False,
        model: Optional[str] = None,
        latency_ms: float = 0,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log LLM call for analytics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO llm_calls
                (purpose, column_name, workflow, subtype, tokens_used,
                 from_cache, model, latency_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                purpose, column_name, workflow, subtype, tokens_used,
                from_cache, model, latency_ms, success, error_message
            ))
    
    def get_llm_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total calls
            cursor.execute("SELECT COUNT(*) as count FROM llm_calls")
            total_calls = cursor.fetchone()["count"]
            
            # Cache hits
            cursor.execute("SELECT COUNT(*) as count FROM llm_calls WHERE from_cache = 1")
            cache_hits = cursor.fetchone()["count"]
            
            # Total tokens
            cursor.execute("SELECT SUM(tokens_used) as total FROM llm_calls")
            total_tokens = cursor.fetchone()["total"] or 0
            
            # By purpose
            cursor.execute("""
                SELECT purpose, COUNT(*) as count, SUM(tokens_used) as tokens
                FROM llm_calls GROUP BY purpose
            """)
            by_purpose = {row["purpose"]: {"calls": row["count"], "tokens": row["tokens"]} 
                         for row in cursor.fetchall()}
            
            return {
                "total_calls": total_calls,
                "cache_hits": cache_hits,
                "cache_hit_rate": cache_hits / total_calls if total_calls > 0 else 0,
                "total_tokens": total_tokens,
                "by_purpose": by_purpose,
            }
    
    # ==================== UTILITIES ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            for table in ["pattern_cache", "column_aliases", "column_bounds", 
                         "detection_cache", "fingerprints", "llm_calls"]:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()["count"]
            
            return stats
    
    def clear_all(self):
        """Clear all cached data (use with caution)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for table in ["pattern_cache", "column_aliases", "column_bounds",
                         "detection_cache", "fingerprints", "llm_calls"]:
                cursor.execute(f"DELETE FROM {table}")
        
        logger.warning("All cache data cleared")
    
    def migrate_from_legacy(self):
        """Migrate data from old .db files."""
        legacy_files = [
            ("llm_pattern_cache.db", self._migrate_pattern_cache),
            ("backend/database/bounds_cache.db", self._migrate_bounds_cache),
            ("data/detection_cache.db", self._migrate_detection_cache),
        ]
        
        for legacy_path, migrate_func in legacy_files:
            legacy_file = Path(legacy_path)
            if legacy_file.exists():
                try:
                    migrate_func(legacy_file)
                    # Rename to backup
                    legacy_file.rename(f"{legacy_file}.backup")
                    logger.info(f"Migrated and backed up: {legacy_path}")
                except Exception as e:
                    logger.warning(f"Could not migrate {legacy_path}: {e}")
    
    def _migrate_pattern_cache(self, legacy_file: Path):
        """Migrate from old pattern_cache.db."""
        legacy_conn = sqlite3.connect(str(legacy_file))
        legacy_conn.row_factory = sqlite3.Row
        
        cursor = legacy_conn.cursor()
        cursor.execute("SELECT * FROM pattern_cache")
        
        for row in cursor.fetchall():
            self.save_patterns(
                workflow=row["workflow"],
                subtype=row["subtype"],
                fingerprint={"sample_values": json.loads(row["sample_values"] or "[]")},
                patterns=json.loads(row["patterns"]),
                column_name=row["column_name"],
                llm_model=row["llm_model"],
                tokens_used=row["llm_tokens_used"] or 0,
            )
        
        legacy_conn.close()
    
    def _migrate_bounds_cache(self, legacy_file: Path):
        """Migrate from old bounds_cache.db."""
        legacy_conn = sqlite3.connect(str(legacy_file))
        legacy_conn.row_factory = sqlite3.Row
        
        cursor = legacy_conn.cursor()
        try:
            cursor.execute("SELECT * FROM column_bounds")
            
            for row in cursor.fetchall():
                bounds = json.loads(row["bounds"]) if row["bounds"] else {}
                self.save_bounds(
                    column_name=row["column_name"],
                    min_value=bounds.get("min"),
                    max_value=bounds.get("max"),
                    source=row["source"] or "legacy",
                )
        except sqlite3.OperationalError:
            pass  # Table doesn't exist
        
        legacy_conn.close()
    
    def _migrate_detection_cache(self, legacy_file: Path):
        """Migrate from old detection_cache.db."""
        legacy_conn = sqlite3.connect(str(legacy_file))
        legacy_conn.row_factory = sqlite3.Row
        
        cursor = legacy_conn.cursor()
        try:
            cursor.execute("SELECT * FROM detection_cache")
            
            for row in cursor.fetchall():
                self.save_detection(
                    column_hash=row["column_hash"],
                    column_name=row.get("column_name", ""),
                    workflow=row["workflow"],
                    subtype=row["subtype"],
                    confidence=row.get("confidence", 0.9),
                    detection_source=row.get("detection_source", "legacy"),
                )
        except sqlite3.OperationalError:
            pass
        
        legacy_conn.close()


# Singleton instance for easy import
_db_manager: Optional[UnifiedDBManager] = None


def get_db_manager() -> UnifiedDBManager:
    """Get singleton instance of database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = UnifiedDBManager()
    return _db_manager
