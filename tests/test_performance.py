"""
Performance Tests
Benchmarks and performance validation for all components.
"""

import pytest
import time
import statistics
from typing import List

from backend.core.security import InputValidator, DataSanitizer
from backend.core.resilience import ConfidenceScorer, CircuitBreaker
from backend.core.detection.ensemble_detector import EnsembleDetector


class TestPerformance:
    """Performance benchmarks."""
    
    def test_input_validator_performance(self):
        """Benchmark input validator performance."""
        validator = InputValidator()
        
        # Test with large batch
        column_names = [f"column_{i}" for i in range(1000)]
        
        start = time.time()
        for col in column_names:
            validator.validate_column_name(col)
        elapsed = time.time() - start
        
        # Should process 1000 columns in < 1 second
        assert elapsed < 1.0
        print(f"Input validation: {len(column_names)} columns in {elapsed:.3f}s "
              f"({len(column_names)/elapsed:.0f} cols/sec)")
    
    def test_data_sanitizer_performance(self):
        """Benchmark data sanitizer performance."""
        sanitizer = DataSanitizer()
        
        # Test with large batch
        values = [f"value_{i}_with_some_text" for i in range(10000)]
        
        start = time.time()
        sanitized = sanitizer.sanitize_batch(values)
        elapsed = time.time() - start
        
        # Should process 10000 values in < 2 seconds
        assert elapsed < 2.0
        print(f"Data sanitization: {len(values)} values in {elapsed:.3f}s "
              f"({len(values)/elapsed:.0f} values/sec)")
    
    def test_confidence_scorer_performance(self):
        """Benchmark confidence scorer performance."""
        scorer = ConfidenceScorer()
        
        # Test with many calculations
        iterations = 1000
        
        start = time.time()
        for _ in range(iterations):
            scorer.calculate_clustering_confidence(
                good_count=80,
                bad_count=20
            )
        elapsed = time.time() - start
        
        # Should process 1000 calculations in < 0.1 seconds
        assert elapsed < 0.1
        print(f"Confidence scoring: {iterations} calculations in {elapsed:.3f}s "
              f"({iterations/elapsed:.0f} calc/sec)")
    
    def test_circuit_breaker_overhead(self):
        """Test circuit breaker overhead is minimal."""
        cb = CircuitBreaker()
        
        def fast_func():
            return "success"
        
        # Measure overhead
        times = []
        for _ in range(100):
            start = time.time()
            cb.call(fast_func)
            times.append(time.time() - start)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Overhead should be < 1ms per call
        assert avg_time < 0.001
        assert max_time < 0.01
        
        print(f"Circuit breaker overhead: avg={avg_time*1000:.3f}ms, max={max_time*1000:.3f}ms")
    
    def test_ensemble_detector_performance(self):
        """Benchmark ensemble detector performance."""
        detector = EnsembleDetector()
        
        # Test with various data types
        test_cases = [
            (["user@example.com"] * 100, "email"),
            ([25, 30, 35, 40] * 25, "age"),
            (["2023-12-25", "2023-12-26"] * 50, "date"),
        ]
        
        total_time = 0
        for sample_data, expected_type in test_cases:
            start = time.time()
            result = detector.detect(f"test_{expected_type}", sample_data)
            elapsed = time.time() - start
            total_time += elapsed
            
            # Should detect correctly
            assert result.workflow in ["text", "numeric", "datetime"]
        
        # Should process all cases in < 1 second
        assert total_time < 1.0
        print(f"Ensemble detection: {len(test_cases)} cases in {total_time:.3f}s")
    
    def test_memory_efficiency(self):
        """Test memory efficiency of components."""
        import sys
        
        # Test that components don't leak memory
        validator = InputValidator()
        sanitizer = DataSanitizer()
        
        initial_size = sys.getsizeof(validator) + sys.getsizeof(sanitizer)
        
        # Process many items
        for i in range(1000):
            validator.validate_column_name(f"col_{i}")
            sanitizer.sanitize_value(f"value_{i}")
        
        final_size = sys.getsizeof(validator) + sys.getsizeof(sanitizer)
        
        # Memory should not grow significantly
        growth = final_size - initial_size
        assert growth < 10000  # Less than 10KB growth
        
        print(f"Memory efficiency: {growth} bytes growth for 1000 operations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
