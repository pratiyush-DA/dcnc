"""
Ensemble Detector
Combines multiple detection methods for higher accuracy.

Production-ready ensemble detection with:
- Weighted voting from multiple methods
- Statistical analysis integration
- Context-aware detection
- Confidence aggregation
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from ..interfaces import DetectionResult, DetectionSource
from .pattern_analyzer import PatternAnalyzer
from .heuristic_matcher import HeuristicMatcher
from .workflow_detector import WorkflowDetector

logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """
    Analyzes statistical properties for detection hints.
    """
    
    def analyze(self, data: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze statistical distribution of data.
        
        Args:
            data: Sample data
            
        Returns:
            Statistical analysis result or None
        """
        import numpy as np
        
        # Filter nulls
        clean_data = [v for v in data if v is not None]
        
        if not clean_data or len(clean_data) < 3:
            return None
        
        # Try to parse as numeric
        numeric_data = []
        for v in clean_data:
            try:
                str_v = str(v).replace(",", "").replace("$", "").replace("%", "")
                numeric_data.append(float(str_v))
            except (ValueError, TypeError):
                pass
        
        if len(numeric_data) / len(clean_data) > 0.8:
            # Mostly numeric
            return self._analyze_numeric_distribution(numeric_data)
        else:
            # String data
            return self._analyze_string_distribution(clean_data)
    
    def _analyze_numeric_distribution(
        self,
        data: List[float]
    ) -> Dict[str, Any]:
        """Analyze numeric distribution."""
        import numpy as np
        
        arr = np.array(data)
        
        # Check for discrete vs continuous
        unique_ratio = len(np.unique(arr)) / len(arr)
        
        # Check range
        min_val, max_val = float(np.min(arr)), float(np.max(arr))
        range_size = max_val - min_val
        
        # Check distribution shape
        mean, median = float(np.mean(arr)), float(np.median(arr))
        std = float(np.std(arr))
        skew = (mean - median) / (std + 1e-10) if std > 0 else 0.0
        
        hints = {
            "type": "numeric",
            "is_discrete": unique_ratio < 0.1,
            "range": (min_val, max_val),
            "range_size": range_size,
            "skew": skew,
            "mean": mean,
            "median": median,
            "std": std,
        }
        
        # Type hints based on distribution
        if 0 <= min_val <= 120 and max_val <= 120 and unique_ratio < 0.1:
            hints["likely_type"] = "age"
            hints["confidence"] = 0.7
        elif 0 <= min_val <= 10 and max_val <= 10:
            hints["likely_type"] = "rating"
            hints["confidence"] = 0.7
        elif 1900 <= min_val <= 2100 and max_val <= 2100:
            hints["likely_type"] = "year"
            hints["confidence"] = 0.7
        else:
            hints["likely_type"] = "generic_numeric"
            hints["confidence"] = 0.5
        
        return hints
    
    def _analyze_string_distribution(
        self,
        data: List[str]
    ) -> Dict[str, Any]:
        """Analyze string distribution."""
        # Length statistics
        lengths = [len(str(v)) for v in data]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        
        # Character type analysis
        alpha_ratios = []
        digit_ratios = []
        for v in str(data[0]) if data else "":
            alpha_count = sum(c.isalpha() for c in v)
            digit_count = sum(c.isdigit() for c in v)
            total = len(v)
            if total > 0:
                alpha_ratios.append(alpha_count / total)
                digit_ratios.append(digit_count / total)
        
        avg_alpha_ratio = sum(alpha_ratios) / len(alpha_ratios) if alpha_ratios else 0
        avg_digit_ratio = sum(digit_ratios) / len(digit_ratios) if digit_ratios else 0
        
        return {
            "type": "string",
            "avg_length": avg_length,
            "alpha_ratio": avg_alpha_ratio,
            "digit_ratio": avg_digit_ratio,
            "likely_type": "generic",
            "confidence": 0.5,
        }


class EnsembleDetector:
    """
    Combines multiple detection methods for higher accuracy.
    
    Uses weighted voting based on confidence scores.
    """
    
    # Method weights (sum should be ~1.0)
    WEIGHTS = {
        "pattern": 0.4,  # Pattern analysis (most reliable)
        "heuristic": 0.3,  # Heuristic matching
        "statistical": 0.2,  # Statistical analysis
        "context": 0.1,  # Context-aware (if available)
    }
    
    # Minimum confidence for ensemble agreement
    MIN_AGREEMENT_CONFIDENCE = 0.6
    
    def __init__(
        self,
        enable_statistical: bool = True,
        enable_context: bool = False
    ):
        """
        Initialize ensemble detector.
        
        Args:
            enable_statistical: Enable statistical analysis
            enable_context: Enable context-aware detection (requires column context)
        """
        self._pattern_analyzer = PatternAnalyzer()
        self._heuristic_matcher = HeuristicMatcher()
        self._statistical_analyzer = StatisticalAnalyzer() if enable_statistical else None
        self.enable_context = enable_context
    
    def detect(
        self,
        column_name: str,
        sample_data: List[Any],
        context_columns: Optional[Dict[str, List[Any]]] = None
    ) -> DetectionResult:
        """
        Detect column type using ensemble of methods.
        
        Args:
            column_name: Column name
            sample_data: Sample data
            context_columns: Optional context from other columns
            
        Returns:
            DetectionResult from ensemble voting
        """
        results = []
        
        # Method 1: Pattern analysis
        try:
            pattern_result = self._pattern_analyzer.analyze(sample_data)
            if pattern_result and pattern_result.get("confidence", 0) >= 0.6:
                if pattern_result.get("subtype") not in ("generic", "generic_numeric", "generic_string"):
                    results.append({
                        "workflow": pattern_result["workflow"],
                        "subtype": pattern_result["subtype"],
                        "confidence": pattern_result.get("confidence", 0.8),
                        "weight": self.WEIGHTS["pattern"],
                        "source": "pattern",
                        "method": "pattern_analysis"
                    })
        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")
        
        # Method 2: Heuristic matching
        try:
            heuristic_result = self._heuristic_matcher.match(column_name)
            if heuristic_result:
                results.append({
                    "workflow": heuristic_result["workflow"],
                    "subtype": heuristic_result["subtype"],
                    "confidence": heuristic_result.get("confidence", 0.9),
                    "weight": self.WEIGHTS["heuristic"],
                    "source": "heuristic",
                    "method": "heuristic_matching"
                })
        except Exception as e:
            logger.warning(f"Heuristic matching failed: {e}")
        
        # Method 3: Statistical analysis
        if self._statistical_analyzer:
            try:
                stats_result = self._statistical_analyzer.analyze(sample_data)
                if stats_result and "likely_type" in stats_result:
                    # Map statistical hints to workflow/subtype
                    likely_type = stats_result["likely_type"]
                    if likely_type in ["age", "rating", "year", "salary", "amount"]:
                        workflow = "numeric"
                        subtype = likely_type
                    else:
                        workflow = "text"
                        subtype = "generic"
                    
                    results.append({
                        "workflow": workflow,
                        "subtype": subtype,
                        "confidence": stats_result.get("confidence", 0.5),
                        "weight": self.WEIGHTS["statistical"],
                        "source": "statistical",
                        "method": "statistical_analysis"
                    })
            except Exception as e:
                logger.warning(f"Statistical analysis failed: {e}")
        
        # Method 4: Context-aware (if available)
        if self.enable_context and context_columns:
            try:
                context_result = self._analyze_context(column_name, sample_data, context_columns)
                if context_result:
                    results.append({
                        "workflow": context_result["workflow"],
                        "subtype": context_result["subtype"],
                        "confidence": context_result.get("confidence", 0.6),
                        "weight": self.WEIGHTS["context"],
                        "source": "context",
                        "method": "context_analysis"
                    })
            except Exception as e:
                logger.warning(f"Context analysis failed: {e}")
        
        # If no results, fall back to generic
        if not results:
            logger.warning(f"No detection results for {column_name}, using generic fallback")
            return DetectionResult(
                workflow="text",
                subtype="generic",
                confidence=0.3,
                source=DetectionSource.DEFAULT,
                details={"ensemble": True, "methods_used": 0}
            )
        
        # Weighted voting
        return self._weighted_vote(results, column_name)
    
    def _weighted_vote(
        self,
        results: List[Dict[str, Any]],
        column_name: str
    ) -> DetectionResult:
        """
        Perform weighted voting on detection results.
        
        Args:
            results: List of detection results from different methods
            column_name: Column name (for logging)
            
        Returns:
            DetectionResult from weighted voting
        """
        # Group by workflow/subtype combination
        votes: Dict[Tuple[str, str], List[Dict]] = {}
        for result in results:
            key = (result["workflow"], result["subtype"])
            if key not in votes:
                votes[key] = []
            votes[key].append(result)
        
        # Calculate weighted scores
        scores: Dict[Tuple[str, str], float] = {}
        for key, vote_list in votes.items():
            score = sum(
                r["confidence"] * r["weight"]
                for r in vote_list
            )
            scores[key] = score
        
        # Get best match
        if not scores:
            # Fallback
            return DetectionResult(
                workflow="text",
                subtype="generic",
                confidence=0.3,
                source=DetectionSource.DEFAULT,
                details={"ensemble": True, "voting_failed": True}
            )
        
        best_key = max(scores.items(), key=lambda x: x[1])
        workflow, subtype = best_key[0]
        confidence = best_key[1]
        
        # Normalize confidence (weights sum to 1.0, so max is ~1.0)
        confidence = min(1.0, confidence)
        
        # Check if confidence meets minimum threshold
        if confidence < self.MIN_AGREEMENT_CONFIDENCE:
            logger.warning(
                f"Low ensemble confidence ({confidence:.2f}) for {column_name}, "
                f"using best match anyway"
            )
        
        # Determine source (use most confident method)
        best_result = max(
            votes[best_key[0]],
            key=lambda r: r["confidence"]
        )
        
        logger.debug(
            f"Ensemble detection for {column_name}: {workflow}/{subtype} "
            f"(confidence: {confidence:.2f}, methods: {len(results)})"
        )
        
        return DetectionResult(
            workflow=workflow,
            subtype=subtype,
            confidence=confidence,
            source=DetectionSource.PATTERN if best_result["source"] == "pattern" else DetectionSource.HEURISTIC,
            matched_rule=best_result.get("method", "ensemble"),
            details={
                "ensemble": True,
                "methods_used": len(results),
                "voting_score": confidence,
                "methods": [r["method"] for r in results]
            }
        )
    
    def _analyze_context(
        self,
        column_name: str,
        sample_data: List[Any],
        context_columns: Dict[str, List[Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze context from other columns.
        
        Args:
            column_name: Current column name
            sample_data: Current column data
            context_columns: Other columns as context
            
        Returns:
            Context-based detection result or None
        """
        # Check for common relationship patterns
        col_lower = column_name.lower()
        
        # Name relationships
        if "first_name" in context_columns and "last_name" in context_columns:
            if "name" in col_lower or "full" in col_lower:
                return {
                    "workflow": "text",
                    "subtype": "name",
                    "confidence": 0.7
                }
        
        # Location relationships
        if "city" in context_columns and "state" in context_columns:
            if "address" in col_lower or "zip" in col_lower or "postal" in col_lower:
                return {
                    "workflow": "text",
                    "subtype": "zipcode" if "zip" in col_lower or "postal" in col_lower else "address",
                    "confidence": 0.6
                }
        
        # Date relationships
        if "date" in col_lower or "time" in col_lower:
            # Check if data looks like dates
            date_like = sum(
                1 for v in sample_data[:10]
                if v and ("/" in str(v) or "-" in str(v) or ":" in str(v))
            )
            if date_like / min(10, len(sample_data)) > 0.5:
                return {
                    "workflow": "datetime",
                    "subtype": "datetime" if ":" in str(sample_data[0]) else "date",
                    "confidence": 0.6
                }
        
        return None
