"""
Test Suite for Ensemble Detector
Tests for ensemble detection system.
"""

import pytest

from backend.core.detection.ensemble_detector import EnsembleDetector, StatisticalAnalyzer
from backend.core.interfaces import DetectionResult


class TestStatisticalAnalyzer:
    """Tests for StatisticalAnalyzer."""
    
    def test_analyze_numeric_age_like(self):
        """Test analysis of age-like numeric data."""
        analyzer = StatisticalAnalyzer()
        
        data = [25, 30, 35, 40, 45, 50] * 10  # Age-like values
        
        result = analyzer.analyze(data)
        
        assert result is not None
        assert result["type"] == "numeric"
        assert result["likely_type"] == "age"
        assert result["confidence"] > 0.5
    
    def test_analyze_numeric_rating_like(self):
        """Test analysis of rating-like numeric data."""
        analyzer = StatisticalAnalyzer()
        
        data = [1, 2, 3, 4, 5, 4, 5, 3, 4, 5] * 10  # Rating-like values
        
        result = analyzer.analyze(data)
        
        assert result is not None
        assert result["type"] == "numeric"
        assert result["likely_type"] == "rating"
    
    def test_analyze_string_data(self):
        """Test analysis of string data."""
        analyzer = StatisticalAnalyzer()
        
        data = ["test", "value", "string", "data"] * 10
        
        result = analyzer.analyze(data)
        
        assert result is not None
        assert result["type"] == "string"
        assert result["likely_type"] == "generic"


class TestEnsembleDetector:
    """Tests for EnsembleDetector."""
    
    def test_detect_with_pattern_match(self):
        """Test detection with strong pattern match."""
        detector = EnsembleDetector()
        
        # Email-like data
        sample_data = [
            "user@example.com",
            "test@domain.org",
            "admin@site.com"
        ]
        
        result = detector.detect("user_email", sample_data)
        
        assert result.workflow == "text"
        assert result.subtype == "email"
        assert result.confidence > 0.5
    
    def test_detect_with_heuristic_match(self):
        """Test detection with heuristic match."""
        detector = EnsembleDetector()
        
        # Generic data but column name suggests email
        sample_data = ["some", "random", "text"]
        
        result = detector.detect("user_email", sample_data)
        
        # Should use heuristic (email in column name)
        assert result.workflow == "text"
        assert result.subtype == "email"
    
    def test_detect_with_statistical_analysis(self):
        """Test detection with statistical analysis."""
        detector = EnsembleDetector(enable_statistical=True)
        
        # Age-like numeric data
        sample_data = [25, 30, 35, 40, 45, 50, 55, 60]
        
        result = detector.detect("age_column", sample_data)
        
        # Should detect as numeric/age
        assert result.workflow == "numeric"
        assert result.subtype == "age"
    
    def test_detect_fallback_to_generic(self):
        """Test fallback to generic when no methods match."""
        detector = EnsembleDetector(enable_statistical=False)
        
        # Completely ambiguous data
        sample_data = ["xyz", "abc", "123", "mixed"]
        
        result = detector.detect("unknown_column", sample_data)
        
        # Should fall back to generic
        assert result.workflow == "text"
        assert result.subtype == "generic"
        assert result.confidence < 0.5
    
    def test_weighted_voting(self):
        """Test weighted voting mechanism."""
        detector = EnsembleDetector()
        
        # Data that could match multiple types
        sample_data = ["2023-12-25", "2023-12-26", "2023-12-27"]
        
        result = detector.detect("date_column", sample_data)
        
        # Should use weighted voting
        assert result.workflow in ["text", "datetime"]
        assert result.details.get("ensemble") is True
        assert result.details.get("methods_used", 0) > 0
    
    def test_context_aware_detection(self):
        """Test context-aware detection."""
        detector = EnsembleDetector(enable_context=True)
        
        # Column that's part of a name group
        sample_data = ["John", "Jane", "Bob"]
        context_columns = {
            "first_name": ["John", "Jane"],
            "last_name": ["Doe", "Smith"]
        }
        
        result = detector.detect("full_name", sample_data, context_columns)
        
        # Should use context to detect as name
        assert result.workflow == "text"
        assert result.subtype == "name"
