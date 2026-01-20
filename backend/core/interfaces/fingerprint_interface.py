"""
Fingerprint Interface
Base interface for fingerprint generation from good data
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FingerprintData:
    """
    Fingerprint data structure.
    Captures characteristics of "good" data for correction learning.
    """
    # Type information
    workflow: str = ""
    subtype: str = ""
    
    # Statistical properties (common to all)
    sample_size: int = 0
    unique_ratio: float = 0.0
    null_ratio: float = 0.0
    
    # Type-specific fingerprint data
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Pattern information
    patterns: List[str] = field(default_factory=list)
    pattern_signature: Optional[str] = None
    
    # Common values for reference
    common_values: List[Any] = field(default_factory=list)
    
    # Confidence in the fingerprint
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "workflow": self.workflow,
            "subtype": self.subtype,
            "sample_size": self.sample_size,
            "unique_ratio": self.unique_ratio,
            "null_ratio": self.null_ratio,
            "properties": self.properties,
            "patterns": self.patterns,
            "pattern_signature": self.pattern_signature,
            "common_values": self.common_values[:10],  # Limit
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FingerprintData":
        """Create from dictionary"""
        return cls(
            workflow=data.get("workflow", ""),
            subtype=data.get("subtype", ""),
            sample_size=data.get("sample_size", 0),
            unique_ratio=data.get("unique_ratio", 0.0),
            null_ratio=data.get("null_ratio", 0.0),
            properties=data.get("properties", {}),
            patterns=data.get("patterns", []),
            pattern_signature=data.get("pattern_signature"),
            common_values=data.get("common_values", []),
            confidence=data.get("confidence", 0.0),
        )


class IFingerprint(ABC):
    """
    Abstract base class for fingerprint generators.
    
    Fingerprints capture the "ideal" characteristics of good data:
    - For strings: length, case style, word count, patterns
    - For numerics: mean, std, range, distribution
    - For datetime: format, timezone, date range
    - For identifiers: pattern signature, prefix/suffix
    
    Correctors use fingerprints to learn how to fix bad data.
    """
    
    @property
    @abstractmethod
    def workflow_type(self) -> str:
        """Workflow type this fingerprint handles"""
        pass
    
    @abstractmethod
    def generate(
        self,
        data: List[Any],
        subtype: str,
        column_name: Optional[str] = None
    ) -> FingerprintData:
        """
        Generate fingerprint from good data.
        
        Args:
            data: Good/valid data samples
            subtype: Data subtype
            column_name: Column name for context
            
        Returns:
            FingerprintData with captured characteristics
        """
        pass
    
    @abstractmethod
    def get_correction_hints(
        self,
        fingerprint: FingerprintData,
        bad_value: Any
    ) -> Dict[str, Any]:
        """
        Get hints for correcting a bad value based on fingerprint.
        
        Args:
            fingerprint: Generated fingerprint from good data
            bad_value: The bad value to be corrected
            
        Returns:
            Dictionary of correction hints/instructions
        """
        pass
    
    def calculate_similarity(
        self,
        fingerprint: FingerprintData,
        value: Any
    ) -> float:
        """
        Calculate how similar a value is to the fingerprint pattern.
        
        Args:
            fingerprint: Reference fingerprint
            value: Value to check
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Default implementation - override for specific logic
        return 0.5
    
    def merge_fingerprints(
        self,
        fingerprints: List[FingerprintData]
    ) -> FingerprintData:
        """
        Merge multiple fingerprints into one.
        Useful for combining fingerprints from multiple columns.
        
        Args:
            fingerprints: List of fingerprints to merge
            
        Returns:
            Merged fingerprint
        """
        if not fingerprints:
            return FingerprintData()
        
        if len(fingerprints) == 1:
            return fingerprints[0]
        
        # Default: use first fingerprint as base
        merged = FingerprintData(
            workflow=fingerprints[0].workflow,
            subtype=fingerprints[0].subtype,
            sample_size=sum(f.sample_size for f in fingerprints),
            confidence=sum(f.confidence for f in fingerprints) / len(fingerprints),
        )
        
        # Merge properties (subclasses should override)
        merged.properties = fingerprints[0].properties.copy()
        
        return merged
