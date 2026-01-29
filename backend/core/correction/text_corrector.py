"""
Text Corrector (Enhanced)
Correction engine for string/text data types with comprehensive fixes
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from .base_corrector import BaseCorrector
from ..interfaces import CorrectionResult, CorrectionStatus
from ..registry import register_corrector

logger = logging.getLogger(__name__)


# Abbreviations to preserve uppercase (Bug Fix #6)
PRESERVE_UPPERCASE = {
    "IT", "HR", "PR", "QA", "CEO", "CFO", "CTO", "COO", "VP",
    "USA", "UK", "EU", "UN", "NATO", "NASA", "FBI", "CIA",
    "PhD", "MD", "MBA", "BS", "MS", "BA", "MA",
}


@register_corrector("text")
@register_corrector("generic_string")
@register_corrector("name")
@register_corrector("company")
class TextCorrector(BaseCorrector):
    """
    Correction engine for text/string data.
    
    Corrections supported:
    - Case normalization (title, upper, lower)
    - Whitespace cleanup
    - Length trimming
    - Pattern alignment
    
    Special handling for abbreviations (Bug Fix #6).
    """
    
    @property
    def name(self) -> str:
        return "text_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects text data using fingerprint patterns"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return [
            "name", "company", "address", "location", "state", "country",
            "username", "file_path", "product_title", "job_title", "generic",
        ]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct text value"""
        str_val = str(value).strip()
        changes = []
        corrected = str_val
        
        # Whitespace cleanup
        if "  " in corrected or corrected != corrected.strip():
            corrected = " ".join(corrected.split())
            changes.append("whitespace_cleaned")
        
        # Case correction based on fingerprint or subtype
        target_case = None
        if learned_patterns:
            target_case = learned_patterns.get("case_style")
        
        # Default case styles for subtypes
        if not target_case:
            if subtype == "name":
                target_case = "title"
            elif subtype == "company":
                target_case = "title"
        
        if target_case:
            if target_case == "title" and not corrected.istitle():
                corrected = self._title_case_preserve(corrected)
                if corrected != str_val:
                    changes.append("title_cased")
            elif target_case == "upper" and not corrected.isupper():
                corrected = corrected.upper()
                changes.append("uppercased")
            elif target_case == "lower" and not corrected.islower():
                corrected = corrected.lower()
                changes.append("lowercased")
        
        if changes:
            return self._make_corrected_result(value, corrected, changes)
        
        return self._make_unchanged_result(value)
    
    def _title_case_preserve(self, text: str) -> str:
        """
        Apply title case while preserving known uppercase abbreviations.
        Bug Fix #6: IT, HR, PR remain uppercase.
        """
        words = text.split()
        result = []
        
        for word in words:
            clean = re.sub(r'[^A-Za-z0-9]', '', word)
            
            # Check if it's a known abbreviation
            if clean.upper() in PRESERVE_UPPERCASE:
                if clean.isupper():
                    result.append(word)
                else:
                    result.append(word.upper())
            else:
                result.append(word.title())
        
        return " ".join(result)


@register_corrector("email")
class EmailCorrector(BaseCorrector):
    """Enhanced email corrector with comprehensive typo fixes"""
    
    # Common domain typo fixes (expanded)
    DOMAIN_FIXES = {
        # Gmail typos
        "gmial.com": "gmail.com",
        "gmal.com": "gmail.com",
        "gmail.co": "gmail.com",
        "gmai.com": "gmail.com",
        "gmailcom": "gmail.com",  # Missing dot!
        "gmaill.com": "gmail.com",
        "gamil.com": "gmail.com",
        # Yahoo typos
        "yahooo.com": "yahoo.com",
        "yaho.com": "yahoo.com",
        "yahoocom": "yahoo.com",
        # Hotmail typos
        "hotmai.com": "hotmail.com",
        "hotmal.com": "hotmail.com",
        "hotmailcom": "hotmail.com",
        # Outlook typos
        "outloo.com": "outlook.com",
        "outlookcom": "outlook.com",
    }
    
    @property
    def name(self) -> str:
        return "email_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects email addresses (domain typos, case)"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["email"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct email value with comprehensive typo fixes"""
        original = str(value).strip()
        email = original
        changes = []
        
        # Must have @ symbol to be correctable
        if "@" not in email:
            return self._make_rejected_result(value, "missing_at_symbol")
        
        # Fix common typos BEFORE splitting
        # Fix double @@ → single @
        if "@@" in email:
            email = email.replace("@@", "@")
            changes.append("double_at_fixed")
        
        # Fix double dots in local part or domain
        if ".." in email:
            email = email.replace("..", ".")
            changes.append("double_dot_fixed")
        
        # Normalize to lowercase for processing
        email_lower = email.lower()
        
        # Split into local and domain parts
        try:
            local_part, domain = email_lower.rsplit("@", 1)
        except ValueError:
            # Invalid email format (multiple @ or incomplete)
            return self._make_rejected_result(value, "invalid_email_format")
        
        # Validate domain completeness
        if not domain or domain == "":
            return self._make_rejected_result(value, "incomplete_domain")
        
        # Check if domain ends with @ (incomplete)
        if domain.endswith("@"):
            return self._make_rejected_result(value, "incomplete_domain")
        
        # Fix domain typos
        if domain in self.DOMAIN_FIXES:
            domain = self.DOMAIN_FIXES[domain]
            changes.append("domain_typo_fixed")
        
        # Try to fix missing dot in common domains
        if "." not in domain:
            fixed_domain = self._try_fix_missing_dot(domain)
            if fixed_domain != domain:
                domain = fixed_domain
                changes.append("domain_dot_added")
        
        # Reconstruct email (preserve original case for local part if needed)
        if original != original.lower():
            # Preserve case of local part if original had mixed case
            local_part_original = original.rsplit("@", 1)[0]
            email = f"{local_part_original}@{domain}"
        else:
            email = f"{local_part}@{domain}"
        
        # Validate final email format
        if not self._is_valid_email_format(email):
            return self._make_rejected_result(value, "invalid_email_format")
        
        if changes:
            return self._make_corrected_result(value, email, changes, confidence=1.0)
        
        return self._make_unchanged_result(value)
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _try_fix_missing_dot(self, domain: str) -> str:
        """Try to add missing dot to common domains"""
        known_patterns = [
            ("gmailcom", "gmail.com"),
            ("yahoocom", "yahoo.com"),
            ("hotmailcom", "hotmail.com"),
            ("outlookcom", "outlook.com"),
        ]
        
        for pattern, fixed in known_patterns:
            if domain == pattern:
                return fixed
        
        return domain


@register_corrector("phone")
class PhoneCorrector(BaseCorrector):
    """Enhanced phone corrector with majority format standardization"""
    
    @property
    def name(self) -> str:
        return "phone_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects phone number formatting to majority format from good data"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["phone"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct phone value to majority format from good data"""
        str_val = str(value).strip()
        
        # Extract digits
        digits = "".join(c for c in str_val if c.isdigit())
        
        # Too few or too many digits - reject
        if len(digits) < 7 or len(digits) > 15:
            return self._make_rejected_result(value, "invalid_digit_count")
        
        # Get target format from fingerprint (majority format from largest good cluster)
        target_format = None
        if learned_patterns:
            target_format = learned_patterns.get("expected_format")
        if not target_format and fingerprint:
            correction_hints = fingerprint.get("correction_hints", {})
            target_format = correction_hints.get("expected_format")
            if not target_format:
                # Check format_distribution for majority
                format_dist = correction_hints.get("format_distribution", {})
                if format_dist:
                    target_format = max(format_dist, key=format_dist.get)
        
        changes = []
        formatted = str_val
        
        # Format based on digit count and target format preference
        if len(digits) == 10:
            # US 10-digit format
            if target_format == "XXX-XXX-XXXX" or not target_format:
                formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            elif target_format == "(XXX) XXX-XXXX":
                formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif target_format == "XXX.XXX.XXXX":
                formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
            else:
                # Default to XXX-XXX-XXXX
                formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            
            if formatted != str_val:
                changes.append("formatted_standard")
        
        elif len(digits) == 11 and digits.startswith("1"):
            # US with country code - remove leading 1
            if target_format == "XXX-XXX-XXXX" or not target_format:
                formatted = f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
            elif target_format == "(XXX) XXX-XXXX":
                formatted = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
            else:
                formatted = f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
            
            if formatted != str_val:
                changes.append("formatted_standard")
        
        elif len(digits) == 7:
            # Local 7-digit format
            formatted = f"{digits[:3]}-{digits[3:]}"
            if formatted != str_val:
                changes.append("formatted_local")
        
        else:
            # International format - keep as is or minimal formatting
            if len(digits) >= 10:
                # Try to format as XXX-XXX-XXXX if possible
                formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                if formatted != str_val:
                    changes.append("formatted_international")
            else:
                # Too short or unusual - reject
                return self._make_rejected_result(value, "invalid_phone_format")
        
        if changes:
            return self._make_corrected_result(value, formatted, changes, confidence=1.0)
        
        return self._make_unchanged_result(value)


@register_corrector("url")
class URLCorrector(BaseCorrector):
    """Enhanced URL corrector with comprehensive fixes"""
    
    # Common URL typos and fixes
    URL_FIXES = {
        "http:/": "http://",
        "https:/": "https://",
        "www.": "https://www.",
    }
    
    @property
    def name(self) -> str:
        return "url_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects URLs (adds protocol, fixes typos, standardizes format)"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["url"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct URL value with comprehensive fixes"""
        url = str(value).strip()
        original = url
        changes = []
        
        # Fix common URL typos
        for typo, fix in self.URL_FIXES.items():
            if url.startswith(typo) and not url.startswith(fix):
                url = url.replace(typo, fix, 1)
                changes.append("url_typo_fixed")
        
        # Check if it looks like a URL (has a dot and valid domain pattern)
        if "." in url:
            # Check if protocol is missing
            if not url.startswith(("http://", "https://", "ftp://", "ftps://")):
                # Determine protocol from fingerprint or use https
                preferred_protocol = learned_patterns.get("preferred_protocol")
                if not preferred_protocol and fingerprint:
                    correction_hints = fingerprint.get("correction_hints", {})
                    preferred_protocol = correction_hints.get("preferred_protocol", "https")
                if not preferred_protocol:
                    preferred_protocol = "https"  # Default to https
                
                url = f"{preferred_protocol}://{url}"
                changes.append("protocol_added")
            
            # Validate URL format
            if self._is_valid_url_format(url):
                if changes:
                    return self._make_corrected_result(value, url, changes, confidence=1.0)
                return self._make_unchanged_result(value)
            else:
                # Invalid URL format - reject
                return self._make_rejected_result(value, "invalid_url_format")
        
        # Doesn't look like a URL - reject
        return self._make_rejected_result(value, "not_url_like")
    
    def _is_valid_url_format(self, url: str) -> bool:
        """Basic URL format validation"""
        import re
        # Basic URL pattern: protocol://domain.extension
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url, re.IGNORECASE))


@register_corrector("boolean")
class BooleanCorrector(BaseCorrector):
    """Enhanced boolean corrector with comprehensive normalization"""
    
    # Expanded truthy values (case-insensitive)
    TRUTHY = {
        "true", "t", "yes", "y", "1", "on", "enabled", "enable",
        "True", "TRUE", "Yes", "YES", "Y", "T", "ON", "On"
    }
    
    # Expanded falsy values (case-insensitive)
    FALSY = {
        "false", "f", "no", "n", "0", "off", "disabled", "disable",
        "False", "FALSE", "No", "NO", "N", "F", "OFF", "Off"
    }
    
    # Ambiguous/null values (can be normalized to null or configurable default)
    AMBIGUOUS = {
        "maybe", "perhaps", "unknown", "null", "none", "na", "n/a",
        "Maybe", "MAYBE", "Unknown", "UNKNOWN", "Null", "NULL", "None", "NONE"
    }
    
    @property
    def name(self) -> str:
        return "boolean_corrector"
    
    @property
    def description(self) -> str:
        return "Standardizes boolean values to True/False/null with normalization"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["boolean"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Standardize boolean to True/False/null with comprehensive normalization"""
        str_val = str(value).strip()
        str_val_lower = str_val.lower()
        
        # Check truthy values
        if str_val_lower in [v.lower() for v in self.TRUTHY] or str_val in self.TRUTHY:
            if str_val not in ("True", "true"):
                return self._make_corrected_result(
                    value, "True", ["normalized_to_true"], confidence=1.0
                )
            return self._make_unchanged_result(value)
        
        # Check falsy values
        if str_val_lower in [v.lower() for v in self.FALSY] or str_val in self.FALSY:
            if str_val not in ("False", "false"):
                return self._make_corrected_result(
                    value, "False", ["normalized_to_false"], confidence=1.0
                )
            return self._make_unchanged_result(value)
        
        # Handle ambiguous values (maybe, unknown, etc.)
        if str_val_lower in [v.lower() for v in self.AMBIGUOUS] or str_val in self.AMBIGUOUS:
            # Get default handling from fingerprint or use null
            default_value = learned_patterns.get("ambiguous_default", "null")
            if fingerprint:
                default_value = fingerprint.get("ambiguous_default", default_value)
            
            if default_value == "null":
                return self._make_corrected_result(
                    value, "null", ["normalized_ambiguous_to_null"], confidence=0.8
                )
            elif default_value == "false":
                return self._make_corrected_result(
                    value, "False", ["normalized_ambiguous_to_false"], confidence=0.7
                )
            else:  # default to false for safety
                return self._make_corrected_result(
                    value, "False", ["normalized_ambiguous_to_false"], confidence=0.7
                )
        
        # Not a recognizable boolean value - reject
        return self._make_rejected_result(value, "not_boolean_like")
