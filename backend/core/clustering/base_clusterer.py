"""
Base Clusterer
Abstract base class for all clustering strategies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """
    Result of a clustering operation.
    Contains good/bad data split and fingerprint for correction.
    """
    good_data: List[Any]
    bad_data: List[Any]
    good_indices: List[int]
    bad_indices: List[int]
    fingerprint: Dict[str, Any]
    method: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_count(self) -> int:
        return len(self.good_data) + len(self.bad_data)
    
    @property
    def good_ratio(self) -> float:
        if self.total_count == 0:
            return 0.0
        return len(self.good_data) / self.total_count


class BaseClusterer(ABC):
    """
    Abstract base class for clustering strategies.
    
    All clusterers must implement the cluster() method which takes
    raw data and returns a ClusteringResult with good/bad split.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize clusterer with optional configuration.
        
        Args:
            config: Strategy-specific configuration
        """
        self.config = config or {}
        self._name = self.__class__.__name__
    
    @property
    def name(self) -> str:
        """Return the name of this clusterer."""
        return self._name
    
    @abstractmethod
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster data into good and bad groups.
        
        Args:
            data: Raw column data to cluster
            indices: Optional row indices for tracking
            column_name: Column name for context
            **kwargs: Additional clusterer-specific parameters
            
        Returns:
            ClusteringResult with good/bad split and fingerprint
        """
        pass
    
    def _prepare_indices(
        self, 
        data: List[Any], 
        indices: Optional[List[int]] = None
    ) -> List[int]:
        """Prepare indices list, creating default if not provided."""
        if indices is None:
            return list(range(len(data)))
        return indices
    
    def _split_by_mask(
        self,
        data: List[Any],
        indices: List[int],
        good_mask: np.ndarray
    ) -> Tuple[List[Any], List[Any], List[int], List[int]]:
        """
        Split data and indices by boolean mask.
        
        Args:
            data: Raw data list
            indices: Index list
            good_mask: Boolean array where True = good
            
        Returns:
            Tuple of (good_data, bad_data, good_indices, bad_indices)
        """
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if i < len(good_mask) and good_mask[i]:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        return good_data, bad_data, good_indices, bad_indices
    
    def _calculate_confidence(
        self,
        good_count: int,
        total_count: int
    ) -> float:
        """Calculate clustering confidence based on good ratio."""
        if total_count == 0:
            return 0.0
        ratio = good_count / total_count
        # Penalize extreme ratios (all good or all bad might indicate issues)
        if ratio > 0.95 or ratio < 0.05:
            return 0.7
        return 0.9
