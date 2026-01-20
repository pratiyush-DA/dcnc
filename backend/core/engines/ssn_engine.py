"""
SSN (Social Security Number) Validation Engine
Validates US SSN format with reserved pattern rejection
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("ssn")
class SSNEngine(BaseEngine):
    """
    SSN validation engine.
    
    Validates:
    - Format: XXX-XX-XXXX or XXXXXXXXX
    - Rejects reserved patterns (000, 666, 900-999 area numbers)
    - Rejects all-zero groups
    """
    
    # Invalid area numbers (first 3 digits)
    INVALID_AREA_PATTERNS = {"000", "666"} | {str(i) for i in range(900, 1000)}
    
    @property
    def name(self) -> str:
        return "ssn"
    
    @property
    def description(self) -> str:
        return "Validates US Social Security Numbers"
    
    @property
    def patterns(self) -> List[str]:
        return [
            r"^\d{3}-\d{2}-\d{4}$",  # Formatted: XXX-XX-XXXX
            r"^\d{9}$",              # Unformatted: XXXXXXXXX
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate normalized SSN value"""
        # Remove dashes for consistent checking
        clean = value.replace("-", "")
        
        # Must be exactly 9 digits
        if len(clean) != 9 or not clean.isdigit():
            return False, 0.0
        
        # Extract components
        area = clean[:3]
        group = clean[3:5]
        serial = clean[5:]
        
        # Rule 1: Area number (first 3 digits) cannot be 000, 666, or 900-999
        if area in self.INVALID_AREA_PATTERNS:
            return False, 0.0
        
        # Rule 2: Group number (middle 2 digits) cannot be 00
        if group == "00":
            return False, 0.0
        
        # Rule 3: Serial number (last 4 digits) cannot be 0000
        if serial == "0000":
            return False, 0.0
        
        # Check format for confidence
        if "-" in value:
            # Properly formatted
            if re.match(r"^\d{3}-\d{2}-\d{4}$", value):
                return True, 1.0
            return False, 0.0
        else:
            # Unformatted - valid but needs formatting
            return True, 0.8
    
    def format_ssn(self, value: str) -> str:
        """Format SSN with dashes."""
        clean = value.replace("-", "")
        if len(clean) == 9 and clean.isdigit():
            return f"{clean[:3]}-{clean[3:5]}-{clean[5:]}"
        return value
