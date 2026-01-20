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
        """Attempt generic correction"""
        str_val = str(value).strip()
        
        if not fingerprint and not learned_patterns:
            # No fingerprint to learn from
            return self._make_unchanged_result(value)
        
        changes = []
        corrected = str_val
        
        # Get properties from fingerprint
        props = learned_patterns or fingerprint.get("properties", {})
        
        # Pattern-based correction for identifiers
        if subtype in ("identifier", "pattern_id"):
            pattern_sig = props.get("pattern_signature")
            if pattern_sig:
                # Try to align to pattern
                aligned = self._align_to_pattern(str_val, pattern_sig, props)
                if aligned != str_val:
                    corrected = aligned
                    changes.append("pattern_aligned")
        
        # Case correction
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
            return self._make_corrected_result(value, corrected, changes)
        
        return self._make_unchanged_result(value)
    
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
        
        # Add prefix if missing
        if prefix and not result.startswith(prefix):
            result = prefix + result
        
        # Add suffix if missing
        if suffix and not result.endswith(suffix):
            result = result + suffix
        
        # Add separator if missing
        if separator and separator not in result:
            # Try to insert based on pattern
            # This is a simplified approach
            pass
        
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
