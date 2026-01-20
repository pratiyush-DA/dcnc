"""
Generic String Validation Engine
Fallback engine for unclassified string data
Uses fingerprint-based validation
"""

from typing import Any, Dict, List, Optional, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("generic_string")
class GenericStringEngine(BaseEngine):
    """
    Generic string validation engine (FALLBACK).
    
    Used when no specific string subtype is detected.
    Uses fingerprint-based similarity validation.
    
    Capabilities:
    - Length-based validation
    - Pattern similarity checking
    - Statistical outlier detection
    - Fingerprint-driven validation
    """
    
    def __init__(self):
        super().__init__()
        self._fingerprint: Optional[Dict[str, Any]] = None
    
    @property
    def name(self) -> str:
        return "generic_string"
    
    @property
    def description(self) -> str:
        return "Generic string validation using fingerprint similarity"
    
    @property
    def patterns(self) -> List[str]:
        return []  # Uses fingerprint instead of patterns
    
    def set_fingerprint(self, fingerprint: Dict[str, Any]):
        """
        Set the fingerprint for validation.
        
        Args:
            fingerprint: Fingerprint from good data
        """
        self._fingerprint = fingerprint
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate using fingerprint similarity"""
        if not self._fingerprint:
            # No fingerprint - accept with low confidence
            if value:
                return True, 0.5
            return False, 0.0
        
        # Calculate similarity to fingerprint
        similarity = self._calculate_similarity(value)
        
        # Accept if similarity is above threshold
        if similarity >= 0.6:
            return True, similarity
        
        return False, similarity
    
    def _calculate_similarity(self, value: str) -> float:
        """Calculate similarity to fingerprint"""
        if not self._fingerprint:
            return 0.5
        
        props = self._fingerprint.get("properties", {})
        scores = []
        
        # Length similarity
        avg_len = props.get("avg_length")
        if avg_len:
            len_std = max(props.get("length_std", avg_len * 0.3), 1)
            diff = abs(len(value) - avg_len)
            len_score = max(0, 1 - diff / (len_std * 3))
            scores.append(len_score)
        
        # Case style similarity
        target_case = props.get("case_style", "mixed")
        actual_case = self._detect_case(value)
        if target_case == actual_case:
            scores.append(1.0)
        elif target_case == "mixed" or actual_case == "mixed":
            scores.append(0.7)
        else:
            scores.append(0.3)
        
        # Word count similarity
        target_words = props.get("avg_word_count")
        if target_words:
            actual_words = len(value.split())
            word_diff = abs(actual_words - target_words)
            word_score = max(0, 1 - word_diff / max(target_words, 1))
            scores.append(word_score)
        
        # Alpha ratio similarity
        target_alpha = props.get("avg_alpha_ratio", 0.8)
        actual_alpha = sum(c.isalpha() for c in value) / max(len(value), 1)
        alpha_diff = abs(actual_alpha - target_alpha)
        alpha_score = max(0, 1 - alpha_diff)
        scores.append(alpha_score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _detect_case(self, value: str) -> str:
        """Detect case style of value"""
        if value.isupper():
            return "upper"
        if value.islower():
            return "lower"
        if value.istitle():
            return "title"
        return "mixed"
    
    def validate_with_fingerprint(
        self,
        value: Any,
        fingerprint: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Validate using a specific fingerprint.
        
        Args:
            value: Value to validate
            fingerprint: Fingerprint to use
            
        Returns:
            Tuple of (is_valid, confidence)
        """
        old_fp = self._fingerprint
        self._fingerprint = fingerprint
        
        result = self.validate(value)
        
        self._fingerprint = old_fp
        return result
