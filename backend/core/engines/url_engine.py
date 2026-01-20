"""
URL Validation Engine
Validates URL format and structure
"""

import re
from typing import List, Tuple
from urllib.parse import urlparse

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("url")
class URLEngine(BaseEngine):
    """
    URL validation engine.
    
    Validates:
    - Protocol (http, https, ftp)
    - Domain structure
    - Valid characters
    """
    
    VALID_PROTOCOLS = {"http", "https", "ftp", "ftps"}
    
    @property
    def name(self) -> str:
        return "url"
    
    @property
    def description(self) -> str:
        return "Validates URL format with protocol and domain"
    
    @property
    def patterns(self) -> List[str]:
        return [
            r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate normalized URL value"""
        # Preprocess: Add https:// if value starts with www.
        if value.lower().startswith("www."):
            value = f"https://{value}"
        
        # Try to parse URL
        try:
            parsed = urlparse(value)
        except Exception:
            return False, 0.0
        
        # Check for scheme
        if not parsed.scheme:
            # No protocol - might still be valid URL-like string
            if "." in value and " " not in value and len(value) > 4:
                return True, 0.6  # Likely a URL, needs protocol
            return False, 0.0
        
        # Validate scheme
        if parsed.scheme.lower() not in self.VALID_PROTOCOLS:
            return False, 0.0
        
        # Check for netloc (domain)
        if not parsed.netloc:
            return False, 0.0
        
        # Domain should have at least one dot
        if "." not in parsed.netloc:
            return False, 0.0
        
        # Check for valid domain characters
        domain = parsed.netloc.split(":")[0]  # Remove port if present
        if not re.match(r"^[a-zA-Z0-9.-]+$", domain):
            return False, 0.0
        
        confidence = 1.0
        
        # HTTPS is preferred
        if parsed.scheme.lower() == "https":
            confidence = 1.0
        elif parsed.scheme.lower() == "http":
            confidence = 0.95
        else:
            confidence = 0.9
        
        return True, confidence
    
    def add_protocol(self, url: str, protocol: str = "https") -> str:
        """
        Add protocol to URL if missing.
        
        Args:
            url: URL string
            protocol: Protocol to add (default: https)
            
        Returns:
            URL with protocol
        """
        url = url.strip()
        
        if not url:
            return url
        
        # Already has protocol
        if re.match(r"^[a-zA-Z]+://", url):
            return url
        
        return f"{protocol}://{url}"
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            if parsed.netloc:
                return parsed.netloc.split(":")[0]
            # Try with protocol added
            parsed = urlparse(f"http://{url}")
            return parsed.netloc.split(":")[0]
        except Exception:
            return ""
