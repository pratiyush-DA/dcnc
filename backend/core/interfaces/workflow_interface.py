"""
Workflow Interface
Base interface for all data quality workflows (String, Numeric, DateTime, Identifier)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class WorkflowType(str, Enum):
    """Enumeration of workflow types"""
    TEXT = "text"
    NUMERIC = "numeric"
    DATETIME = "datetime"
    IDENTIFIER = "identifier"


@dataclass
class ClusterResult:
    """
    Result of clustering operation.
    Contains good/bad data split and metadata for correction.
    """
    # Core clustering results
    good_data: List[Any] = field(default_factory=list)
    bad_data: List[Any] = field(default_factory=list)
    
    # Type information
    workflow: str = ""
    subtype: str = ""
    
    # Confidence in the clustering
    confidence: float = 0.0
    
    # Fingerprint from good data (passed to corrector)
    fingerprint: Optional[Dict[str, Any]] = None
    
    # Format information (for datetime)
    target_format: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Row indices for tracking
    good_indices: List[int] = field(default_factory=list)
    bad_indices: List[int] = field(default_factory=list)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics of clustering result"""
        total = len(self.good_data) + len(self.bad_data)
        return {
            "total_records": total,
            "good_count": len(self.good_data),
            "bad_count": len(self.bad_data),
            "good_ratio": len(self.good_data) / total if total > 0 else 0,
            "workflow": self.workflow,
            "subtype": self.subtype,
            "confidence": self.confidence,
            "has_fingerprint": self.fingerprint is not None,
        }


class IWorkflow(ABC):
    """
    Abstract base class for all data quality workflows.
    
    Each workflow handles a specific type of data (text, numeric, datetime, identifier)
    and provides:
    - Subtype detection
    - Data clustering (good/bad split)
    - Fingerprint generation from good data
    - Integration with validators and correctors
    """
    
    @property
    @abstractmethod
    def workflow_type(self) -> WorkflowType:
        """Return the type of this workflow"""
        pass
    
    @property
    @abstractmethod
    def supported_subtypes(self) -> List[str]:
        """List of supported subtypes for this workflow"""
        pass
    
    @property
    def default_subtype(self) -> str:
        """Default/fallback subtype (generic)"""
        return "generic"
    
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
    
    @abstractmethod
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
        1. Validates each data point against subtype rules
        2. Generates fingerprint from good data
        3. Returns ClusterResult with all information
        
        Args:
            data: Column data to cluster
            indices: Optional row indices for tracking
            column_name: Column name for context
            subtype: Pre-detected subtype (skip detection if provided)
            **kwargs: Additional workflow-specific parameters
            
        Returns:
            ClusterResult with good/bad split and fingerprint
        """
        pass
    
    @abstractmethod
    def generate_fingerprint(
        self,
        good_data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """
        Generate fingerprint from good data for correction.
        
        The fingerprint captures the "ideal" characteristics of good data:
        - Pattern signatures
        - Statistical properties
        - Common formats/structures
        
        Args:
            good_data: Validated good data
            subtype: Detected subtype
            
        Returns:
            Fingerprint dictionary
        """
        pass
    
    @abstractmethod
    def get_validator(self, subtype: str):
        """
        Get the validator (engine) for a specific subtype.
        
        Args:
            subtype: Subtype to get validator for
            
        Returns:
            IValidator instance
        """
        pass
    
    @abstractmethod
    def get_corrector(self, subtype: str):
        """
        Get the corrector for a specific subtype.
        
        Args:
            subtype: Subtype to get corrector for
            
        Returns:
            ICorrector instance
        """
        pass
    
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
        return True, 0.5  # Default to passing with low confidence
