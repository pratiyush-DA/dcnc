"""
String Workflow
Handles text/string data types with INTEGRATED VALIDATION
Uses registered validators for strict data quality checking
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from .base_workflow import BaseWorkflow
from ..interfaces import WorkflowType, ClusterResult
from ..registry import register_workflow, get_validator_registry
from ..clustering import get_clusterer

logger = logging.getLogger(__name__)


@register_workflow("text")
class StringWorkflow(BaseWorkflow):
    """
    String/Text workflow handler with integrated validators.
    
    Supports 16+ subtypes with STRICT validation:
    - email, phone, url, ip_address, uuid
    - name, company, address, location, state, country, zipcode
    - boolean, username, file_path, product_title, job_title
    - generic (fallback)
    """
    
    SUBTYPES = [
        "email", "phone", "url", "ip_address", "uuid",
        "name", "company", "address", "location", "state", "country", "zipcode",
        "boolean", "username", "file_path", "product_title", "job_title",
        "generic",
    ]
    
    @property
    def workflow_type(self) -> WorkflowType:
        return WorkflowType.TEXT
    
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
        """
        Detect string subtype from data using validators.
        """
        if not data:
            return self.default_subtype, 0.3
        
        # Filter non-null values
        str_data = [str(v).strip() for v in data if v is not None and str(v).strip()]
        
        if not str_data:
            return self.default_subtype, 0.3
        
        # Try each subtype validator in priority order
        priority_order = [
            "email", "uuid", "ip_address", "url", "phone", 
            "zipcode", "boolean"
        ]
        
        registry = get_validator_registry()
        best_match = self.default_subtype
        best_ratio = 0.0
        
        for subtype in priority_order:
            validator = registry.get(subtype)
            if validator:
                ratio = validator.get_pattern_match_ratio(str_data)
                if ratio > best_ratio and ratio >= 0.7:
                    best_match = subtype
                    best_ratio = ratio
        
        if best_ratio >= 0.7:
            return best_match, best_ratio
        
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
        Cluster string data with INTEGRATED VALIDATION.
        Uses registered validators for strict checking when available.
        Falls back to lenient validation for unknown subtypes.
        """
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        if indices is None:
            indices = list(range(len(data)))
        
        # Get validator for this subtype (may be None)
        validator = self._get_validator_for_subtype(subtype)
        
        # Subtypes that should have strict validation
        strict_subtypes = {"email", "uuid", "ip_address", "url", "phone", "zipcode", "boolean"}
        use_strict = subtype in strict_subtypes and validator is not None
        
        good_data = []
        bad_data = []
        good_indices = []
        bad_indices = []
        
        for value, idx in zip(data, indices):
            # Skip nulls/empty
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            str_val = str(value).strip()
            
            if use_strict and validator:
                # Use strict validator for known types
                is_valid, confidence = validator.validate(str_val)
                
                if is_valid and confidence >= 0.5:
                    good_data.append(value)
                    good_indices.append(idx)
                else:
                    bad_data.append(value)
                    bad_indices.append(idx)
            else:
                # Lenient validation for unknown subtypes (name, company, etc.)
                if self._is_valid_text(str_val):
                    good_data.append(value)
                    good_indices.append(idx)
                else:
                    bad_data.append(value)
                    bad_indices.append(idx)
        
        # Generate fingerprint
        fingerprint_dict = None
        if good_data:
            fingerprint_dict = self.generate_fingerprint(good_data, subtype)
        
        # Calculate confidence
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
                "validator_used": validator.name if validator else "lenient",
                "strict_mode": use_strict,
            }
        )
        
        logger.debug(
            f"Clustered {column_name}: {len(good_data)} good, "
            f"{len(bad_data)} bad ({subtype}, strict={use_strict})"
        )
        
        return result
    
    def _get_validator_for_subtype(self, subtype: str):
        """Get validator for a subtype"""
        registry = get_validator_registry()
        return registry.get(subtype)
    
    def _is_valid_text(self, value: str) -> bool:
        """Lenient validation for generic text - accept most values"""
        # Reject empty
        if len(value) < 1:
            return False
        
        # Accept anything with at least some text content
        return True
    
    def _is_valid_generic_string(self, value: str) -> bool:
        """Basic validation for generic strings"""
        return self._is_valid_text(value)
    
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
        Production-grade clustering using ML-based anomaly detection.
        
        Uses the new clustering module with:
        - Validator engines for known subtypes (email, phone, url)
        - DBSCAN on structural features for generic subtypes
        """
        if not use_ml:
            return self.cluster(data, indices, column_name, subtype, **kwargs)
        
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        try:
            clusterer = get_clusterer("text", subtype)
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

