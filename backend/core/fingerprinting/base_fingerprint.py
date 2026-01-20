"""
Base Fingerprint Generator
Abstract base class for all fingerprint generators
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from collections import Counter
import statistics

from ..interfaces import IFingerprint, FingerprintData
from ..registry import register_fingerprint


class BaseFingerprint(IFingerprint):
    """
    Base class for all fingerprint generators.
    
    Fingerprints capture the "ideal" characteristics of good data:
    - Pattern signatures
    - Statistical properties
    - Common formats/structures
    
    Correctors use fingerprints to learn how to fix bad data.
    """
    
    @property
    @abstractmethod
    def workflow_type(self) -> str:
        """Workflow type this fingerprint handles"""
        pass
    
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
        if not data:
            return FingerprintData(
                workflow=self.workflow_type,
                subtype=subtype,
                confidence=0.0,
            )
        
        # Calculate base statistics
        non_null_data = [d for d in data if d is not None and str(d).strip()]
        
        fingerprint = FingerprintData(
            workflow=self.workflow_type,
            subtype=subtype,
            sample_size=len(non_null_data),
            unique_ratio=len(set(non_null_data)) / len(non_null_data) if non_null_data else 0,
            null_ratio=1 - (len(non_null_data) / len(data)) if data else 0,
        )
        
        # Get common values
        if non_null_data:
            value_counts = Counter(non_null_data)
            fingerprint.common_values = [v for v, _ in value_counts.most_common(10)]
        
        # Generate type-specific properties
        fingerprint.properties = self._generate_properties(non_null_data, subtype)
        
        # Generate patterns
        fingerprint.patterns = self._generate_patterns(non_null_data)
        
        # Generate signature
        fingerprint.pattern_signature = self._generate_signature(non_null_data)
        
        # Calculate confidence
        fingerprint.confidence = self._calculate_confidence(fingerprint)
        
        return fingerprint
    
    @abstractmethod
    def _generate_properties(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """
        Generate type-specific fingerprint properties.
        Override in subclasses.
        
        Args:
            data: Non-null data samples
            subtype: Data subtype
            
        Returns:
            Dictionary of properties
        """
        pass
    
    def _generate_patterns(self, data: List[Any]) -> List[str]:
        """
        Generate list of patterns found in data.
        Override in subclasses for specific pattern detection.
        
        Args:
            data: Non-null data samples
            
        Returns:
            List of pattern strings
        """
        return []
    
    def _generate_signature(self, data: List[Any]) -> Optional[str]:
        """
        Generate a single representative signature for the data.
        Override in subclasses.
        
        Args:
            data: Non-null data samples
            
        Returns:
            Signature string or None
        """
        return None
    
    def _calculate_confidence(self, fingerprint: FingerprintData) -> float:
        """
        Calculate confidence in the fingerprint.
        
        Args:
            fingerprint: Generated fingerprint
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence on sample size
        if fingerprint.sample_size == 0:
            return 0.0
        
        if fingerprint.sample_size < 5:
            return 0.3
        elif fingerprint.sample_size < 20:
            return 0.6
        elif fingerprint.sample_size < 100:
            return 0.8
        else:
            return 0.95
    
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
        hints = {
            "target_pattern": fingerprint.pattern_signature,
            "common_values": fingerprint.common_values[:5],
            "properties": fingerprint.properties,
        }
        
        return hints
    
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
        # Default implementation
        if value in fingerprint.common_values:
            return 1.0
        
        return 0.5
    
    @staticmethod
    def safe_mean(values: List[float]) -> float:
        """Calculate mean safely"""
        if not values:
            return 0.0
        return statistics.mean(values)
    
    @staticmethod
    def safe_stdev(values: List[float]) -> float:
        """Calculate standard deviation safely"""
        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)
    
    @staticmethod
    def safe_median(values: List[float]) -> float:
        """Calculate median safely"""
        if not values:
            return 0.0
        return statistics.median(values)
