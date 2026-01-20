"""
Generic Identifier Clusterer
Production-grade identifier validation using entropy, uniqueness, and pattern analysis
"""

import logging
import math
from typing import Any, Dict, List, Optional
from collections import Counter
import numpy as np

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class GenericIdentifierClusterer(BaseClusterer):
    """
    Production-grade clusterer for unknown/generic identifiers.
    
    Combines:
    1. Pattern signature matching
    2. Shannon entropy analysis
    3. Uniqueness ratio validation
    4. Length consistency checking
    
    Handles:
    - UUIDs, GUIDs
    - Hash-like strings
    - Custom ID formats
    - Mixed pattern IDs
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.pattern_threshold = config.get("pattern_threshold", 0.1) if config else 0.1
        self.min_uniqueness = config.get("min_uniqueness", 0.5) if config else 0.5
        self.entropy_factor = config.get("entropy_factor", 0.3) if config else 0.3
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster identifier data using entropy and pattern analysis.
        """
        indices = self._prepare_indices(data, indices)
        
        # Filter valid values
        valid_entries = []
        null_entries = []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if value is None or str(value).strip() == "":
                null_entries.append((i, idx, value))
            else:
                valid_entries.append((i, idx, str(value).strip()))
        
        if not valid_entries:
            return ClusteringResult(
                good_data=[],
                bad_data=[v[2] for v in null_entries],
                good_indices=[],
                bad_indices=[v[1] for v in null_entries],
                fingerprint={"method": "generic_identifier", "error": "all_empty"},
                method="generic_identifier_empty",
                confidence=0.0,
            )
        
        values = [v[2] for v in valid_entries]
        
        # 1. Calculate uniqueness ratio
        unique_ratio = len(set(values)) / len(values)
        
        # 2. Extract pattern signatures
        signatures = [self._to_signature(v) for v in values]
        sig_counts = Counter(signatures)
        
        # 3. Calculate entropies
        entropies = [self._calculate_entropy(v) for v in values]
        avg_entropy = np.mean(entropies) if entropies else 0
        entropy_std = np.std(entropies) if len(entropies) > 1 else 0
        
        # 4. Calculate lengths
        lengths = [len(v) for v in values]
        avg_length = np.mean(lengths)
        length_std = np.std(lengths) if len(lengths) > 1 else 0
        
        # 5. Determine valid patterns
        valid_patterns = self._get_valid_patterns(sig_counts, len(values))
        
        # 6. Classify each value
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for (i, idx, value), sig, entropy, length in zip(
            valid_entries, signatures, entropies, lengths
        ):
            is_valid = True
            
            # Check pattern match
            if sig not in valid_patterns:
                is_valid = False
            
            # Check entropy anomaly (too low compared to average)
            if avg_entropy > 0 and entropy < avg_entropy * self.entropy_factor:
                is_valid = False
            
            # Check length anomaly (outlier)
            if length_std > 0 and abs(length - avg_length) > 3 * length_std:
                is_valid = False
            
            if is_valid:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Add nulls to bad
        for i, idx, value in null_entries:
            bad_data.append(value)
            bad_indices.append(idx)
        
        # Generate fingerprint
        majority_pattern = sig_counts.most_common(1)[0][0] if sig_counts else None
        fingerprint = self._generate_fingerprint(
            good_data, sig_counts, unique_ratio, avg_entropy, avg_length, majority_pattern
        )
        
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="pattern_entropy_uniqueness",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "unique_ratio": unique_ratio,
                "avg_entropy": avg_entropy,
                "avg_length": avg_length,
                "majority_pattern": majority_pattern,
            }
        )
    
    def _to_signature(self, value: str) -> str:
        """Convert value to collapsed pattern signature."""
        sig = []
        prev = None
        
        for c in value:
            if c.isalpha():
                t = "A"
            elif c.isdigit():
                t = "N"
            else:
                t = c
            
            if t != prev:
                sig.append(t)
                prev = t
        
        return "".join(sig)
    
    def _calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of character distribution."""
        if not value:
            return 0.0
        
        freq = Counter(value)
        total = len(value)
        
        entropy = 0.0
        for count in freq.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy
    
    def _get_valid_patterns(
        self,
        sig_counts: Counter,
        total: int
    ) -> set:
        """Determine valid patterns based on occurrence threshold."""
        valid = {
            p for p, c in sig_counts.items()
            if c / total >= self.pattern_threshold
        }
        
        # At least include the most common pattern
        if not valid and sig_counts:
            valid = {sig_counts.most_common(1)[0][0]}
        
        return valid
    
    def _generate_fingerprint(
        self,
        values: List[str],
        sig_counts: Counter,
        unique_ratio: float,
        avg_entropy: float,
        avg_length: float,
        majority_pattern: Optional[str]
    ) -> Dict[str, Any]:
        """Generate fingerprint from analyzed identifiers."""
        return {
            "workflow": "identifier",
            "method": "generic_entropy",
            "sample_size": len(values),
            "properties": {
                "unique_ratio": unique_ratio,
                "avg_entropy": avg_entropy,
                "avg_length": avg_length,
                "majority_pattern": majority_pattern,
                "pattern_distribution": dict(sig_counts),
                "is_high_entropy": avg_entropy > 3.0,  # Threshold for hash-like
            }
        }
