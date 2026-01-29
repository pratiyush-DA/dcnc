"""
Confidence Scorer
Calculates calibrated confidence scores for detection and clustering results.

Production-ready confidence scoring with:
- Sample size adjustment
- Data quality adjustment
- Pattern strength consideration
- Calibrated confidence ranges
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import DetectionResult

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculates calibrated confidence scores.
    
    Features:
    - Adjusts for sample size
    - Adjusts for data quality (null ratio, variance)
    - Considers pattern match strength
    - Provides calibrated confidence ranges
    """
    
    # Confidence calibration parameters
    MIN_SAMPLE_SIZE_FOR_FULL_CONFIDENCE = 100
    NULL_RATIO_PENALTY = 0.3  # Penalty per 10% null ratio
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0
    
    def __init__(
        self,
        min_sample_size: int = None,
        null_ratio_penalty: float = None
    ):
        """
        Initialize confidence scorer.
        
        Args:
            min_sample_size: Minimum sample size for full confidence (default: 100)
            null_ratio_penalty: Penalty factor for null ratio (default: 0.3)
        """
        self.min_sample_size = min_sample_size or self.MIN_SAMPLE_SIZE_FOR_FULL_CONFIDENCE
        self.null_ratio_penalty = null_ratio_penalty or self.NULL_RATIO_PENALTY
    
    def calculate_detection_confidence(
        self,
        detection_result: DetectionResult,
        sample_data: List[Any],
        sample_size: Optional[int] = None
    ) -> float:
        """
        Calculate calibrated confidence for detection result.
        
        Args:
            detection_result: Detection result
            sample_data: Sample data used for detection
            sample_size: Optional explicit sample size (if None, uses len(sample_data))
            
        Returns:
            Calibrated confidence score (0.0 - 1.0)
        """
        base_confidence = detection_result.confidence
        sample_size = sample_size or len(sample_data)
        
        # Adjust for sample size
        sample_factor = min(1.0, sample_size / self.min_sample_size)
        
        # Adjust for data quality (null ratio)
        null_count = sum(1 for v in sample_data if v is None)
        null_ratio = null_count / len(sample_data) if sample_data else 0.0
        quality_factor = 1.0 - (null_ratio * self.null_ratio_penalty)
        
        # Adjust for pattern strength (if available)
        pattern_strength = 1.0
        if detection_result.details:
            match_ratio = detection_result.details.get("match_ratio", 1.0)
            pattern_strength = match_ratio
        
        # Calibrated confidence
        calibrated = (
            base_confidence *
            sample_factor *
            quality_factor *
            pattern_strength
        )
        
        # Clamp to valid range
        calibrated = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, calibrated))
        
        logger.debug(
            f"Confidence calibration: base={base_confidence:.2f}, "
            f"sample_factor={sample_factor:.2f}, quality_factor={quality_factor:.2f}, "
            f"pattern_strength={pattern_strength:.2f}, calibrated={calibrated:.2f}"
        )
        
        return calibrated
    
    def calculate_clustering_confidence(
        self,
        good_count: int,
        bad_count: int,
        total_count: Optional[int] = None,
        sample_size: Optional[int] = None,
        data_quality: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate calibrated confidence for clustering result.
        
        Args:
            good_count: Number of good values
            bad_count: Number of bad values
            total_count: Total count (if None, uses good_count + bad_count)
            sample_size: Sample size used for clustering
            data_quality: Optional data quality metrics (null_ratio, variance, etc.)
            
        Returns:
            Calibrated confidence score (0.0 - 1.0)
        """
        total = total_count or (good_count + bad_count)
        
        if total == 0:
            return 0.0
        
        # Base confidence from good ratio
        base_confidence = good_count / total
        
        # Adjust for sample size
        sample_factor = 1.0
        if sample_size:
            sample_factor = min(1.0, sample_size / self.min_sample_size)
        
        # Adjust for data quality
        quality_factor = 1.0
        if data_quality:
            null_ratio = data_quality.get("null_ratio", 0.0)
            quality_factor = 1.0 - (null_ratio * self.null_ratio_penalty)
        
        # Penalize extreme ratios (all good or all bad might indicate issues)
        if base_confidence > 0.95:
            # Very high good ratio - might be too lenient
            base_confidence *= 0.9
        elif base_confidence < 0.05:
            # Very low good ratio - might be too strict
            base_confidence = 0.3  # Minimum confidence for very low ratios
        
        # Calibrated confidence
        calibrated = base_confidence * sample_factor * quality_factor
        
        # Clamp to valid range
        calibrated = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, calibrated))
        
        return calibrated
    
    def get_confidence_level(self, confidence: float) -> str:
        """
        Get human-readable confidence level.
        
        Args:
            confidence: Confidence score (0.0 - 1.0)
            
        Returns:
            Confidence level string (very_low, low, medium, high, very_high)
        """
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"
    
    def should_trust_result(self, confidence: float, threshold: float = 0.7) -> bool:
        """
        Determine if result should be trusted based on confidence.
        
        Args:
            confidence: Confidence score
            threshold: Minimum confidence threshold (default: 0.7)
            
        Returns:
            True if confidence >= threshold
        """
        return confidence >= threshold
