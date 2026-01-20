"""
Email Validation Engine
STRICT email validation with typo detection
"""

import re
from typing import List, Optional, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("email")
class EmailEngine(BaseEngine):
    """
    Strict email validation engine.
    
    Validates:
    - Proper format (local@domain.tld)
    - Valid domain structure
    - At least 2-char TLD
    
    Also detects common typos for correction.
    """
    
    # Common domain typos
    DOMAIN_TYPOS = {
        "gmial.com": "gmail.com",
        "gmal.com": "gmail.com",
        "gmail.co": "gmail.com",
        "gmai.com": "gmail.com",
        "gmailcom": "gmail.com",
        "yahooo.com": "yahoo.com",
        "yaho.com": "yahoo.com",
        "hotmai.com": "hotmail.com",
        "hotmal.com": "hotmail.com",
        "hotmailcom": "hotmail.com",
        "outloo.com": "outlook.com",
    }
    
    @property
    def name(self) -> str:
        return "email"
    
    @property
    def description(self) -> str:
        return "Validates email addresses with strict format checking"
    
    @property
    def patterns(self) -> List[str]:
        return [
            # Standard email pattern - STRICT
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate email with additional checks"""
        # Must have exactly one @
        if value.count("@") != 1:
            return False, 0.0
        
        local, domain = value.rsplit("@", 1)
        
        # Local part checks
        if len(local) < 1 or len(local) > 64:
            return False, 0.0
        
        # Domain checks
        if len(domain) < 4:  # Minimum: a.bc
            return False, 0.0
        
        # Must have at least one dot in domain
        if "." not in domain:
            return False, 0.0
        
        # TLD must be at least 2 chars
        tld = domain.rsplit(".", 1)[-1]
        if len(tld) < 2:
            return False, 0.0
        
        # Check for common typos (lower confidence)
        if domain.lower() in self.DOMAIN_TYPOS:
            return True, 0.7  # Valid but has typo
        
        return True, 1.0
    
    def normalize(self, value: str) -> str:
        """Normalize email to lowercase"""
        return value.strip().lower()
    
    def get_correction_suggestion(self, value: str) -> Optional[str]:
        """Suggest correction for domain typos"""
        if "@" not in value:
            return None
        
        local, domain = value.rsplit("@", 1)
        domain_lower = domain.lower()
        
        if domain_lower in self.DOMAIN_TYPOS:
            return f"{local}@{self.DOMAIN_TYPOS[domain_lower]}"
        
        return None


@register_validator("uuid")
class UUIDEngine(BaseEngine):
    """Strict UUID validation"""
    
    @property
    def name(self) -> str:
        return "uuid"
    
    @property
    def description(self) -> str:
        return "Validates UUIDs (with or without dashes)"
    
    @property
    def patterns(self) -> List[str]:
        return [
            # Standard UUID with dashes
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            # UUID without dashes
            r"^[0-9a-fA-F]{32}$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """UUID is valid if pattern matched"""
        return True, 1.0
