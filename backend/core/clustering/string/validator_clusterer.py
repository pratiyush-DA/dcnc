"""
Validator String Clusterer
Uses existing validation engines for known string subtypes
"""

import logging
from typing import Any, Dict, List, Optional

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class ValidatorStringClusterer(BaseClusterer):
    """
    Clusterer for string data with known validators.
    
    Wraps existing validation engines (email, phone, url, etc.)
    for deterministic rule-based validation.
    
    Supported engines:
        - email, phone, url, uuid, ip_address, zipcode, boolean
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.engine_name = config.get("engine", "generic_string") if config else "generic_string"
        self._engine = None
    
    def _get_engine(self):
        """Lazy load the validation engine."""
        if self._engine is None:
            from ...registry import get_validator_registry
            registry = get_validator_registry()
            self._engine = registry.get(self.engine_name)
            if self._engine is None:
                logger.warning(f"Validator '{self.engine_name}' not found, using fallback")
        return self._engine
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster string data using validator engine.
        """
        indices = self._prepare_indices(data, indices)
        engine = self._get_engine()
        
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        confidence_scores = []
        
        # Detect majority case for format consistency
        case_votes = {"lower": 0, "upper": 0, "mixed": 0}
        
        for value, idx in zip(data, indices):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            str_val = str(value).strip()
            
            if engine:
                try:
                    is_valid, confidence = engine.validate(str_val)
                    
                    if is_valid and confidence >= 0.5:
                        # Track case pattern
                        if str_val.islower():
                            case_votes["lower"] += 1
                        elif str_val.isupper():
                            case_votes["upper"] += 1
                        else:
                            case_votes["mixed"] += 1
                        
                        good_data.append(value)
                        good_indices.append(idx)
                        confidence_scores.append(confidence)
                    else:
                        bad_data.append(value)
                        bad_indices.append(idx)
                except Exception as e:
                    logger.warning(f"Validation error for '{str_val[:50]}': {e}")
                    bad_data.append(value)
                    bad_indices.append(idx)
            else:
                # No engine - fallback to basic non-empty check
                if len(str_val) > 0:
                    good_data.append(value)
                    good_indices.append(idx)
                    confidence_scores.append(0.5)
                else:
                    bad_data.append(value)
                    bad_indices.append(idx)
        
        # Phase 2: Case consistency check for email
        # Emails should be lowercase - flag uppercase emails for correction
        majority_case = max(case_votes, key=case_votes.get)
        expected_case = "lower" if self.engine_name == "email" else majority_case
        
        if self.engine_name == "email" and case_votes["upper"] > 0:
            # Re-process to move uppercase emails to bad
            new_good_data, new_good_indices = [], []
            for val, idx in zip(good_data.copy(), good_indices.copy()):
                str_val = str(val).strip()
                if str_val.isupper():
                    # Uppercase email - move to bad for correction
                    bad_data.append(val)
                    bad_indices.append(idx)
                    # Also remove from good
                    if val in good_data:
                        idx_in_good = good_data.index(val)
                        confidence_scores.pop(idx_in_good) if idx_in_good < len(confidence_scores) else None
                else:
                    new_good_data.append(val)
                    new_good_indices.append(idx)
            good_data = new_good_data
            good_indices = new_good_indices
        
        # Phase 3: Phone format consistency
        # Detect majority format and flag non-conforming for correction
        majority_format = None
        if self.engine_name == "phone":
            format_counts = {}
            for val in good_data:
                fmt = self._detect_phone_format(str(val).strip())
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            
            if format_counts:
                majority_format = max(format_counts, key=format_counts.get)
                
                # Re-process to move non-majority format to bad
                new_good_data, new_good_indices, new_conf = [], [], []
                for val, idx, conf in zip(good_data.copy(), good_indices.copy(), 
                                          confidence_scores.copy() if confidence_scores else [1.0]*len(good_data)):
                    str_val = str(val).strip()
                    if self._detect_phone_format(str_val) == majority_format:
                        new_good_data.append(val)
                        new_good_indices.append(idx)
                        new_conf.append(conf)
                    else:
                        # Different format - move to bad for correction
                        bad_data.append(val)
                        bad_indices.append(idx)
                
                good_data = new_good_data
                good_indices = new_good_indices
                confidence_scores = new_conf
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(good_data, confidence_scores)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method=f"validator_{self.engine_name}",
            confidence=avg_confidence,
            metadata={
                "column_name": column_name,
                "engine": self.engine_name,
                "avg_validation_confidence": avg_confidence,
            }
        )
    
    def _generate_fingerprint(
        self,
        values: List[str],
        confidence_scores: List[float]
    ) -> Dict[str, Any]:
        """Generate fingerprint from validated values."""
        if not values:
            return {
                "workflow": "string",
                "method": "validator",
                "engine": self.engine_name,
                "properties": {},
            }
        
        str_values = [str(v) for v in values]
        lengths = [len(v) for v in str_values]
        
        fingerprint = {
            "workflow": "string",
            "method": "validator",
            "engine": self.engine_name,
            "sample_size": len(values),
            "properties": {
                "avg_length": sum(lengths) / len(lengths),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "sample_values": str_values[:5],
            }
        }
        
        # Add format info for phone
        if self.engine_name == "phone" and values:
            format_counts = {}
            for val in values:
                fmt = self._detect_phone_format(str(val))
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            if format_counts:
                majority_fmt = max(format_counts, key=format_counts.get)
                fingerprint["correction_hints"] = {
                    "expected_format": majority_fmt,
                    "format_distribution": format_counts,
                }
        
        # Add case info for email
        if self.engine_name == "email":
            fingerprint["correction_hints"] = {
                "expected_case": "lowercase",
            }
        
        return fingerprint
    
    def _detect_phone_format(self, phone: str) -> str:
        """
        Detect the format of a phone number.
        Returns a format identifier for grouping.
        """
        import re
        
        # Check common formats
        if re.match(r"^\d{3}-\d{3}-\d{4}$", phone):
            return "XXX-XXX-XXXX"
        if re.match(r"^\(\d{3}\)\s*\d{3}-\d{4}$", phone):
            return "(XXX) XXX-XXXX"
        if re.match(r"^\+\d{1,3}-\d{3}-\d{3}-\d{4}$", phone):
            return "+X-XXX-XXX-XXXX"
        if re.match(r"^\+\d{1,3}\s+\d+", phone):
            return "+X INTL"
        if re.match(r"^\d{10}$", phone):
            return "XXXXXXXXXX"
        if re.match(r"^\d{3}\.\d{3}\.\d{4}$", phone):
            return "XXX.XXX.XXXX"
        
        return "other"
