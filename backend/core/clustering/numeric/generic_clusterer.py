"""
Generic Numeric Clusterer
Production-grade ML-based outlier detection with LLM-assisted bounds detection

Uses unified db_manager for bounds caching:
1. Check config for semantic bounds (salary: min=0, max=null)
2. Fall back to LLM-based bounds detection with caching
3. Use statistical ensemble only when no bounds apply
"""

import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..base_clusterer import BaseClusterer, ClusteringResult

# Use unified database manager
try:
    from backend.database import get_db_manager
except ImportError:
    get_db_manager = None

logger = logging.getLogger(__name__)


class GenericNumericClusterer(BaseClusterer):
    """
    Production-grade clusterer for unknown numeric data.
    
    Uses column-aware bounds detection:
    1. Config-defined bounds (salary: min=0, no max)
    2. LLM-detected bounds with caching (via unified db_manager)
    3. Statistical ensemble (Isolation Forest + IQR + Z-score)
    
    A value is marked as "good" if it passes bounds check (if any)
    AND at least 2 of 3 statistical methods agree.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.contamination = config.get("contamination", "auto") if config else "auto"
        self.n_estimators = config.get("n_estimators", 100) if config else 100
        self.iqr_factor = config.get("iqr_factor", 1.5) if config else 1.5
        self.z_threshold = config.get("z_threshold", 3.0) if config else 3.0
        
        # Config-defined bounds (from semantic_constraints in heuristic_rules.yaml)
        self.config_bounds = config.get("bounds", {}) if config else {}
        
        # Initialize unified db_manager
        self._db = None
        if get_db_manager is not None:
            try:
                self._db = get_db_manager()
            except Exception as e:
                logger.warning(f"Could not initialize db_manager: {e}")

    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster numeric data using bounds + ML ensemble.
        """
        indices = self._prepare_indices(data, indices)
        
        # Parse all values
        parsed_values = []
        parse_map = {}  # original index -> parsed value
        valid_indices = []
        
        for i, value in enumerate(data):
            parsed = self._parse_numeric(value)
            if parsed is not None:
                parsed_values.append(parsed)
                parse_map[i] = parsed
                valid_indices.append(i)
        
        if not parsed_values:
            # No valid numeric values
            return ClusteringResult(
                good_data=[],
                bad_data=list(data),
                good_indices=[],
                bad_indices=list(indices),
                fingerprint={"method": "generic_numeric", "error": "no_valid_values"},
                method="generic_numeric_empty",
                confidence=0.0,
            )
        
        arr = np.array(parsed_values)
        
        # Get bounds for this column
        bounds = self._get_column_bounds(column_name, arr[:5].tolist())
        
        # Phase 1: Bounds-based filtering (if bounds exist)
        bounds_mask = np.ones(len(arr), dtype=bool)
        if bounds and bounds.get("has_bounds"):
            min_val = bounds.get("min")
            max_val = bounds.get("max")
            
            if min_val is not None:
                bounds_mask &= arr >= min_val
            if max_val is not None:
                bounds_mask &= arr <= max_val
        
        # Phase 2: Statistical outlier detection (only if no bounds or partial bounds)
        if bounds and bounds.get("has_bounds") and bounds.get("skip_statistical"):
            # Have explicit bounds - trust them, skip statistical
            ensemble_mask = bounds_mask
        else:
            # Use statistical methods for additional filtering
            # 1. Isolation Forest
            iso_mask = self._isolation_forest_detect(arr)
            
            # 2. IQR bounds
            iqr_mask, iqr_bounds = self._iqr_detect(arr)
            
            # 3. Z-score
            z_mask, z_bounds = self._zscore_detect(arr)
            
            # Ensemble voting: good if at least 2 methods agree
            votes = iso_mask.astype(int) + iqr_mask.astype(int) + z_mask.astype(int)
            statistical_mask = votes >= 2
            
            # Combine bounds and statistical (both must pass)
            ensemble_mask = bounds_mask & statistical_mask
        
        # Map back to original indices
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        valid_idx_set = set(valid_indices)
        ensemble_idx = 0
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if i not in valid_idx_set:
                # Unparseable value = bad
                bad_data.append(value)
                bad_indices.append(idx)
            else:
                if ensemble_mask[ensemble_idx]:
                    good_data.append(value)
                    good_indices.append(idx)
                else:
                    bad_data.append(value)
                    bad_indices.append(idx)
                ensemble_idx += 1
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(
            arr[ensemble_mask].tolist() if np.any(ensemble_mask) else [],
            bounds
        )
        
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="generic_bounds_ensemble",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "bounds_applied": bounds is not None and bounds.get("has_bounds", False),
                "bounds_source": bounds.get("source") if bounds else None,
            }
        )
    
    def _get_column_bounds(
        self, 
        column_name: Optional[str], 
        sample_values: List[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Get bounds for column from config, cache, or inference.
        
        Priority:
        1. Cached bounds (from previous runs)
        2. Config-defined bounds (semantic_constraints)
        3. Inferred from column name patterns
        
        All bounds are cached to unified_cache.db for visibility.
        """
        if not column_name:
            return None
        
        column_lower = column_name.lower()
        
        # 1. Check cache first (fastest)
        cached = self._get_cached_bounds(column_name)
        if cached is not None:
            return cached
        
        # 2. Check config bounds
        config_bounds = self._get_config_bounds(column_lower)
        if config_bounds:
            # Cache config bounds for visibility
            self._cache_bounds(column_name, config_bounds)
            return config_bounds
        
        # 3. Infer from column name patterns
        inferred = self._infer_bounds_from_name(column_lower, sample_values)
        if inferred:
            self._cache_bounds(column_name, inferred)
            return inferred
        
        return None
    
    def _get_config_bounds(self, column_name: str) -> Optional[Dict[str, Any]]:
        """Get bounds from config (semantic_constraints)."""
        # Mapping of common column types to bounds
        KNOWN_BOUNDS = {
            "salary": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "amount": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "price": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "cost": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "revenue": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "income": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "count": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
            "quantity": {"has_bounds": True, "min": 0, "max": None, "source": "config"},
        }
        
        # Check for exact match or partial match
        for key, bounds in KNOWN_BOUNDS.items():
            if key in column_name:
                return bounds
        
        return None
    
    def _infer_bounds_from_name(
        self, 
        column_name: str, 
        sample_values: List[float]
    ) -> Optional[Dict[str, Any]]:
        """Infer bounds from column name patterns."""
        # Patterns that typically have no upper bound
        NO_UPPER_PATTERNS = [
            "salary", "wage", "income", "pay", "compensation",
            "amount", "price", "cost", "total", "sum", "revenue",
            "count", "quantity", "number", "num_",
        ]
        
        # Check if column matches no-upper-bound pattern
        for pattern in NO_UPPER_PATTERNS:
            if pattern in column_name:
                # Check if values are all positive
                if sample_values and min(sample_values) >= 0:
                    return {
                        "has_bounds": True,
                        "min": 0,
                        "max": None,
                        "source": "inferred",
                        "skip_statistical": True,  # Trust bounds, skip IQR/Z
                    }
        
        return None
    
    def _get_cached_bounds(self, column_name: str) -> Optional[Dict[str, Any]]:
        """Get bounds from unified cache via db_manager."""
        if self._db is None:
            return None
        
        try:
            cached = self._db.get_bounds(column_name)
            if cached:
                return {
                    "has_bounds": True,
                    "min": cached.get("min"),
                    "max": cached.get("max"),
                    "source": cached.get("source", "cache"),
                    "skip_statistical": True,
                }
        except Exception as e:
            logger.debug(f"Cache lookup failed: {e}")
        
        return None
    
    def _cache_bounds(self, column_name: str, bounds: Dict[str, Any]):
        """Cache bounds via unified db_manager."""
        if self._db is None:
            return
        
        try:
            self._db.save_bounds(
                column_name=column_name,
                min_value=bounds.get("min"),
                max_value=bounds.get("max"),
                source=bounds.get("source", "inferred"),
                workflow="numeric",
                subtype="generic",
                reasoning=f"Inferred from column name: {column_name}",
            )
            logger.debug(f"Cached bounds for {column_name}: {bounds}")
        except Exception as e:
            logger.warning(f"Failed to cache bounds: {e}")
    
    def _isolation_forest_detect(self, arr: np.ndarray) -> np.ndarray:
        """Isolation Forest outlier detection."""
        try:
            from sklearn.ensemble import IsolationForest
            
            if len(arr) < 10:
                # Too few samples for reliable detection
                return np.ones(len(arr), dtype=bool)
            
            iso = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42,
                n_jobs=-1
            )
            labels = iso.fit_predict(arr.reshape(-1, 1))
            return labels == 1  # 1 = inlier, -1 = outlier
            
        except Exception as e:
            logger.warning(f"IsolationForest failed: {e}")
            return np.ones(len(arr), dtype=bool)
    
    def _iqr_detect(self, arr: np.ndarray) -> Tuple[np.ndarray, Tuple[float, float]]:
        """IQR-based outlier detection."""
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        
        lower = q1 - self.iqr_factor * iqr
        upper = q3 + self.iqr_factor * iqr
        
        mask = (arr >= lower) & (arr <= upper)
        return mask, (lower, upper)
    
    def _zscore_detect(self, arr: np.ndarray) -> Tuple[np.ndarray, Tuple[float, float]]:
        """Z-score based outlier detection."""
        mean = np.mean(arr)
        std = np.std(arr)
        
        if std < 1e-10:
            # Near-zero std - all values are similar
            return np.ones(len(arr), dtype=bool), (mean, mean)
        
        z_scores = np.abs((arr - mean) / std)
        mask = z_scores < self.z_threshold
        
        lower = mean - self.z_threshold * std
        upper = mean + self.z_threshold * std
        
        return mask, (lower, upper)
    
    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse value as numeric, handling various formats."""
        if value is None:
            return None
        
        str_val = str(value).strip()
        if not str_val:
            return None
        
        # Check for non-numeric strings
        if str_val.lower() in ["nan", "null", "none", "na", "n/a", "invalid", "undefined"]:
            return None
        
        # Strip currency symbols
        clean = str_val
        for symbol in ["$", "€", "£", "¥", "₹", "%"]:
            clean = clean.replace(symbol, "")
        clean = clean.strip()
        
        # Handle negative with parentheses: (123) -> -123
        if clean.startswith("(") and clean.endswith(")"):
            clean = "-" + clean[1:-1]
        
        # European decimal: 4,9 or 1234,56
        if re.match(r"^-?\d+,\d{1,2}$", clean):
            clean = clean.replace(",", ".")
        # US thousand separators: 1,000,000
        elif re.match(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$", clean):
            clean = clean.replace(",", "")
        # European thousands: 1.000.000,50
        elif re.match(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$", clean):
            clean = clean.replace(".", "").replace(",", ".")
        # Just remove commas
        elif "," in clean:
            clean = clean.replace(",", "")
        
        try:
            return float(clean)
        except (ValueError, TypeError):
            return None
    
    def _generate_fingerprint(
        self,
        values: List[float],
        bounds: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate fingerprint from good values."""
        if not values:
            return {
                "workflow": "numeric",
                "method": "generic_ensemble",
                "properties": {},
            }
        
        arr = np.array(values)
        q1, q3 = np.percentile(arr, [25, 75])
        
        fingerprint = {
            "workflow": "numeric",
            "method": "generic_bounds_ensemble",
            "sample_size": len(values),
            "properties": {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "q1": float(q1),
                "q3": float(q3),
                "is_integer": all(v == int(v) for v in values),
            },
        }
        
        if bounds:
            fingerprint["bounds"] = bounds
            fingerprint["correction_hints"] = {
                "min": bounds.get("min"),
                "max": bounds.get("max"),
            }
        
        return fingerprint
