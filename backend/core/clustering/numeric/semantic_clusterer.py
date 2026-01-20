"""
Semantic Numeric Clusterer
For numeric subtypes with known semantic bounds (age, rating, year, etc.)
"""

import re
import logging
from typing import Any, Dict, List, Optional
import numpy as np

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class SemanticNumericClusterer(BaseClusterer):
    """
    Clusterer for numeric data with known semantic constraints.
    
    Uses IQR statistics within semantic bounds for outlier detection.
    
    Supported configs:
        - min: Minimum allowed value
        - max: Maximum allowed value
        - type: "integer" or "float"
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.min_val = config.get("min", float("-inf")) if config else float("-inf")
        self.max_val = config.get("max", float("inf")) if config else float("inf")
        self.expected_type = config.get("type", "float") if config else "float"
        # Make outlier detection configurable (default True for backward compatibility)
        self.outlier_detection = config.get("outlier_detection", True) if config else True
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster numeric data using semantic constraints + IQR.
        Dynamically adjusts rating scale based on data.
        """
        indices = self._prepare_indices(data, indices)
        
        # Parse all values
        parsed_values = []
        parse_map = {}  # original index -> parsed value
        
        for i, value in enumerate(data):
            parsed = self._parse_numeric(value)
            if parsed is not None:
                parsed_values.append(parsed)
                parse_map[i] = parsed
        
        # Dynamic rating scale detection
        # If column is "rating" subtype, auto-detect scale based on data distribution
        effective_max = self.max_val
        if column_name and "rating" in column_name.lower() and self.max_val == 10:
            if parsed_values:
                # Use percentile-based detection
                # If 90%+ of values are <= 5, use 0-5 scale (5.1 would be anomaly)
                values_under_5 = sum(1 for v in parsed_values if v <= 5)
                pct_under_5 = values_under_5 / len(parsed_values)
                
                if pct_under_5 >= 0.9:
                    effective_max = 5
                    logger.debug(f"Auto-detected 0-5 rating scale for {column_name} ({pct_under_5:.0%} values <= 5)")
        
        # Calculate IQR bounds for additional outlier detection
        iqr_lower, iqr_upper = float("-inf"), float("inf")
        if parsed_values:
            arr = np.array(parsed_values)
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            iqr_lower = q1 - 1.5 * iqr
            iqr_upper = q3 + 1.5 * iqr
        
        # Classify each value
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            parsed = parse_map.get(i)
            
            if parsed is None:
                # Couldn't parse as number
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            is_valid = True
            
            # Semantic constraint check (use effective_max for dynamic rating scale)
            if parsed < self.min_val or parsed > effective_max:
                is_valid = False
            
            # Type check
            if self.expected_type == "integer" and parsed != int(parsed):
                is_valid = False
            
            # IQR outlier check (within semantic bounds)
            # Only apply if outlier detection is enabled
            if is_valid and self.outlier_detection and (parsed < iqr_lower or parsed > iqr_upper):
                # Outlier but within semantic bounds - still flag as bad
                is_valid = False
            
            if is_valid:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(
            [parse_map[i] for i in range(len(data)) if i in parse_map and data[i] in good_data]
        )
        
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="semantic_iqr",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "semantic_bounds": [self.min_val, self.max_val],
                "iqr_bounds": [iqr_lower, iqr_upper],
                "expected_type": self.expected_type,
            }
        )
    
    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse value as numeric, handling various formats."""
        if value is None:
            return None
        
        str_val = str(value).strip()
        if not str_val:
            return None
        
        # Strip currency symbols
        clean = str_val
        for symbol in ["$", "€", "£", "¥", "₹", "%"]:
            clean = clean.replace(symbol, "")
        clean = clean.strip()
        
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
    
    def _generate_fingerprint(self, values: List[float]) -> Dict[str, Any]:
        """Generate fingerprint from parsed numeric values."""
        if not values:
            return {
                "workflow": "numeric",
                "method": "semantic",
                "properties": {},
            }
        
        arr = np.array(values)
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        
        return {
            "workflow": "numeric",
            "method": "semantic",
            "sample_size": len(values),
            "properties": {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(iqr),
                "lower_bound": float(q1 - 1.5 * iqr),
                "upper_bound": float(q3 + 1.5 * iqr),
                "is_integer": all(v == int(v) for v in values),
            },
            "constraints": {
                "min": self.min_val,
                "max": self.max_val,
                "type": self.expected_type,
            }
        }
