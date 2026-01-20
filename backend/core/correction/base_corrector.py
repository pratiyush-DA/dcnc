"""
Base Corrector
Abstract base class for all correction engines
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..interfaces import ICorrector, CorrectionResult, CorrectionStatus
from ..registry import register_corrector

logger = logging.getLogger(__name__)


class BaseCorrector(ICorrector):
    """
    Base class for all correction engines.
    
    Provides:
    - Common correction interface
    - Fingerprint learning integration
    - Correction caching
    - Batch correction support
    """
    
    def __init__(self):
        self._correction_cache: Dict[str, CorrectionResult] = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    @abstractmethod
    def supported_subtypes(self) -> List[str]:
        pass
    
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
        # Check cache
        cache_key = self._get_cache_key(value, subtype)
        if cache_key in self._correction_cache:
            cached = self._correction_cache[cache_key]
            logger.debug(f"Cache hit for correction: {value}")
            return cached
        
        # Skip null/empty values
        if value is None or str(value).strip() == "":
            return CorrectionResult(
                original_value=value,
                corrected_value=value,
                status=CorrectionStatus.SKIPPED,
                confidence=0.0,
            )
        
        # Learn from fingerprint
        learned_patterns = {}
        if fingerprint:
            learned_patterns = self.learn_from_fingerprint(fingerprint)
        
        # Perform correction
        result = self._correct_value(
            value=value,
            fingerprint=fingerprint,
            learned_patterns=learned_patterns,
            subtype=subtype,
            column_name=column_name,
            **kwargs
        )
        
        # Cache result
        self._correction_cache[cache_key] = result
        
        return result
    
    @abstractmethod
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """
        Perform actual correction logic.
        Override in subclasses.
        
        Args:
            value: Value to correct
            fingerprint: Fingerprint from good data
            learned_patterns: Patterns learned from fingerprint
            subtype: Data subtype
            column_name: Column name
            **kwargs: Additional parameters
            
        Returns:
            CorrectionResult
        """
        pass
    
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
        return fingerprint.get("properties", {})
    
    def _get_cache_key(self, value: Any, subtype: Optional[str]) -> str:
        """Generate cache key for a value"""
        return f"{subtype or 'generic'}:{value}"
    
    def clear_cache(self):
        """Clear correction cache"""
        self._correction_cache.clear()
    
    def supports_subtype(self, subtype: str) -> bool:
        """Check if this corrector supports a subtype"""
        return subtype in self.supported_subtypes or subtype == "generic"
    
    def _make_corrected_result(
        self,
        original: Any,
        corrected: Any,
        changes: List[str],
        confidence: float = 1.0
    ) -> CorrectionResult:
        """Helper to create a corrected result"""
        return CorrectionResult(
            original_value=original,
            corrected_value=corrected,
            status=CorrectionStatus.CORRECTED,
            confidence=confidence,
            changes_made=changes,
        )
    
    def _make_unchanged_result(self, value: Any) -> CorrectionResult:
        """Helper to create an unchanged result"""
        return CorrectionResult(
            original_value=value,
            corrected_value=value,
            status=CorrectionStatus.UNCHANGED,
            confidence=1.0,
        )
    
    def _make_rejected_result(
        self,
        value: Any,
        reason: str = "uncorrectable"
    ) -> CorrectionResult:
        """Helper to create a rejected result"""
        return CorrectionResult(
            original_value=value,
            corrected_value=value,
            status=CorrectionStatus.REJECTED,
            confidence=0.0,
            details={"reason": reason},
        )
