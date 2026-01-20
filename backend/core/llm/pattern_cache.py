"""
LLM Pattern Cache
SQLite-based cache for LLM-generated patterns
Reduces LLM costs by caching patterns based on fingerprint similarity
"""

import json
import sqlite3
import hashlib
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMPatternCache:
    """
    SQLite-based cache for LLM-generated patterns.
    
    Key Strategy:
    - Hash fingerprint properties to create cache key
    - Store patterns with metadata
    - Lookup by fingerprint hash before calling LLM
    
    Cost Savings:
    - Same column type + similar data = same patterns = no LLM call
    """
    
    def __init__(self, db_path: str = "llm_pattern_cache.db"):
        self.db_path = Path(db_path)
        self._init_db()
        logger.info(f"LLMPatternCache initialized: {self.db_path}")
    
    def _init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint_hash TEXT UNIQUE NOT NULL,
                workflow TEXT NOT NULL,
                subtype TEXT NOT NULL,
                column_name TEXT,
                patterns TEXT NOT NULL,
                constraints TEXT,
                sample_values TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 1,
                llm_model TEXT,
                llm_tokens_used INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fingerprint_hash 
            ON pattern_cache(fingerprint_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_subtype 
            ON pattern_cache(workflow, subtype)
        """)
        
        conn.commit()
        conn.close()
    
    def _compute_fingerprint_hash(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any]
    ) -> str:
        """
        Compute hash from fingerprint for cache lookup.
        
        Uses:
        - workflow + subtype
        - Key fingerprint properties (not sample values)
        - Constraints
        """
        # Extract key properties for hashing
        hash_data = {
            "workflow": workflow,
            "subtype": subtype,
        }
        
        # Add relevant fingerprint properties
        if fingerprint:
            props = fingerprint.get("properties", {})
            if props:
                # For numeric: use is_integer, rough range
                if workflow == "numeric":
                    hash_data["is_integer"] = props.get("is_integer")
                    # Round min/max to reduce uniqueness
                    if "min" in props:
                        hash_data["min_range"] = int(props["min"] // 100) * 100
                    if "max" in props:
                        hash_data["max_range"] = int(props["max"] // 100) * 100
                
                # For text: use length range, pattern type
                if workflow == "text":
                    hash_data["avg_length"] = fingerprint.get("avg_length")
                    hash_data["case_style"] = fingerprint.get("case_style")
            
            # Include constraints
            constraints = fingerprint.get("constraints", {})
            if constraints:
                hash_data["constraints"] = json.dumps(constraints, sort_keys=True)
        
        # Create deterministic hash
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:32]
    
    def get_patterns(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any]
    ) -> Optional[List[str]]:
        """
        Get cached patterns for a fingerprint.
        
        Args:
            workflow: Workflow type
            subtype: Subtype
            fingerprint: Fingerprint dict
            
        Returns:
            List of patterns or None if not cached
        """
        fingerprint_hash = self._compute_fingerprint_hash(
            workflow, subtype, fingerprint
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT patterns FROM pattern_cache 
            WHERE fingerprint_hash = ?
        """, (fingerprint_hash,))
        
        row = cursor.fetchone()
        
        if row:
            # Update usage stats
            cursor.execute("""
                UPDATE pattern_cache 
                SET last_used_at = ?, use_count = use_count + 1
                WHERE fingerprint_hash = ?
            """, (datetime.now().isoformat(), fingerprint_hash))
            conn.commit()
            
            patterns = json.loads(row[0])
            logger.info(f"Cache HIT: {workflow}/{subtype} → {len(patterns)} patterns")
            conn.close()
            return patterns
        
        conn.close()
        logger.debug(f"Cache MISS: {workflow}/{subtype}")
        return None
    
    def save_patterns(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any],
        patterns: List[str],
        column_name: Optional[str] = None,
        llm_model: Optional[str] = None,
        tokens_used: int = 0
    ):
        """
        Save LLM-generated patterns to cache.
        
        Args:
            workflow: Workflow type
            subtype: Subtype
            fingerprint: Fingerprint dict
            patterns: List of regex patterns
            column_name: Original column name
            llm_model: LLM model used
            tokens_used: Tokens consumed
        """
        fingerprint_hash = self._compute_fingerprint_hash(
            workflow, subtype, fingerprint
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO pattern_cache 
                (fingerprint_hash, workflow, subtype, column_name, patterns, 
                 constraints, sample_values, llm_model, llm_tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fingerprint_hash,
                workflow,
                subtype,
                column_name,
                json.dumps(patterns),
                json.dumps(fingerprint.get("constraints", {})),
                json.dumps(fingerprint.get("common_values", [])[:5]),
                llm_model,
                tokens_used,
            ))
            
            conn.commit()
            logger.info(
                f"Cached patterns: {workflow}/{subtype} → {len(patterns)} patterns "
                f"(tokens: {tokens_used})"
            )
        except Exception as e:
            logger.error(f"Failed to cache patterns: {e}")
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM pattern_cache")
        total_entries = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(use_count) FROM pattern_cache")
        total_hits = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(llm_tokens_used) FROM pattern_cache")
        total_tokens_saved = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT workflow, subtype, use_count 
            FROM pattern_cache 
            ORDER BY use_count DESC 
            LIMIT 5
        """)
        top_patterns = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_cached_patterns": total_entries,
            "total_cache_hits": total_hits - total_entries,  # Subtract initial saves
            "tokens_saved": total_tokens_saved * (total_hits - total_entries),
            "top_patterns": [
                {"workflow": w, "subtype": s, "hits": h}
                for w, s, h in top_patterns
            ]
        }
    
    def clear(self):
        """Clear all cached patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pattern_cache")
        conn.commit()
        conn.close()
        logger.info("Pattern cache cleared")
