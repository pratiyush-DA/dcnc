"""
Numeric Workflow
Handles numeric data types with semantic constraints
Supports currency, European decimals, and outlier detection
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from .base_workflow import BaseWorkflow
from ..interfaces import WorkflowType, ClusterResult
from ..registry import register_workflow
from ..clustering import get_clusterer

logger = logging.getLogger(__name__)


# Semantic constraints for numeric subtypes
SEMANTIC_CONSTRAINTS = {
    "age": {"min": 0, "max": 120, "type": "integer"},
    "rating": {"min": 0, "max": 10, "type": "float"},
    "year": {"min": 1900, "max": 2100, "type": "integer"},
    "latitude": {"min": -90, "max": 90, "type": "float"},
    "longitude": {"min": -180, "max": 180, "type": "float"},
    "percentage": {"min": 0, "max": 100, "type": "float"},
    "salary": {"min": 0, "type": "float"},  # No max
    "amount": {"min": 0, "type": "float"},  # No max
}


@register_workflow("numeric")
class NumericWorkflow(BaseWorkflow):
    """
    Numeric workflow handler.
    
    Supports 14 subtypes with smart parsing:
    - Currency formats ($150,000)
    - European decimals (4,9)
    - Semantic constraints (age 0-120, rating 0-10)
    - Statistical outlier detection
    """
    
    SUBTYPES = [
        "age", "year", "salary", "amount", "count",
        "rating", "percentage", "temperature",
        "latitude", "longitude",
        "phone_numeric", "zipcode_numeric", "numeric_id",
        "generic",
    ]
    
    @property
    def workflow_type(self) -> WorkflowType:
        return WorkflowType.NUMERIC
    
    @property
    def supported_subtypes(self) -> List[str]:
        return self.SUBTYPES
    
    @property
    def default_subtype(self) -> str:
        return "generic"
    
    def detect_subtype(
        self,
        data: List[Any],
        column_name: Optional[str] = None
    ) -> Tuple[str, float]:
        """Detect numeric subtype from data characteristics."""
        if not data:
            return self.default_subtype, 0.3
        
        # Parse all values
        parsed_data = []
        for v in data:
            parsed = self._parse_numeric(v)
            if parsed is not None:
                parsed_data.append(parsed)
        
        if not parsed_data:
            return self.default_subtype, 0.3
        
        # Analyze statistics
        min_val = min(parsed_data)
        max_val = max(parsed_data)
        is_integer = all(v == int(v) for v in parsed_data)
        
        # Check against semantic constraints
        for subtype, constraints in SEMANTIC_CONSTRAINTS.items():
            c_min = constraints.get("min", float("-inf"))
            c_max = constraints.get("max", float("inf"))
            c_type = constraints.get("type", "float")
            
            if min_val >= c_min and max_val <= c_max:
                if c_type == "integer" and is_integer:
                    return subtype, 0.7
                elif c_type == "float":
                    return subtype, 0.6
        
        return self.default_subtype, 0.5
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        **kwargs
    ) -> ClusterResult:
        """
        Cluster numeric data with semantic validation.
        Handles currency and European decimal formats.
        """
        # Get constraints for subtype
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        constraints = SEMANTIC_CONSTRAINTS.get(subtype, {})
        
        # Create indices
        if indices is None:
            indices = list(range(len(data)))
        
        good_data = []
        bad_data = []
        good_indices = []
        bad_indices = []
        parsed_good = []  # For fingerprint stats
        
        for value, idx in zip(data, indices):
            # Skip nulls
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            # Try to parse as numeric (handles currency, European decimals)
            parsed = self._parse_numeric(value)
            
            if parsed is None:
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            # Apply semantic constraints
            is_valid = True
            
            if "min" in constraints and parsed < constraints["min"]:
                is_valid = False
            
            if "max" in constraints and parsed > constraints["max"]:
                is_valid = False
            
            if constraints.get("type") == "integer" and parsed != int(parsed):
                is_valid = False
            
            if is_valid:
                good_data.append(value)
                good_indices.append(idx)
                parsed_good.append(parsed)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Generate fingerprint from parsed good values
        fingerprint_dict = None
        if parsed_good:
            fingerprint_dict = self._generate_numeric_fingerprint(
                parsed_good, subtype, constraints
            )
        
        # Calculate confidence
        total = len(good_data) + len(bad_data)
        confidence = len(good_data) / total if total > 0 else 0.0
        
        result = ClusterResult(
            good_data=good_data,
            bad_data=bad_data,
            workflow=self.workflow_type.value,
            subtype=subtype,
            confidence=confidence,
            fingerprint=fingerprint_dict,
            good_indices=good_indices,
            bad_indices=bad_indices,
            metadata={
                "column_name": column_name,
                "total_records": total,
                "constraints_applied": constraints,
            }
        )
        
        return result
    
    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse value as numeric, handling various formats."""
        if value is None:
            return None
        
        str_val = str(value).strip()
        if not str_val:
            return None
        
        # Strip currency symbols
        clean = str_val
        for symbol in ["$", "€", "£", "¥", "₹"]:
            clean = clean.replace(symbol, "")
        clean = clean.strip()
        
        # European decimal: 4,9 or 1234,56
        if re.match(r"^\d+,\d{1,2}$", clean):
            clean = clean.replace(",", ".")
        # US thousand separators: 1,000,000
        elif re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", clean):
            clean = clean.replace(",", "")
        # European thousands: 1.000.000,50
        elif re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", clean):
            clean = clean.replace(".", "").replace(",", ".")
        # Just remove commas
        elif "," in clean:
            clean = clean.replace(",", "")
        
        try:
            return float(clean)
        except (ValueError, TypeError):
            return None
    
    def _generate_numeric_fingerprint(
        self,
        values: List[float],
        subtype: str,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fingerprint from parsed numeric values."""
        import numpy as np
        
        arr = np.array(values)
        
        # Calculate IQR for outlier bounds
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return {
            "workflow": "numeric",
            "subtype": subtype,
            "sample_size": len(values),
            "properties": {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "is_integer": all(v == int(v) for v in values),
            },
            "constraints": constraints,
        }
    
    def cluster_v2(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        use_ml: bool = True,
        **kwargs
    ) -> ClusterResult:
        """
        Production-grade clustering using ML-based anomaly detection.
        
        Uses the new clustering module with:
        - Semantic constraints for known subtypes (age, rating, year)
        - Isolation Forest + IQR + Z-score ensemble for generic subtypes
        
        Args:
            data: Column data
            indices: Row indices
            column_name: Column name
            subtype: Detected subtype
            use_ml: Whether to use ML clustering (True) or legacy (False)
        """
        if not use_ml:
            # Fall back to legacy clustering
            return self.cluster(data, indices, column_name, subtype, **kwargs)
        
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        # Get appropriate clusterer from strategy selector
        try:
            clusterer = get_clusterer("numeric", subtype)
            result = clusterer.cluster(data, indices, column_name, **kwargs)
            
            # Convert ClusteringResult to ClusterResult
            return ClusterResult(
                good_data=result.good_data,
                bad_data=result.bad_data,
                workflow=self.workflow_type.value,
                subtype=subtype,
                confidence=result.confidence,
                fingerprint=result.fingerprint,
                good_indices=result.good_indices,
                bad_indices=result.bad_indices,
                metadata={
                    "column_name": column_name,
                    "total_records": result.total_count,
                    "clustering_method": result.method,
                    **result.metadata,
                }
            )
        except Exception as e:
            logger.warning(f"ML clustering failed: {e}, falling back to legacy")
            return self.cluster(data, indices, column_name, subtype, **kwargs)

