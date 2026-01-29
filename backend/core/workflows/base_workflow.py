"""
Base Workflow
Abstract base class for all data quality workflows
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..interfaces import (
    IWorkflow,
    IValidator,
    ICorrector,
    ClusterResult,
    WorkflowType,
    FingerprintData,
)
from ..registry import (
    get_validator_registry,
    get_corrector_registry,
    get_fingerprint_registry,
)

logger = logging.getLogger(__name__)


class BaseWorkflow(IWorkflow):
    """
    Base class for all data quality workflows.
    
    Provides:
    - Common clustering logic
    - Fingerprint generation integration
    - Validator and corrector lookup
    - Generic subtype fallback
    """
    
    def __init__(self):
        self._validator_cache: Dict[str, IValidator] = {}
        self._corrector_cache: Dict[str, ICorrector] = {}
        self._fingerprint_generator = None
    
    @property
    @abstractmethod
    def workflow_type(self) -> WorkflowType:
        pass
    
    @property
    @abstractmethod
    def supported_subtypes(self) -> List[str]:
        pass
    
    @property
    def default_subtype(self) -> str:
        """Default/fallback subtype (generic)"""
        return "generic"
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        **kwargs
    ) -> ClusterResult:
        """
        Cluster data into good and bad groups.
        
        This method:
        1. Detects subtype if not provided
        2. Validates each data point
        3. Splits into good/bad groups
        4. Generates fingerprint from good data
        5. Returns complete ClusterResult
        
        Args:
            data: Column data to cluster
            indices: Optional row indices for tracking
            column_name: Column name for context
            subtype: Pre-detected subtype (skip detection if provided)
            **kwargs: Additional workflow-specific parameters
            
        Returns:
            ClusterResult with good/bad split and fingerprint
        """
        # Create indices if not provided
        if indices is None:
            indices = list(range(len(data)))
        
        # Detect subtype if not provided
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        # Get validator for subtype
        validator = self.get_validator(subtype)
        
        # Cluster data
        good_data = []
        bad_data = []
        good_indices = []
        bad_indices = []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            # Skip nulls
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            # Validate
            is_valid, confidence = self.validate_single(value, subtype)
            
            if is_valid:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Generate fingerprint from good data
        fingerprint_dict = None
        if good_data:
            fingerprint_dict = self.generate_fingerprint(good_data, subtype)
        
        # Calculate confidence
        total = len(good_data) + len(bad_data)
        confidence = len(good_data) / total if total > 0 else 0.0
        
        # Determine method based on subtype and validation approach
        method = self._determine_method(subtype, validator)
        
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
                "method": method,  # Track method used
            }
        )
        
        # Also store method in fingerprint if available
        if fingerprint_dict:
            fingerprint_dict["method"] = method
        
        logger.debug(
            f"Clustered {column_name}: {len(good_data)} good, "
            f"{len(bad_data)} bad ({subtype})"
        )
        
        return result
    
    def generate_fingerprint(
        self,
        good_data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """
        Generate fingerprint from good data for correction.
        
        Args:
            good_data: Validated good data
            subtype: Detected subtype
            
        Returns:
            Fingerprint dictionary
        """
        # Get fingerprint generator for this workflow type
        fp_generator = self._get_fingerprint_generator()
        
        if fp_generator:
            fingerprint = fp_generator.generate(good_data, subtype)
            return fingerprint.to_dict() if fingerprint else {}
        
        # Fallback: create basic fingerprint
        return self._create_basic_fingerprint(good_data, subtype)
    
    def _get_fingerprint_generator(self):
        """Get fingerprint generator for this workflow type"""
        if self._fingerprint_generator is None:
            registry = get_fingerprint_registry()
            self._fingerprint_generator = registry.get(self.workflow_type.value)
        
        return self._fingerprint_generator
    
    def _determine_method(self, subtype: str, validator) -> str:
        """Determine clustering method based on subtype and validator."""
        # Map subtypes to methods
        method_map = {
            # Text validators
            "email": "validator_email",
            "phone": "validator_phone",
            "url": "validator_url",
            "ip_address": "validator_ip_address",
            "uuid": "validator_uuid",
            "zipcode": "validator_zipcode",
            "boolean": "validator_boolean",
            "ssn": "validator_ssn",
            # Text freetext
            "name": "freetext_lenient",
            "company": "freetext_lenient",
            "address": "freetext_lenient",
            "job_title": "freetext_lenient",
            "generic": "freetext_lenient",
            # Text categorical
            "state": "categorical_frequency_fuzzy",
            "country": "categorical_frequency_fuzzy",
        }
        
        if subtype in method_map:
            return method_map[subtype]
        
        # Default based on validator presence
        if validator:
            return f"validator_{subtype}"
        return "freetext_lenient"
    
    def _create_basic_fingerprint(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """Create basic fingerprint when generator not available"""
        from collections import Counter
        
        str_data = [str(d) for d in data if d is not None]
        
        return {
            "workflow": self.workflow_type.value,
            "subtype": subtype,
            "sample_size": len(str_data),
            "unique_ratio": len(set(str_data)) / len(str_data) if str_data else 0,
            "common_values": [v for v, _ in Counter(str_data).most_common(5)],
        }
    
    def validate_single(self, value: Any, subtype: str) -> Tuple[bool, float]:
        """
        Validate a single value against subtype rules.
        
        Args:
            value: Value to validate
            subtype: Subtype to validate against
            
        Returns:
            Tuple of (is_valid, confidence)
        """
        validator = self.get_validator(subtype)
        
        if validator:
            return validator.validate(value)
        
        # Default: accept with low confidence
        return True, 0.5
    
    def get_validator(self, subtype: str) -> Optional[IValidator]:
        """
        Get the validator (engine) for a specific subtype.
        
        Args:
            subtype: Subtype to get validator for
            
        Returns:
            IValidator instance or None
        """
        # Check cache
        if subtype in self._validator_cache:
            return self._validator_cache[subtype]
        
        # Look up in registry
        registry = get_validator_registry()
        validator = registry.get(subtype)
        
        if not validator:
            # Try generic fallback
            generic_name = f"generic_{self.workflow_type.value}"
            validator = registry.get(generic_name)
        
        if validator:
            self._validator_cache[subtype] = validator
        
        return validator
    
    def get_corrector(self, subtype: str) -> Optional[ICorrector]:
        """
        Get the corrector for a specific subtype.
        
        Args:
            subtype: Subtype to get corrector for
            
        Returns:
            ICorrector instance or None
        """
        # Check cache
        if subtype in self._corrector_cache:
            return self._corrector_cache[subtype]
        
        # Look up in registry
        registry = get_corrector_registry()
        corrector = registry.get(subtype)
        
        if not corrector:
            # Try generic fallback
            generic_name = f"generic_{self.workflow_type.value}"
            corrector = registry.get(generic_name)
        
        if corrector:
            self._corrector_cache[subtype] = corrector
        
        return corrector
    
    @abstractmethod
    def detect_subtype(
        self,
        data: List[Any],
        column_name: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Detect the specific subtype of data within this workflow.
        
        Args:
            data: Sample of column data
            column_name: Optional column name for hints
            
        Returns:
            Tuple of (subtype, confidence)
        """
        pass
