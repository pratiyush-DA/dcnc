"""
Identifier Workflow
Handles ID/identifier data types with pattern-based clustering
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from .base_workflow import BaseWorkflow
from ..interfaces import WorkflowType, ClusterResult
from ..registry import register_workflow
from ..clustering import get_clusterer

logger = logging.getLogger(__name__)


@register_workflow("identifier")
class IdentifierWorkflow(BaseWorkflow):
    """
    Identifier workflow handler.
    
    Handles IDs with consistent patterns:
    - Product codes (SKU-12345)
    - Employee IDs (EMP-0001)
    - Order numbers, etc.
    
    Key Feature: Uses pattern fingerprinting to detect
    IDs that don't match the majority pattern.
    
    Subtypes:
    - pattern_id (e.g., ABC-1234)
    - numeric_id (e.g., 12345)
    - generic (fallback)
    """
    
    SUBTYPES = ["pattern_id", "numeric_id", "generic"]
    
    @property
    def workflow_type(self) -> WorkflowType:
        return WorkflowType.IDENTIFIER
    
    @property
    def supported_subtypes(self) -> List[str]:
        return self.SUBTYPES
    
    @property
    def default_subtype(self) -> str:
        return "generic"
    
    def detect_subtype(
        self,
        data: List[Any],
        column_name: Optional[str] = None
    ) -> Tuple[str, float]:
        """Detect identifier subtype"""
        if not data:
            return self.default_subtype, 0.3
        
        str_data = [str(v).strip() for v in data if v is not None and str(v).strip()]
        
        if not str_data:
            return self.default_subtype, 0.3
        
        # Check if purely numeric
        numeric_count = sum(1 for s in str_data if s.isdigit())
        
        if numeric_count / len(str_data) > 0.9:
            return "numeric_id", 0.8
        
        # Check for pattern structure
        has_pattern = any(
            re.search(r"[A-Za-z]+[-_][0-9]+|[0-9]+[-_][A-Za-z]+", s)
            for s in str_data
        )
        
        if has_pattern:
            return "pattern_id", 0.8
        
        return self.default_subtype, 0.5
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        **kwargs
    ) -> ClusterResult:
        """
        Cluster identifier data using pattern fingerprinting.
        
        IDs that don't match the majority pattern are flagged as bad.
        """
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        if indices is None:
            indices = list(range(len(data)))
        
        # First pass: collect all patterns
        pattern_map = {}  # value -> pattern
        pattern_counts = Counter()
        
        for value in data:
            if value is None or str(value).strip() == "":
                continue
            
            str_val = str(value).strip()
            pattern = self._value_to_pattern(str_val)
            pattern_map[str_val] = pattern
            pattern_counts[pattern] += 1
        
        # Find majority pattern(s)
        if not pattern_counts:
            # All null/empty - return as bad
            return ClusterResult(
                good_data=[],
                bad_data=list(data),
                workflow=self.workflow_type.value,
                subtype=subtype,
                confidence=0.0,
                bad_indices=indices,
            )
        
        # Get majority pattern(s) - patterns with >10% occurrence
        total_patterns = sum(pattern_counts.values())
        valid_patterns = {
            p for p, c in pattern_counts.items()
            if c / total_patterns >= 0.1  # At least 10% of values
        }
        
        # If only one dominant pattern, use stricter threshold
        if len(pattern_counts) == 1 or pattern_counts.most_common(1)[0][1] / total_patterns > 0.8:
            valid_patterns = {pattern_counts.most_common(1)[0][0]}
        
        # Second pass: cluster based on pattern match
        good_data = []
        bad_data = []
        good_indices = []
        bad_indices = []
        
        for value, idx in zip(data, indices):
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            str_val = str(value).strip()
            pattern = pattern_map.get(str_val, "")
            
            if pattern in valid_patterns:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Generate fingerprint
        fingerprint_dict = None
        if good_data:
            fingerprint_dict = self.generate_fingerprint(good_data, subtype)
            fingerprint_dict["majority_pattern"] = list(valid_patterns)[0] if valid_patterns else None
            fingerprint_dict["pattern_counts"] = dict(pattern_counts)
        
        total = len(good_data) + len(bad_data)
        confidence = len(good_data) / total if total > 0 else 0.0
        
        result = ClusterResult(
            good_data=good_data,
            bad_data=bad_data,
            workflow=self.workflow_type.value,
            subtype=subtype,
            confidence=confidence,
            fingerprint=fingerprint_dict,
            good_indices=good_indices,
            bad_indices=bad_indices,
            metadata={
                "column_name": column_name,
                "total_records": total,
                "valid_patterns": list(valid_patterns),
            }
        )
        
        return result
    
    def _value_to_pattern(self, value: str) -> str:
        """
        Convert value to pattern signature.
        
        Examples:
            "ABC-1234" -> "A-9"
            "EMP_00123" -> "A_9"
            "12345" -> "9"
        """
        pattern = []
        prev_type = None
        
        for char in value:
            if char.isalpha():
                curr_type = "A"
            elif char.isdigit():
                curr_type = "9"
            else:
                # Keep separator as is
                pattern.append(char)
                prev_type = None
                continue
            
            # Collapse consecutive same types
            if curr_type != prev_type:
                pattern.append(curr_type)
                prev_type = curr_type
        
        return "".join(pattern)
    
    def cluster_v2(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        use_ml: bool = True,
        **kwargs
    ) -> ClusterResult:
        """
        Production-grade clustering using pattern and entropy analysis.
        
        Uses the new clustering module with:
        - Pattern signature matching for pattern_id / numeric_id
        - Entropy + uniqueness analysis for generic identifiers
        """
        if not use_ml:
            return self.cluster(data, indices, column_name, subtype, **kwargs)
        
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        try:
            clusterer = get_clusterer("identifier", subtype)
            result = clusterer.cluster(data, indices, column_name, **kwargs)
            
            return ClusterResult(
                good_data=result.good_data,
                bad_data=result.bad_data,
                workflow=self.workflow_type.value,
                subtype=subtype,
                confidence=result.confidence,
                fingerprint=result.fingerprint,
                good_indices=result.good_indices,
                bad_indices=result.bad_indices,
                metadata={
                    "column_name": column_name,
                    "total_records": result.total_count,
                    "clustering_method": result.method,
                    **result.metadata,
                }
            )
        except Exception as e:
            logger.warning(f"ML clustering failed: {e}, falling back to legacy")
            return self.cluster(data, indices, column_name, subtype, **kwargs)

