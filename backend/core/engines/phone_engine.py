"""
Phone Number Validation Engine
Flexible phone number validation
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("phone")
class PhoneEngine(BaseEngine):
    """
    Flexible phone number validation engine.
    
    Validates based on:
    - Digit count (7-15 digits)
    - Reasonable separators
    
    Does NOT require specific format - accepts any phone-like string.
    """
    
    ALLOWED_SEPARATORS = set("-. ()+")
    
    @property
    def name(self) -> str:
        return "phone"
    
    @property
    def description(self) -> str:
        return "Validates phone numbers (7-15 digits)"
    
    @property
    def patterns(self) -> List[str]:
        # Flexible pattern - any mix of digits and separators
        return [
            r"^[\d\s\-\.\(\)\+]+$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate phone by digit count and allowed characters"""
        # Extract digits
        digits = "".join(c for c in value if c.isdigit())
        
        # Check digit count
        if len(digits) < 7 or len(digits) > 15:
            return False, 0.0
        
        # Check for invalid/reserved numbers
        if self._is_invalid_number(digits):
            return False, 0.0
        
        # Check for invalid characters
        for char in value:
            if not char.isdigit() and char not in self.ALLOWED_SEPARATORS:
                return False, 0.0
        
        # Confidence based on digit count
        if len(digits) == 10:
            return True, 1.0  # Standard US format
        elif len(digits) == 11 and digits.startswith("1"):
            return True, 1.0  # US with country code
        elif 7 <= len(digits) < 10:
            return True, 0.8  # Local format
        else:
            return True, 0.7  # International
    
    def _is_invalid_number(self, digits: str) -> bool:
        """
        Check if phone number is an invalid/placeholder pattern.
        
        Invalid patterns:
        - All same digit (0000000000, 1111111111)
        - Sequential (1234567890)
        - Too repetitive
        """
        # Reserved invalid numbers
        INVALID_NUMBERS = {
            "0000000000", "1111111111", "2222222222", "3333333333",
            "4444444444", "5555555555", "6666666666", "7777777777",
            "8888888888", "9999999999", "1234567890", "0987654321",
        }
        
        if digits in INVALID_NUMBERS:
            return True
        
        # All same digit (any length)
        if len(set(digits)) == 1:
            return True
        
        # Too many repeated digits (e.g., 000000xxxx)
        if len(digits) >= 7:
            for d in "0123456789":
                if digits.count(d) >= len(digits) * 0.8:  # 80%+ same digit
                    return True
        
        return False
    
    def extract_digits(self, phone: str) -> str:
        """Extract just the digits from a phone number"""
        return "".join(c for c in phone if c.isdigit())
