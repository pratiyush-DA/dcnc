"""
FreeText String Clusterer
Production-grade clusterer for free-text columns with lenient validation

For columns like: name, company, address, job_title, notes, description

Philosophy:
- Accept most values by default
- Only reject clearly invalid data (gibberish, placeholders, reserved words)
- NO frequency-based rejection (unique values are expected)
- Trust user data unless obviously bad
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class FreeTextStringClusterer(BaseClusterer):
    """
    Lenient clusterer for free-text columns like names, addresses, notes.
    
    Only rejects:
    - Empty/null values
    - Reserved words (null, undefined, n/a, test, invalid, etc.)
    - Extreme structural anomalies (all special chars, gibberish patterns)
    
    Does NOT reject based on:
    - Frequency (unique values are expected)
    - Similarity to reference (no reference set built)
    - Case variations (accepted as-is)
    """
    
    # Reserved/placeholder words that indicate bad data
    RESERVED_WORDS: Set[str] = {
        # Null-like
        "null", "nan", "none", "undefined", "nil", "void",
        # Placeholder
        "n/a", "na", "n.a.", "tbd", "todo", "placeholder", "temp",
        # Invalid markers
        "invalid", "unknown", "test", "testing", "sample", "example",
        # Defaults
        "default", "blank", "empty", "missing",
        # Gibberish patterns
        "asdf", "qwerty", "xxx", "zzz", "aaa", "abc", "xyz",
        "1234", "12345", "123456",
    }
    
    # Patterns that indicate gibberish
    GIBBERISH_PATTERNS = [
        r'^[^a-zA-Z]*$',  # No letters at all
        r'^(.)\1{4,}$',   # Same char repeated 5+ times
        r'^[!@#$%^&*()_+=\[\]{}|\\;:,.<>?/~`]+$',  # All special chars
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Configurable thresholds
        self.min_length = config.get("min_length", 2) if config else 2
        self.min_alpha_ratio = config.get("min_alpha_ratio", 0.3) if config else 0.3
        
        # Compile gibberish patterns
        self._gibberish_patterns = [re.compile(p) for p in self.GIBBERISH_PATTERNS]
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster free-text data with lenient validation.
        
        Args:
            data: List of values to cluster
            indices: Optional row indices
            column_name: Column name for context
            
        Returns:
            ClusteringResult with good/bad separation
        """
        indices = self._prepare_indices(data, indices)
        
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        rejection_reasons = []
        
        for value, idx in zip(data, indices):
            is_valid, reason = self._validate_freetext(value)
            
            if is_valid:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
                rejection_reasons.append({
                    "value": str(value)[:50] if value else None,
                    "reason": reason
                })
        
        # Generate fingerprint for correction hints
        fingerprint = self._create_fingerprint(good_data, column_name)
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="freetext_lenient",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "rejection_summary": self._summarize_rejections(rejection_reasons),
                "validation_mode": "lenient",
            }
        )
    
    def _validate_freetext(self, value: Any) -> tuple[bool, str]:
        """
        Lenient validation - accept most values.
        
        Returns:
            (is_valid, rejection_reason)
        """
        # Null check
        if value is None:
            return False, "null_value"
        
        str_val = str(value).strip()
        
        # Empty check
        if not str_val:
            return False, "empty_value"
        
        # Too short
        if len(str_val) < self.min_length:
            return False, "too_short"
        
        str_lower = str_val.lower()
        
        # Reserved words check
        if str_lower in self.RESERVED_WORDS:
            return False, f"reserved_word:{str_lower}"
        
        # Check if reserved word is part of value (e.g., "test user")
        if any(word in str_lower.split() for word in ["test", "invalid", "null", "undefined"]):
            # Only reject if it's the first word (likely placeholder)
            first_word = str_lower.split()[0] if str_lower.split() else ""
            if first_word in self.RESERVED_WORDS:
                return False, f"starts_with_reserved:{first_word}"
        
        # Low alpha ratio (< 30% letters in long strings)
        if len(str_val) > 3:
            alpha_ratio = sum(c.isalpha() for c in str_val) / len(str_val)
            if alpha_ratio < self.min_alpha_ratio:
                return False, f"low_alpha_ratio:{alpha_ratio:.2f}"
        
        # Gibberish pattern check
        for i, pattern in enumerate(self._gibberish_patterns):
            if pattern.match(str_val):
                return False, f"gibberish_pattern_{i}"
        
        # Email in non-email column (likely misplaced data)
        if "@" in str_val and "." in str_val:
            return False, "email_in_freetext"
        
        # Accept everything else
        return True, ""
    
    def _create_fingerprint(
        self, 
        values: List[Any], 
        column_name: Optional[str]
    ) -> Dict[str, Any]:
        """Create fingerprint for correction hints."""
        if not values:
            return {
                "workflow": "string",
                "method": "freetext",
                "properties": {},
            }
        
        str_values = [str(v).strip() for v in values if v is not None]
        lengths = [len(v) for v in str_values]
        
        # Analyze case patterns
        case_counts = {"title": 0, "upper": 0, "lower": 0, "mixed": 0}
        for v in str_values:
            if v.istitle():
                case_counts["title"] += 1
            elif v.isupper():
                case_counts["upper"] += 1
            elif v.islower():
                case_counts["lower"] += 1
            else:
                case_counts["mixed"] += 1
        
        dominant_case = max(case_counts, key=case_counts.get)
        
        return {
            "workflow": "string",
            "method": "freetext",
            "column_name": column_name,
            "sample_size": len(str_values),
            "properties": {
                "avg_length": sum(lengths) / len(lengths) if lengths else 0,
                "min_length": min(lengths) if lengths else 0,
                "max_length": max(lengths) if lengths else 0,
                "dominant_case": dominant_case,
                "case_distribution": case_counts,
                "sample_values": str_values[:5],
            },
            "correction_hints": {
                "mode": "lenient",
                "expected_case": dominant_case,
                "allow_mixed_case": True,
            },
            "validation_rules": {
                "min_length": self.min_length,
                "min_alpha_ratio": self.min_alpha_ratio,
                "reserved_words_checked": True,
            }
        }
    
    def _summarize_rejections(self, reasons: List[Dict]) -> Dict[str, int]:
        """Summarize rejection reasons."""
        from collections import Counter
        reason_counts = Counter(r["reason"].split(":")[0] for r in reasons)
        return dict(reason_counts.most_common())
