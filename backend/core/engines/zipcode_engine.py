"""
ZIP Code Validation Engine
Validates US ZIP code formats
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("zipcode")
class ZipCodeEngine(BaseEngine):
    """
    ZIP code validation engine.
    
    Validates:
    - 5-digit format (12345)
    - 9-digit format with hyphen (12345-6789)
    - 9-digit format without hyphen (123456789)
    """
    
    @property
    def name(self) -> str:
        return "zipcode"
    
    @property
    def description(self) -> str:
        return "Validates US ZIP code format (5 or 9 digits)"
    
    @property
    def patterns(self) -> List[str]:
        return [
            r"^\d{5}$",              # 12345
            r"^\d{5}-\d{4}$",        # 12345-6789
            r"^\d{9}$",              # 123456789
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate normalized ZIP code value"""
        # Remove any spaces
        value = value.replace(" ", "")
        
        # Check 5-digit format
        if re.match(r"^\d{5}$", value):
            return True, 1.0
        
        # Check 9-digit with hyphen
        if re.match(r"^\d{5}-\d{4}$", value):
            return True, 1.0
        
        # Check 9-digit without hyphen
        if re.match(r"^\d{9}$", value):
            return True, 0.9  # Slightly lower confidence, might need formatting
        
        return False, 0.0

    def normalize(self, value: str) -> str:
        """Normalize ZIP code value (handle floats)"""
        value = value.strip()
        if value.endswith(".0"):
            value = value[:-2]
        return value
    
    def format_zip(self, zipcode: str, include_plus4: bool = True) -> str:
        """
        Format ZIP code to standard format.
        
        Args:
            zipcode: ZIP code string
            include_plus4: Whether to include +4 if present
            
        Returns:
            Formatted ZIP code
        """
        # Extract digits only
        digits = "".join(c for c in zipcode if c.isdigit())
        
        if len(digits) == 5:
            return digits
        elif len(digits) == 9:
            if include_plus4:
                return f"{digits[:5]}-{digits[5:]}"
            return digits[:5]
        
        return zipcode  # Return original if can't format
    
    def get_zip5(self, zipcode: str) -> str:
        """Extract 5-digit ZIP from any format"""
        digits = "".join(c for c in zipcode if c.isdigit())
        
        if len(digits) >= 5:
            return digits[:5]
        
        return zipcode
