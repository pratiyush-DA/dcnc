"""
IP Address Validation Engine
STRICT IP address validation with octet range checking
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("ip_address")
class IPAddressEngine(BaseEngine):
    """
    Strict IP address validation.
    
    Validates:
    - IPv4 format (x.x.x.x)
    - Each octet 0-255
    - IPv6 format (optional)
    
    Rejects:
    - Invalid octets (256+)
    - "localhost", hostnames
    - Malformed addresses
    """
    
    @property
    def name(self) -> str:
        return "ip_address"
    
    @property
    def description(self) -> str:
        return "Validates IP addresses with strict octet checking"
    
    @property
    def patterns(self) -> List[str]:
        return [
            # IPv4 - basic pattern (strict validation in _validate_normalized)
            r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$",
            # IPv6 (simplified)
            r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$",
        ]
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate IP with octet range checking"""
        # Check for IPv4
        ipv4_match = re.match(
            r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$",
            value
        )
        
        if ipv4_match:
            octets = [int(g) for g in ipv4_match.groups()]
            
            # Each octet must be 0-255
            for octet in octets:
                if octet < 0 or octet > 255:
                    return False, 0.0
            
            # Check for private IP (valid but note it)
            if self._is_private_ip(octets):
                return True, 0.9
            
            return True, 1.0
        
        # IPv6 matched pattern - valid
        return True, 1.0
    
    def _is_private_ip(self, octets: List[int]) -> bool:
        """Check if IP is private"""
        # 10.x.x.x
        if octets[0] == 10:
            return True
        # 172.16.x.x - 172.31.x.x
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            return True
        # 192.168.x.x
        if octets[0] == 192 and octets[1] == 168:
            return True
        # Loopback 127.x.x.x
        if octets[0] == 127:
            return True
        return False
    
    def validate(self, value: str) -> Tuple[bool, float]:
        """Override to reject hostnames"""
        if value is None:
            return False, 0.0
        
        str_val = str(value).strip().lower()
        
        # Reject hostnames
        if str_val in ("localhost", "host", "server"):
            return False, 0.0
        
        # Reject if contains letters (not IPv6)
        if re.search(r"[a-z]", str_val) and ":" not in str_val:
            return False, 0.0
        
        return super().validate(value)
