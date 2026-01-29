"""
Generic Corrector
Fallback corrector for any data type using fingerprint patterns
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .base_corrector import BaseCorrector
from ..interfaces import CorrectionResult, CorrectionStatus
from ..registry import register_corrector

logger = logging.getLogger(__name__)


@register_corrector("generic")
@register_corrector("identifier")
@register_corrector("pattern_id")
@register_corrector("numeric_id")
class GenericCorrector(BaseCorrector):
    """
    Generic fallback corrector.
    
    Uses fingerprint patterns to attempt correction:
    - Length adjustment
    - Pattern alignment
    - Common value substitution
    
    This corrector is used when no specific corrector
    is available for a subtype.
    """
    
    @property
    def name(self) -> str:
        return "generic_corrector"
    
    @property
    def description(self) -> str:
        return "Generic correction using fingerprint similarity"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["generic", "identifier", "pattern_id", "numeric_id"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Attempt generic correction with pattern validation"""
        str_val = str(value).strip()
        
        if not fingerprint and not learned_patterns:
            # No fingerprint to learn from
            return self._make_unchanged_result(value)
        
        changes = []
        corrected = str_val
        
        # Get properties from fingerprint
        props = learned_patterns or fingerprint.get("properties", {})
        
        # Pattern-based correction and validation for identifiers
        if subtype in ("identifier", "pattern_id"):
            pattern_sig = props.get("pattern_signature")
            if pattern_sig:
                # Validate current value against expected pattern
                current_pattern = self._value_to_pattern(str_val)
                
                if current_pattern != pattern_sig:
                    # Try to align to pattern
                    aligned = self._align_to_pattern(str_val, pattern_sig, props)
                    
                    # Validate aligned value matches pattern
                    aligned_pattern = self._value_to_pattern(aligned)
                    
                    if aligned_pattern == pattern_sig:
                        # Successfully aligned
                        corrected = aligned
                        changes.append("pattern_aligned")
                    else:
                        # Cannot align to pattern - reject
                        return self._make_rejected_result(
                            value, 
                            f"pattern_mismatch: expected {pattern_sig}, got {current_pattern}"
                        )
                else:
                    # Pattern matches - check other properties
                    # Case correction if needed
                    target_case = props.get("case_style")
                    if target_case == "upper" and not corrected.isupper():
                        corrected = corrected.upper()
                        changes.append("uppercased")
                    elif target_case == "lower" and not corrected.islower():
                        corrected = corrected.lower()
                        changes.append("lowercased")
            else:
                # No pattern signature - reject invalid pattern IDs
                if subtype == "pattern_id":
                    return self._make_rejected_result(value, "no_pattern_signature")
        
        # Case correction for non-pattern identifiers
        if subtype not in ("identifier", "pattern_id"):
            target_case = props.get("case_style")
            if target_case == "upper" and not corrected.isupper():
                corrected = corrected.upper()
                changes.append("uppercased")
            elif target_case == "lower" and not corrected.islower():
                corrected = corrected.lower()
                changes.append("lowercased")
        
        # Padding for numeric IDs
        padding = props.get("numeric_padding")
        if padding and subtype == "numeric_id":
            digits = "".join(c for c in corrected if c.isdigit())
            if len(digits) < padding:
                corrected = digits.zfill(padding)
                changes.append("zero_padded")
        
        if changes:
            return self._make_corrected_result(value, corrected, changes, confidence=1.0)
        
        return self._make_unchanged_result(value)
    
    def _value_to_pattern(self, value: str) -> str:
        """
        Convert value to pattern signature (e.g., "ABC-123" -> "A-9").
        Used for pattern validation.
        """
        import re
        pattern = []
        
        for char in value:
            if char.isalpha():
                pattern.append("A")
            elif char.isdigit():
                pattern.append("9")
            else:
                # Keep separator as is
                pattern.append(char)
        
        # Collapse consecutive same types
        result = []
        prev = None
        for p in pattern:
            if p in ("A", "9"):
                if prev != p:
                    result.append(p)
                    prev = p
            else:
                result.append(p)
                prev = None
        
        return "".join(result)
    
    def _align_to_pattern(
        self,
        value: str,
        pattern: str,
        props: Dict[str, Any]
    ) -> str:
        """
        Try to align a value to match the target pattern.
        
        Args:
            value: Original value
            pattern: Target pattern signature (e.g., "A-9")
            props: Fingerprint properties
            
        Returns:
            Aligned value or original if cannot align
        """
        separator = props.get("separator")
        prefix = props.get("prefix")
        suffix = props.get("suffix")
        
        result = value
        
        # Extract alphanumeric parts
        import re
        alpha_parts = re.findall(r'[A-Za-z]+', result)
        digit_parts = re.findall(r'\d+', result)
        
        # Add prefix if missing
        if prefix and not result.startswith(prefix):
            result = prefix + result
        
        # Add suffix if missing
        if suffix and not result.endswith(suffix):
            result = result + suffix
        
        # Try to reconstruct based on pattern
        # Pattern format: e.g., "A-9" means letters-separator-digits
        if separator:
            # Check if separator is in pattern
            if separator in pattern:
                # Reconstruct with separator
                if alpha_parts and digit_parts:
                    result = f"{alpha_parts[0]}{separator}{digit_parts[0]}"
                elif alpha_parts:
                    result = alpha_parts[0]
                elif digit_parts:
                    result = digit_parts[0]
        
        return result
    
    def can_correct(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]] = None,
        subtype: Optional[str] = None,
    ) -> Tuple[bool, float]:
        """Check if value can be corrected"""
        # Generic corrector can attempt correction on most values
        if value is None or str(value).strip() == "":
            return False, 0.0
        
        # If we have a fingerprint, check similarity
        if fingerprint:
            common_values = fingerprint.get("common_values", [])
            if str(value) in common_values:
                return True, 1.0
        
        # Assume correction is possible with medium confidence
        return True, 0.5
