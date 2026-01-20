"""
Corrector Interface
Base interface for all correction engines
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class CorrectionStatus(str, Enum):
    """Status of a correction attempt"""
    CORRECTED = "corrected"      # Successfully corrected
    UNCHANGED = "unchanged"      # Already correct, no change needed
    REJECTED = "rejected"        # Cannot be corrected
    PARTIAL = "partial"          # Partially corrected
    SKIPPED = "skipped"          # Skipped (e.g., null value)


@dataclass
class CorrectionResult:
    """
    Result of correction operation.
    """
    # Original and corrected values
    original_value: Any
    corrected_value: Any
    
    # Status of correction
    status: CorrectionStatus
    
    # Confidence in the correction (0.0 to 1.0)
    confidence: float = 0.0
    
    # List of changes made
    changes_made: List[str] = field(default_factory=list)
    
    # Detailed correction metadata
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Row index for tracking
    row_index: Optional[int] = None
    
    @property
    def was_changed(self) -> bool:
        """Check if value was actually changed"""
        return self.status == CorrectionStatus.CORRECTED
    
    @property
    def is_usable(self) -> bool:
        """Check if the result is usable in final output"""
        return self.status in (
            CorrectionStatus.CORRECTED, 
            CorrectionStatus.UNCHANGED
        )


class ICorrector(ABC):
    """
    Abstract base class for all correction engines.
    
    Correctors attempt to fix bad data values using:
    - Fingerprint from good data (learning from patterns)
    - Type-specific correction rules
    - Common error patterns and fixes
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this corrector"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass
    
    @property
    @abstractmethod
    def supported_subtypes(self) -> List[str]:
        """List of subtypes this corrector can handle"""
        pass
    
    @abstractmethod
    def correct(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]] = None,
        subtype: Optional[str] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> CorrectionResult:
        """
        Attempt to correct a single value.
        
        Args:
            value: Value to correct
            fingerprint: Fingerprint from good data (for learning patterns)
            subtype: Data subtype for specific rules
            column_name: Column name for context
            **kwargs: Additional corrector-specific parameters
            
        Returns:
            CorrectionResult with corrected value and metadata
        """
        pass
    
    def correct_batch(
        self,
        values: List[Any],
        fingerprint: Optional[Dict[str, Any]] = None,
        subtype: Optional[str] = None,
        column_name: Optional[str] = None,
        indices: Optional[List[int]] = None,
        **kwargs
    ) -> List[CorrectionResult]:
        """
        Correct multiple values.
        
        Args:
            values: List of values to correct
            fingerprint: Fingerprint from good data
            subtype: Data subtype
            column_name: Column name
            indices: Optional row indices for tracking
            **kwargs: Additional parameters
            
        Returns:
            List of CorrectionResult
        """
        results = []
        for i, value in enumerate(values):
            idx = indices[i] if indices else i
            result = self.correct(
                value=value,
                fingerprint=fingerprint,
                subtype=subtype,
                column_name=column_name,
                **kwargs
            )
            result.row_index = idx
            results.append(result)
        return results
    
    def can_correct(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]] = None,
        subtype: Optional[str] = None,
    ) -> Tuple[bool, float]:
        """
        Check if a value can potentially be corrected.
        Useful for LLM promotion blocking.
        
        Args:
            value: Value to check
            fingerprint: Fingerprint from good data
            subtype: Data subtype
            
        Returns:
            Tuple of (can_correct, confidence)
        """
        # Default: try correction and check result
        try:
            result = self.correct(value, fingerprint, subtype)
            return result.is_usable, result.confidence
        except Exception:
            return False, 0.0
    
    def learn_from_fingerprint(
        self,
        fingerprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract learnable patterns from fingerprint.
        Override in subclasses for specific learning logic.
        
        Args:
            fingerprint: Fingerprint from good data
            
        Returns:
            Dictionary of learned patterns/rules
        """
        return fingerprint or {}
    
    def supports_subtype(self, subtype: str) -> bool:
        """Check if this corrector supports a subtype"""
        return subtype in self.supported_subtypes or subtype == "generic"
