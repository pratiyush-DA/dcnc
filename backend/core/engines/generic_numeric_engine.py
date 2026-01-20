"""
Generic Numeric Validation Engine
Fallback engine for unclassified numeric data
Uses statistical and fingerprint-based validation
"""

from typing import Any, Dict, List, Optional, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("generic_numeric")
class GenericNumericEngine(BaseEngine):
    """
    Generic numeric validation engine (FALLBACK).
    
    Used when no specific numeric subtype is detected.
    Uses statistical outlier detection and fingerprint validation.
    
    Capabilities:
    - Range-based validation
    - Statistical outlier detection (IQR method)
    - Type validation (integer vs float)
    - Fingerprint-driven bounds
    """
    
    def __init__(self):
        super().__init__()
        self._fingerprint: Optional[Dict[str, Any]] = None
        self._semantic_constraints: Optional[Dict[str, Any]] = None
    
    @property
    def name(self) -> str:
        return "generic_numeric"
    
    @property
    def description(self) -> str:
        return "Generic numeric validation using statistical analysis"
    
    @property
    def patterns(self) -> List[str]:
        return [
            r"^-?\d+\.?\d*$",  # Basic number pattern
        ]
    
    def set_fingerprint(self, fingerprint: Dict[str, Any]):
        """Set fingerprint for validation"""
        self._fingerprint = fingerprint
    
    def set_constraints(self, constraints: Dict[str, Any]):
        """
        Set semantic constraints.
        
        Args:
            constraints: Dict with 'min', 'max', 'type' keys
        """
        self._semantic_constraints = constraints
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate numeric value"""
        # Try to parse as number
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, 0.0
        
        confidence = 1.0
        
        # Check semantic constraints first (if set)
        if self._semantic_constraints:
            min_val = self._semantic_constraints.get("min", float("-inf"))
            max_val = self._semantic_constraints.get("max", float("inf"))
            
            if num_value < min_val or num_value > max_val:
                return False, 0.0
            
            expected_type = self._semantic_constraints.get("type")
            if expected_type == "integer" and num_value != int(num_value):
                confidence = 0.7  # Float when integer expected
        
        # Check against fingerprint if available
        if self._fingerprint:
            props = self._fingerprint.get("properties", {})
            
            # IQR-based outlier detection
            lower_bound = props.get("lower_bound", float("-inf"))
            upper_bound = props.get("upper_bound", float("inf"))
            
            if num_value < lower_bound or num_value > upper_bound:
                # Outlier detected
                return False, 0.3
            
            # Check strict range
            min_val = props.get("min", float("-inf"))
            max_val = props.get("max", float("inf"))
            
            if num_value < min_val or num_value > max_val:
                # Outside observed range but not outlier
                confidence = 0.6
            
            # Type mismatch
            if props.get("is_integer") and num_value != int(num_value):
                confidence = min(confidence, 0.7)
        
        return True, confidence
    
    def is_outlier(
        self,
        value: float,
        fingerprint: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Check if value is a statistical outlier.
        
        Args:
            value: Numeric value to check
            fingerprint: Optional fingerprint (uses stored if not provided)
            
        Returns:
            Tuple of (is_outlier, reason)
        """
        fp = fingerprint or self._fingerprint
        
        if not fp:
            return False, ""
        
        props = fp.get("properties", {})
        
        lower_bound = props.get("lower_bound", float("-inf"))
        upper_bound = props.get("upper_bound", float("inf"))
        
        if value < lower_bound:
            return True, f"below_lower_bound_{lower_bound:.2f}"
        
        if value > upper_bound:
            return True, f"above_upper_bound_{upper_bound:.2f}"
        
        # Check z-score if mean and std available
        mean = props.get("mean")
        std = props.get("std")
        
        if mean is not None and std and std > 0:
            z_score = abs(value - mean) / std
            if z_score > 3:
                return True, f"z_score_{z_score:.2f}"
        
        return False, ""
    
    def validate_with_fingerprint(
        self,
        value: Any,
        fingerprint: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Validate using a specific fingerprint"""
        old_fp = self._fingerprint
        self._fingerprint = fingerprint
        
        result = self.validate(value)
        
        self._fingerprint = old_fp
        return result
    
    def validate_with_constraints(
        self,
        value: Any,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        is_integer: bool = False
    ) -> Tuple[bool, float]:
        """
        Validate with explicit constraints.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            is_integer: Whether value should be integer
            
        Returns:
            Tuple of (is_valid, confidence)
        """
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, 0.0
        
        confidence = 1.0
        
        if min_val is not None and num_value < min_val:
            return False, 0.0
        
        if max_val is not None and num_value > max_val:
            return False, 0.0
        
        if is_integer and num_value != int(num_value):
            confidence = 0.7
        
        return True, confidence
