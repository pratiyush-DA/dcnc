"""
Detector Interface
Base interface for column type detection (heuristics + pattern-based, NO LLM)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class DetectionSource(str, Enum):
    """Source of detection result"""
    CACHE = "cache"           # From SQLite cache
    HEURISTIC = "heuristic"   # From heuristic rules
    PATTERN = "pattern"       # From content pattern analysis
    DEFAULT = "default"       # Default fallback


@dataclass
class DetectionResult:
    """
    Result of column type detection.
    """
    # Detected type information
    workflow: str
    subtype: str
    
    # Confidence in detection (0.0 to 1.0)
    confidence: float = 0.0
    
    # How was this detected
    source: DetectionSource = DetectionSource.DEFAULT
    
    # Matching rule/pattern that triggered detection
    matched_rule: Optional[str] = None
    
    # Additional detection metadata
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Whether this should be cached
    cacheable: bool = True
    
    @property
    def is_generic(self) -> bool:
        """Check if detection fell back to generic"""
        return self.subtype == "generic"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "workflow": self.workflow,
            "subtype": self.subtype,
            "confidence": self.confidence,
            "source": self.source.value,
            "matched_rule": self.matched_rule,
            "details": self.details,
        }


class IDetector(ABC):
    """
    Abstract base class for column type detectors.
    
    Detection uses ONLY:
    1. Cache lookup (SQLite)
    2. Heuristic rules (column name matching)
    3. Content pattern analysis
    
    NO LLM is used in detection.
    """
    
    @abstractmethod
    def detect(
        self,
        column_name: str,
        sample_data: List[Any],
        use_cache: bool = True
    ) -> DetectionResult:
        """
        Detect column type using heuristics and pattern analysis.
        
        Detection flow:
        1. Check cache for exact column name match
        2. Apply heuristic rules (priority-ordered)
        3. Analyze content patterns
        4. Fall back to generic if nothing matches
        
        Args:
            column_name: Name of the column
            sample_data: Sample of column data for pattern analysis
            use_cache: Whether to check cache first
            
        Returns:
            DetectionResult with workflow and subtype
        """
        pass
    
    @abstractmethod
    def detect_from_content(
        self,
        sample_data: List[Any]
    ) -> DetectionResult:
        """
        Detect type purely from content (for headerless files).
        
        Args:
            sample_data: Data samples to analyze
            
        Returns:
            DetectionResult based on content patterns
        """
        pass
    
    @abstractmethod
    def cache_result(
        self,
        column_name: str,
        result: DetectionResult
    ) -> None:
        """
        Cache a detection result for future use.
        
        Args:
            column_name: Column name to cache
            result: Detection result to cache
        """
        pass
    
    @abstractmethod
    def get_cached(
        self,
        column_name: str
    ) -> Optional[DetectionResult]:
        """
        Get cached detection result.
        
        Args:
            column_name: Column name to look up
            
        Returns:
            Cached result or None
        """
        pass
    
    def detect_batch(
        self,
        columns: Dict[str, List[Any]]
    ) -> Dict[str, DetectionResult]:
        """
        Detect types for multiple columns.
        
        Args:
            columns: Dictionary of column_name -> sample_data
            
        Returns:
            Dictionary of column_name -> DetectionResult
        """
        results = {}
        for col_name, sample_data in columns.items():
            results[col_name] = self.detect(col_name, sample_data)
        return results
    
    def clear_cache(self) -> None:
        """Clear the detection cache"""
        pass
