"""
Graceful Degradation Handler
Handles failures gracefully with automatic fallbacks.

Production-ready graceful degradation with:
- Automatic fallback chains
- Retry logic with exponential backoff
- Safe clustering with multiple fallback levels
- Error recovery strategies
"""

import time
import logging
from typing import Any, Callable, List, Optional, TypeVar
from functools import wraps

from ..clustering.base_clusterer import BaseClusterer, ClusteringResult
from ..exceptions import DataQualityError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class GracefulDegradationHandler:
    """
    Handles failures gracefully with automatic fallbacks.
    
    Features:
    - Primary method with fallback chain
    - Retry logic with exponential backoff
    - Safe clustering with multiple fallback levels
    - Error recovery strategies
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        enable_fallbacks: bool = True
    ):
        """
        Initialize graceful degradation handler.
        
        Args:
            max_retries: Maximum retry attempts for primary method
            retry_delay: Base delay between retries (seconds)
            enable_fallbacks: Whether to use fallback methods
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_fallbacks = enable_fallbacks
    
    def process_with_fallback(
        self,
        primary_method: Callable[[], T],
        fallback_methods: List[Callable[[], T]],
        operation_name: str = "operation"
    ) -> T:
        """
        Try primary method, fall back to alternatives on failure.
        
        Args:
            primary_method: Primary method to try first
            fallback_methods: List of fallback methods to try in order
            operation_name: Name of operation (for logging)
            
        Returns:
            Result from first successful method
            
        Raises:
            RuntimeError: If all methods fail
        """
        last_error = None
        
        # Try primary method with retries
        for attempt in range(self.max_retries):
            try:
                result = primary_method()
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded on retry {attempt + 1}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
        
        # Try fallback methods if enabled
        if self.enable_fallbacks and fallback_methods:
            for i, fallback in enumerate(fallback_methods):
                try:
                    logger.info(f"Trying fallback method {i + 1} for {operation_name}")
                    return fallback()
                except Exception as e:
                    logger.warning(f"Fallback method {i + 1} failed: {e}")
                    last_error = e
        
        # All methods failed
        error_msg = f"All methods failed for {operation_name}"
        if last_error:
            error_msg += f". Last error: {last_error}"
        raise RuntimeError(error_msg) from last_error
    
    def safe_cluster(
        self,
        clusterer: BaseClusterer,
        data: List[Any],
        indices: List[int],
        column_name: str,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster with automatic fallback to simpler methods.
        
        Args:
            clusterer: Clusterer to use (can be workflow or clusterer)
            data: Data to cluster
            indices: Row indices
            column_name: Column name
            **kwargs: Additional clusterer parameters (subtype, etc.)
            
        Returns:
            ClusteringResult from first successful method
        """
        # Check if it's a workflow (has cluster_v2 method)
        is_workflow = hasattr(clusterer, 'cluster_v2')
        
        # Fallback chain
        def try_ml_clustering():
            """Try ML-based clustering."""
            if is_workflow:
                # For workflows, use cluster_v2 with use_ml=True
                return clusterer.cluster_v2(
                    data=data,
                    indices=indices,
                    column_name=column_name,
                    use_ml=True,
                    **{k: v for k, v in kwargs.items() if k != 'use_ml'}
                )
            elif hasattr(clusterer, 'cluster'):
                # For clusterers, just use cluster
                return clusterer.cluster(data, indices, column_name, **kwargs)
            raise ValueError("Clusterer does not support clustering")
        
        def try_non_ml_clustering():
            """Try non-ML clustering."""
            if is_workflow:
                # For workflows, use regular cluster method
                return clusterer.cluster(
                    data=data,
                    indices=indices,
                    column_name=column_name,
                    **{k: v for k, v in kwargs.items() if k != 'use_ml'}
                )
            elif hasattr(clusterer, 'cluster'):
                # For clusterers, just use cluster
                return clusterer.cluster(data, indices, column_name, **kwargs)
            raise ValueError("Clusterer does not support clustering")
        
        def try_basic_validation():
            """Ultimate fallback: basic null/empty check."""
            return self._basic_validation_cluster(data, indices, column_name)
        
        # Try with fallbacks
        return self.process_with_fallback(
            primary_method=try_ml_clustering,
            fallback_methods=[try_non_ml_clustering, try_basic_validation],
            operation_name=f"clustering for {column_name}"
        )
    
    def _basic_validation_cluster(
        self,
        data: List[Any],
        indices: List[int],
        column_name: str
    ) -> ClusteringResult:
        """
        Ultimate fallback: basic null/empty check.
        
        This is the most basic clustering that should always work.
        """
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for value, idx in zip(data, indices):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                bad_data.append(value)
                bad_indices.append(idx)
            else:
                good_data.append(value)
                good_indices.append(idx)
        
        total = len(good_data) + len(bad_data)
        confidence = len(good_data) / total if total > 0 else 0.0
        
        logger.warning(
            f"Using basic validation fallback for {column_name}: "
            f"{len(good_data)} good, {len(bad_data)} bad"
        )
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint={
                "workflow": "unknown",
                "method": "basic_fallback",
                "column_name": column_name,
            },
            method="basic_fallback",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "fallback_used": True,
                "reason": "All clustering methods failed, using basic validation"
            }
        )
    
    def safe_detect(
        self,
        detector,
        column_name: str,
        sample_data: List[Any]
    ):
        """
        Detect with fallback to generic type.
        
        Args:
            detector: Detector instance
            column_name: Column name
            sample_data: Sample data
            
        Returns:
            DetectionResult (always succeeds with fallback)
        """
        def try_detection():
            """Try normal detection."""
            return detector.detect(column_name, sample_data)
        
        def fallback_to_generic():
            """Fallback to generic text type."""
            from ..interfaces import DetectionResult, DetectionSource
            logger.warning(f"Detection failed for {column_name}, using generic text fallback")
            return DetectionResult(
                workflow="text",
                subtype="generic",
                confidence=0.3,
                source=DetectionSource.DEFAULT,
                details={"fallback": True}
            )
        
        return self.process_with_fallback(
            primary_method=try_detection,
            fallback_methods=[fallback_to_generic],
            operation_name=f"detection for {column_name}"
        )


def with_graceful_degradation(
    fallback_methods: List[Callable] = None,
    max_retries: int = 3
):
    """
    Decorator for automatic graceful degradation.
    
    Usage:
        @with_graceful_degradation(fallback_methods=[fallback1, fallback2])
        def my_function():
            # primary implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = GracefulDegradationHandler(max_retries=max_retries)
            
            def primary():
                return func(*args, **kwargs)
            
            return handler.process_with_fallback(
                primary_method=primary,
                fallback_methods=fallback_methods or [],
                operation_name=func.__name__
            )
        
        return wrapper
    return decorator
