"""
Numeric Fingerprint Generator
Captures statistical characteristics of numeric data
"""

import math
from typing import Any, Dict, List, Optional
from collections import Counter

from .base_fingerprint import BaseFingerprint
from ..registry import register_fingerprint


@register_fingerprint("numeric")
class NumericFingerprint(BaseFingerprint):
    """
    Fingerprint generator for numeric data.
    
    Captures:
    - Statistical properties (mean, median, std, range)
    - Distribution characteristics
    - Integer vs float detection
    - Decimal places
    - Common values
    - Outlier boundaries
    """
    
    @property
    def workflow_type(self) -> str:
        return "numeric"
    
    def _generate_properties(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """Generate numeric-specific properties"""
        if not data:
            return {}
        
        # Convert to numeric values
        numeric_data = []
        for v in data:
            try:
                numeric_data.append(float(v))
            except (ValueError, TypeError):
                continue
        
        if not numeric_data:
            return {}
        
        # Basic statistics
        mean = self.safe_mean(numeric_data)
        median = self.safe_median(numeric_data)
        std = self.safe_stdev(numeric_data)
        min_val = min(numeric_data)
        max_val = max(numeric_data)
        
        # Integer detection (filter out NaN values)
        import math
        valid_numeric = [v for v in numeric_data if not math.isnan(v)]
        is_integer = all(v == int(v) for v in valid_numeric) if valid_numeric else False
        
        # Decimal places
        max_decimals = 0
        if not is_integer:
            for v in numeric_data:
                str_v = str(v)
                if "." in str_v:
                    decimals = len(str_v.split(".")[1])
                    max_decimals = max(max_decimals, decimals)
        
        # Distribution detection
        distribution = self._detect_distribution(numeric_data, mean, std)
        
        # Negative check
        has_negatives = any(v < 0 for v in numeric_data)
        
        # Outlier boundaries (using IQR method)
        sorted_data = sorted(numeric_data)
        n = len(sorted_data)
        q1 = sorted_data[n // 4] if n >= 4 else min_val
        q3 = sorted_data[3 * n // 4] if n >= 4 else max_val
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Range classification
        value_range = self._classify_range(min_val, max_val, subtype)
        
        return {
            # Statistical properties
            "mean": mean,
            "median": median,
            "std": std,
            "min": min_val,
            "max": max_val,
            "range": max_val - min_val,
            
            # Type properties
            "is_integer": is_integer,
            "decimal_places": max_decimals,
            "has_negatives": has_negatives,
            
            # Distribution
            "distribution": distribution,
            
            # Outlier boundaries
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            
            # Range classification
            "value_range": value_range,
            
            # Subtype specific
            "subtype": subtype,
        }
    
    def _detect_distribution(
        self, 
        data: List[float], 
        mean: float, 
        std: float
    ) -> str:
        """
        Detect the distribution type.
        
        Returns:
            'normal', 'uniform', 'skewed', 'bimodal', or 'unknown'
        """
        if len(data) < 10:
            return "unknown"
        
        if std == 0:
            return "constant"
        
        # Check skewness
        skewness = self._calculate_skewness(data, mean, std)
        
        if abs(skewness) < 0.5:
            return "normal"
        elif skewness > 1:
            return "right_skewed"
        elif skewness < -1:
            return "left_skewed"
        else:
            return "normal"
    
    def _calculate_skewness(
        self, 
        data: List[float], 
        mean: float, 
        std: float
    ) -> float:
        """Calculate skewness of the distribution"""
        if std == 0:
            return 0
        
        n = len(data)
        skew = sum((x - mean) ** 3 for x in data) / n
        skew = skew / (std ** 3)
        
        return skew
    
    def _classify_range(
        self, 
        min_val: float, 
        max_val: float, 
        subtype: str
    ) -> str:
        """Classify the value range for context"""
        if subtype == "percentage":
            if min_val >= 0 and max_val <= 1:
                return "decimal_percent"
            elif min_val >= 0 and max_val <= 100:
                return "whole_percent"
        
        if subtype == "age":
            if min_val >= 0 and max_val <= 120:
                return "valid_age"
        
        if subtype == "rating":
            if min_val >= 0 and max_val <= 5:
                return "five_star"
            elif min_val >= 0 and max_val <= 10:
                return "ten_scale"
        
        if min_val >= 0 and max_val <= 1:
            return "unit_interval"
        elif min_val >= 0 and max_val <= 100:
            return "percentage_like"
        elif abs(min_val) <= 180 and abs(max_val) <= 180:
            return "coordinate_like"
        
        return "general"
    
    def _generate_signature(self, data: List[Any]) -> Optional[str]:
        """Generate signature for numeric data"""
        if not data:
            return None
        
        # Convert to numeric
        numeric_data = []
        for v in data:
            try:
                numeric_data.append(float(v))
            except (ValueError, TypeError):
                continue
        
        if not numeric_data:
            return None
        
        # Create range-based signature (filter out NaN values)
        import math
        valid_numeric = [v for v in numeric_data if not math.isnan(v)]
        if not valid_numeric:
            return None
        min_val = min(valid_numeric)
        max_val = max(valid_numeric)
        is_int = all(v == int(v) for v in valid_numeric)
        
        type_str = "INT" if is_int else "FLOAT"
        range_str = f"[{min_val:.0f},{max_val:.0f}]"
        
        return f"{type_str}{range_str}"
    
    def get_correction_hints(
        self,
        fingerprint: FingerprintData,
        bad_value: Any
    ) -> Dict[str, Any]:
        """Get numeric-specific correction hints"""
        props = fingerprint.properties
        
        try:
            bad_num = float(bad_value)
        except (ValueError, TypeError):
            return {
                "issues": ["not_numeric"],
                "correctable": False,
            }
        
        hints = {
            "target_range": (props.get("min", 0), props.get("max", 100)),
            "target_mean": props.get("mean"),
            "is_integer": props.get("is_integer", False),
            "decimal_places": props.get("decimal_places", 0),
            "issues": [],
        }
        
        # Detect issues
        lower = props.get("lower_bound", props.get("min", float("-inf")))
        upper = props.get("upper_bound", props.get("max", float("inf")))
        
        if bad_num < lower:
            hints["issues"].append("below_range")
        if bad_num > upper:
            hints["issues"].append("above_range")
        
        # Integer mismatch
        if props.get("is_integer") and bad_num != int(bad_num):
            hints["issues"].append("should_be_integer")
        
        return hints
    
    def calculate_similarity(
        self,
        fingerprint: FingerprintData,
        value: Any
    ) -> float:
        """Calculate numeric similarity to fingerprint"""
        props = fingerprint.properties
        
        try:
            val_num = float(value)
        except (ValueError, TypeError):
            return 0.0
        
        # Check if within range
        min_val = props.get("min", float("-inf"))
        max_val = props.get("max", float("inf"))
        
        if min_val <= val_num <= max_val:
            # Calculate how close to mean
            mean = props.get("mean", val_num)
            std = props.get("std", 1)
            
            if std > 0:
                z_score = abs(val_num - mean) / std
                # Convert z-score to similarity (lower z = higher similarity)
                similarity = max(0, 1 - z_score / 3)
            else:
                similarity = 1.0 if val_num == mean else 0.0
            
            return similarity
        
        return 0.0
