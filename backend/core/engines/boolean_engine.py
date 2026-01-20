"""
Boolean Validation Engine
Validates boolean/boolean-like values (True/False/Yes/No/1/0)
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("boolean")
class BooleanEngine(BaseEngine):
    """
    Boolean validation engine.
    
    Validates:
    - True/False (case insensitive)
    - Yes/No
    - Y/N
    - 1/0
    - T/F
    """
    
    # All valid boolean representations
    TRUTHY_VALUES = {"true", "yes", "y", "1", "t", "on", "active", "enabled"}
    FALSY_VALUES = {"false", "no", "n", "0", "f", "off", "inactive", "disabled"}
    ALL_VALID = TRUTHY_VALUES | FALSY_VALUES
    
    @property
    def name(self) -> str:
        return "boolean"
    
    @property
    def description(self) -> str:
        return "Validates boolean values (True/False/Yes/No/1/0)"
    
    @property
    def patterns(self) -> List[str]:
        return [
            r"^(true|false|yes|no|1|0|y|n|t|f|on|off)$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate normalized boolean value"""
        lower = value.lower().strip()
        
        if lower in self.ALL_VALID:
            return True, 1.0
        
        # Check for common misspellings
        if lower in {"tru", "ture", "flase", "fasle"}:
            return True, 0.5  # Correctable
        
        return False, 0.0
    
    def to_boolean(self, value: str) -> bool:
        """Convert value to Python boolean"""
        return value.lower().strip() in self.TRUTHY_VALUES
    
    def normalize_to_standard(self, value: str, format_style: str = "TrueFalse") -> str:
        """
        Normalize boolean to standard format.
        
        Args:
            value: Boolean value
            format_style: 'TrueFalse', 'YesNo', '10'
            
        Returns:
            Normalized boolean string
        """
        is_truthy = value.lower().strip() in self.TRUTHY_VALUES
        
        if format_style == "TrueFalse":
            return "True" if is_truthy else "False"
        elif format_style == "YesNo":
            return "Yes" if is_truthy else "No"
        elif format_style == "10":
            return "1" if is_truthy else "0"
        else:
            return "True" if is_truthy else "False"
