"""
Test Suite for Resilience Components
Tests for graceful degradation, circuit breaker, and confidence scoring.
"""

import pytest
import time
from unittest.mock import Mock, patch

from backend.core.resilience import (
    GracefulDegradationHandler,
    CircuitBreaker,
    ConfidenceScorer
)
from backend.core.exceptions import CircuitBreakerOpenError
from backend.core.interfaces import DetectionResult, DetectionSource


class TestGracefulDegradationHandler:
    """Tests for GracefulDegradationHandler."""
    
    def test_process_with_fallback_success(self):
        """Test successful primary method execution."""
        handler = GracefulDegradationHandler()
        
        def primary():
            return "success"
        
        result = handler.process_with_fallback(primary, [])
        assert result == "success"
    
    def test_process_with_fallback_with_retry(self):
        """Test retry on failure."""
        handler = GracefulDegradationHandler(max_retries=3)
        
        call_count = [0]
        
        def primary():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = handler.process_with_fallback(primary, [])
        assert result == "success"
        assert call_count[0] == 2
    
    def test_process_with_fallback_uses_fallback(self):
        """Test fallback method usage."""
        handler = GracefulDegradationHandler(max_retries=1)
        
        def primary():
            raise ValueError("Primary failed")
        
        def fallback1():
            raise ValueError("Fallback 1 failed")
        
        def fallback2():
            return "fallback2_success"
        
        result = handler.process_with_fallback(primary, [fallback1, fallback2])
        assert result == "fallback2_success"
    
    def test_process_with_fallback_all_fail(self):
        """Test when all methods fail."""
        handler = GracefulDegradationHandler(max_retries=1)
        
        def primary():
            raise ValueError("Primary failed")
        
        def fallback():
            raise ValueError("Fallback failed")
        
        with pytest.raises(RuntimeError) as exc_info:
            handler.process_with_fallback(primary, [fallback])
        
        assert "All methods failed" in str(exc_info.value)
    
    def test_safe_cluster_basic(self):
        """Test safe clustering with basic fallback."""
        handler = GracefulDegradationHandler()
        
        # Mock clusterer that fails
        mock_clusterer = Mock()
        mock_clusterer.cluster.side_effect = ValueError("Clustering failed")
        
        data = ["value1", "value2", None, "value3"]
        indices = [0, 1, 2, 3]
        
        result = handler.safe_cluster(mock_clusterer, data, indices, "test_column")
        
        # Should use basic validation fallback
        assert result.method == "basic_fallback"
        assert len(result.good_data) == 3
        assert len(result.bad_data) == 1
        assert result.bad_data[0] is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=1)
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state.value == "closed"
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=1)
        
        def failing_func():
            raise ValueError("Failure")
        
        # Fail 3 times
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        # Circuit should be open
        assert cb.state.value == "open"
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_func)
    
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout_seconds=0.1,  # Short timeout for testing
            half_open_max_calls=2
        )
        
        def failing_func():
            raise ValueError("Failure")
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state.value == "open"
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Try successful call (should transition to half-open)
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state.value == "half_open"
        
        # Another success should close circuit
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state.value == "closed"
    
    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        cb = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise ValueError("Failure")
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state.value == "open"
        
        # Reset
        cb.reset()
        assert cb.state.value == "closed"
        assert cb.failure_count == 0


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""
    
    def test_calculate_detection_confidence_basic(self):
        """Test basic detection confidence calculation."""
        scorer = ConfidenceScorer()
        
        detection_result = DetectionResult(
            workflow="text",
            subtype="email",
            confidence=0.8,
            source=DetectionSource.PATTERN
        )
        
        sample_data = ["test@example.com"] * 100  # 100 samples
        
        confidence = scorer.calculate_detection_confidence(
            detection_result,
            sample_data
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high with good sample size
    
    def test_calculate_detection_confidence_small_sample(self):
        """Test confidence adjustment for small sample size."""
        scorer = ConfidenceScorer(min_sample_size=100)
        
        detection_result = DetectionResult(
            workflow="text",
            subtype="email",
            confidence=0.8,
            source=DetectionSource.PATTERN
        )
        
        sample_data = ["test@example.com"] * 10  # Only 10 samples
        
        confidence = scorer.calculate_detection_confidence(
            detection_result,
            sample_data
        )
        
        # Should be lower due to small sample size
        assert confidence < 0.8
    
    def test_calculate_detection_confidence_null_penalty(self):
        """Test confidence penalty for high null ratio."""
        scorer = ConfidenceScorer()
        
        detection_result = DetectionResult(
            workflow="text",
            subtype="email",
            confidence=0.8,
            source=DetectionSource.PATTERN
        )
        
        # 50% null values
        sample_data = ["test@example.com"] * 50 + [None] * 50
        
        confidence = scorer.calculate_detection_confidence(
            detection_result,
            sample_data
        )
        
        # Should be lower due to null penalty
        assert confidence < 0.8
    
    def test_calculate_clustering_confidence_basic(self):
        """Test basic clustering confidence calculation."""
        scorer = ConfidenceScorer()
        
        confidence = scorer.calculate_clustering_confidence(
            good_count=80,
            bad_count=20
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence == pytest.approx(0.8, abs=0.1)
    
    def test_calculate_clustering_confidence_extreme_ratios(self):
        """Test confidence adjustment for extreme ratios."""
        scorer = ConfidenceScorer()
        
        # All good (might be too lenient)
        confidence_all_good = scorer.calculate_clustering_confidence(
            good_count=100,
            bad_count=0
        )
        
        # All bad (might be too strict)
        confidence_all_bad = scorer.calculate_clustering_confidence(
            good_count=0,
            bad_count=100
        )
        
        # Extreme ratios should be penalized
        assert confidence_all_good < 1.0
        assert confidence_all_bad > 0.0  # Should have minimum confidence
    
    def test_get_confidence_level(self):
        """Test confidence level categorization."""
        scorer = ConfidenceScorer()
        
        assert scorer.get_confidence_level(0.95) == "very_high"
        assert scorer.get_confidence_level(0.75) == "high"
        assert scorer.get_confidence_level(0.55) == "medium"
        assert scorer.get_confidence_level(0.35) == "low"
        assert scorer.get_confidence_level(0.15) == "very_low"
    
    def test_should_trust_result(self):
        """Test trust decision based on confidence."""
        scorer = ConfidenceScorer()
        
        assert scorer.should_trust_result(0.8, threshold=0.7) is True
        assert scorer.should_trust_result(0.6, threshold=0.7) is False
        assert scorer.should_trust_result(0.9, threshold=0.7) is True
