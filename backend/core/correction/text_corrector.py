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
        """Correct email value"""
        original = str(value).strip()
        email = original.lower()
        changes = []
        
        # Must have @ symbol to be correctable
        if "@" not in email:
            return self._make_rejected_result(value, "missing_at_symbol")
        
        local_part, domain = email.rsplit("@", 1)
        
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
        
        email = f"{local_part}@{domain}"
        
        if changes:
            return self._make_corrected_result(value, email, changes)
        
        return self._make_unchanged_result(value)
    
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
    """Enhanced phone corrector with formatting"""
    
    @property
    def name(self) -> str:
        return "phone_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects phone number formatting"
    
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
        """Correct phone value"""
        str_val = str(value).strip()
        
        # Extract digits
        digits = "".join(c for c in str_val if c.isdigit())
        
        # Too few or too many digits - reject
        if len(digits) < 7 or len(digits) > 15:
            return self._make_rejected_result(value, "invalid_digit_count")
        
        # Format to standard
        changes = []
        
        if len(digits) == 10:
            formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            if formatted != str_val:
                changes.append("formatted_standard")
            return self._make_corrected_result(value, formatted, changes)
        
        if len(digits) == 11 and digits.startswith("1"):
            formatted = f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
            if formatted != str_val:
                changes.append("formatted_standard")
            return self._make_corrected_result(value, formatted, changes)
        
        # 7 digits - local number, just format
        if len(digits) == 7:
            formatted = f"{digits[:3]}-{digits[3:]}"
            if formatted != str_val:
                changes.append("formatted_local")
            return self._make_corrected_result(value, formatted, changes)
        
        return self._make_unchanged_result(value)


@register_corrector("url")
class URLCorrector(BaseCorrector):
    """URL corrector - adds protocol if missing"""
    
    @property
    def name(self) -> str:
        return "url_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects URLs (adds protocol if missing)"
    
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
        """Correct URL value"""
        url = str(value).strip()
        changes = []
        
        # Check if it looks like a URL (has a dot)
        if "." in url and not url.startswith(("http://", "https://")):
            # Add https:// protocol
            url = f"https://{url}"
            changes.append("protocol_added")
            return self._make_corrected_result(value, url, changes)
        
        return self._make_unchanged_result(value)


@register_corrector("boolean")
class BooleanCorrector(BaseCorrector):
    """Corrects boolean values to standard format"""
    
    TRUTHY = {"true", "yes", "y", "1", "t", "on"}
    FALSY = {"false", "no", "n", "0", "f", "off"}
    
    @property
    def name(self) -> str:
        return "boolean_corrector"
    
    @property
    def description(self) -> str:
        return "Standardizes boolean values to True/False"
    
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
        """Standardize boolean to True/False"""
        str_val = str(value).strip().lower()
        
        if str_val in self.TRUTHY:
            if str(value) != "True":
                return self._make_corrected_result(value, "True", ["standardized_true"])
        elif str_val in self.FALSY:
            if str(value) != "False":
                return self._make_corrected_result(value, "False", ["standardized_false"])
        else:
            return self._make_rejected_result(value, "not_boolean")
        
        return self._make_unchanged_result(value)
