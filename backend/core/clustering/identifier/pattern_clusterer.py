"""
Pattern Identifier Clusterer
Pattern signature-based clustering for structured IDs
"""

import re
import logging
from typing import Any, Dict, List, Optional
from collections import Counter

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class PatternIdentifierClusterer(BaseClusterer):
    """
    Clusterer for structured identifier patterns.
    
    Uses pattern signature matching to detect IDs
    that don't match the majority pattern.
    
    Examples:
        - "ABC-1234" -> "A-N" (alpha-numeric)
        - "EMP_00123" -> "A_N" (alpha_numeric)
        - "12345" -> "N" (pure numeric)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.threshold = config.get("threshold", 0.1) if config else 0.1
        self.majority_threshold = config.get("majority_threshold", 0.6) if config else 0.6
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster identifiers using pattern signatures.
        """
        indices = self._prepare_indices(data, indices)
        
        # First pass: collect all patterns
        pattern_map = {}  # index -> pattern
        pattern_counts = Counter()
        
        for i, value in enumerate(data):
            if value is None or str(value).strip() == "":
                continue
            
            str_val = str(value).strip()
            pattern = self._value_to_pattern(str_val)
            pattern_map[i] = pattern
            pattern_counts[pattern] += 1
        
        if not pattern_counts:
            # All null/empty
            return ClusteringResult(
                good_data=[],
                bad_data=list(data),
                good_indices=[],
                bad_indices=list(indices),
                fingerprint={"method": "pattern_identifier", "error": "all_empty"},
                method="pattern_identifier_empty",
                confidence=0.0,
            )
        
        # Determine valid patterns
        total_patterns = sum(pattern_counts.values())
        valid_patterns = self._get_valid_patterns(pattern_counts, total_patterns)
        
        # Second pass: classify based on pattern match
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            pattern = pattern_map.get(i)
            
            if pattern in valid_patterns:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Fingerprint
        majority_pattern = pattern_counts.most_common(1)[0][0] if pattern_counts else None
        fingerprint = self._generate_fingerprint(
            good_data, pattern_counts, valid_patterns, majority_pattern
        )
        
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="pattern_signature",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "majority_pattern": majority_pattern,
                "valid_patterns": list(valid_patterns),
                "pattern_distribution": dict(pattern_counts),
            }
        )
    
    def _value_to_pattern(self, value: str) -> str:
        """
        Convert value to pattern signature.
        
        Examples:
            "ABC-1234" -> "A-N"
            "EMP_00123" -> "A_N"
            "12345" -> "N"
        """
        pattern = []
        prev_type = None
        
        for char in value:
            if char.isalpha():
                curr_type = "A"
            elif char.isdigit():
                curr_type = "N"
            else:
                # Keep separator as is, reset prev_type
                pattern.append(char)
                prev_type = None
                continue
            
            # Collapse consecutive same types
            if curr_type != prev_type:
                pattern.append(curr_type)
                prev_type = curr_type
        
        return "".join(pattern)
    
    def _get_valid_patterns(
        self,
        pattern_counts: Counter,
        total: int
    ) -> set:
        """Determine which patterns are valid."""
        # Check if there's a dominant pattern
        most_common_pattern, most_common_count = pattern_counts.most_common(1)[0]
        
        if most_common_count / total >= self.majority_threshold:
            # Clear majority - only that pattern is valid
            return {most_common_pattern}
        
        # No clear majority - accept patterns with >= threshold occurrence
        valid = {
            p for p, c in pattern_counts.items()
            if c / total >= self.threshold
        }
        
        # If no patterns meet threshold, use the most common one
        if not valid:
            valid = {most_common_pattern}
        
        return valid
    
    def _generate_fingerprint(
        self,
        values: List[Any],
        pattern_counts: Counter,
        valid_patterns: set,
        majority_pattern: Optional[str]
    ) -> Dict[str, Any]:
        """Generate fingerprint from identifier patterns."""
        str_values = [str(v) for v in values if v is not None]
        lengths = [len(v) for v in str_values] if str_values else [0]
        
        return {
            "workflow": "identifier",
            "method": "pattern_signature",
            "sample_size": len(values),
            "properties": {
                "majority_pattern": majority_pattern,
                "valid_patterns": list(valid_patterns),
                "pattern_distribution": dict(pattern_counts),
                "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            }
        }
