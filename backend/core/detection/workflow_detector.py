"""
Workflow Detector
Main detection class using CONTENT-FIRST + heuristics (NO LLM)

Detection Philosophy:
1. ALWAYS analyze content patterns FIRST
2. Use heuristics only when content is ambiguous
3. Fall back to generic when nothing matches
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IDetector, DetectionResult, DetectionSource
from .detection_cache import DetectionCache
from .heuristic_matcher import HeuristicMatcher
from .pattern_analyzer import PatternAnalyzer

logger = logging.getLogger(__name__)


class WorkflowDetector(IDetector):
    """
    Column type detector using CONTENT-FIRST + heuristic analysis.
    
    Detection Flow (NO LLM):
    1. Check cache for exact column name match
    2. **ANALYZE CONTENT PATTERNS FIRST** (email, IP, date, etc.)
    3. If no strong pattern match, apply heuristic rules
    4. Fall back to generic if nothing matches
    
    This order ensures that:
    - "ip_login" column with IP addresses → detected as IP (not username)
    - "last_login" column with datetimes → detected as datetime (not text)
    """
    
    def __init__(
        self,
        cache_path: Optional[str] = None,
        enable_cache: bool = True
    ):
        """
        Initialize detector.
        
        Args:
            cache_path: Path to SQLite cache database
            enable_cache: Whether to use caching
        """
        self._cache = DetectionCache(cache_path) if enable_cache else None
        self._heuristic_matcher = HeuristicMatcher()
        self._pattern_analyzer = PatternAnalyzer()
        
        logger.info("WorkflowDetector initialized (CONTENT-FIRST, NO LLM)")
    
    def detect(
        self,
        column_name: str,
        sample_data: List[Any],
        use_cache: bool = True
    ) -> DetectionResult:
        """
        Detect column type using content-first + heuristic analysis.
        
        Args:
            column_name: Name of the column
            sample_data: Sample of column data for pattern analysis
            use_cache: Whether to check cache first
            
        Returns:
            DetectionResult with workflow and subtype
        """
        logger.debug(f"Detecting type for column: {column_name}")
        
        # Step 1: Check cache
        if use_cache and self._cache:
            cached = self.get_cached(column_name)
            if cached:
                logger.debug(f"Cache hit: {column_name} → {cached.workflow}/{cached.subtype}")
                return cached
        
        # Step 2: **CONTENT PATTERNS FIRST** (critical for accuracy)
        pattern_result = None
        if sample_data:
            pattern_result = self._pattern_analyzer.analyze(sample_data)
            # Only use pattern result for SPECIFIC subtypes (not generic)
            # Generic subtypes should fall through to heuristics for more specific matching
            if pattern_result and pattern_result.get("confidence", 0) >= 0.6:
                if pattern_result.get("subtype") not in ("generic", "generic_numeric", "generic_string"):
                    result = DetectionResult(
                        workflow=pattern_result["workflow"],
                        subtype=pattern_result["subtype"],
                        confidence=pattern_result.get("confidence", 0.8),
                        source=DetectionSource.PATTERN,
                        matched_rule=pattern_result.get("pattern_name"),
                        details={"match_ratio": pattern_result.get("match_ratio", 0)},
                    )
                    logger.debug(
                        f"Content pattern match: {column_name} → "
                        f"{result.workflow}/{result.subtype} "
                        f"(pattern: {result.matched_rule}, confidence: {result.confidence:.2f})"
                    )
                    
                    # Cache the result
                    if self._cache:
                        self.cache_result(column_name, result)
                    
                    return result
        
        # Step 3: Apply heuristic rules (for ambiguous content or generic patterns)
        heuristic_result = self._heuristic_matcher.match(column_name)
        if heuristic_result:
            result = DetectionResult(
                workflow=heuristic_result["workflow"],
                subtype=heuristic_result["subtype"],
                confidence=heuristic_result.get("confidence", 0.9),
                source=DetectionSource.HEURISTIC,
                matched_rule=heuristic_result.get("rule_name"),
            )
            logger.debug(
                f"Heuristic match: {column_name} → "
                f"{result.workflow}/{result.subtype} (rule: {result.matched_rule})"
            )
            
            # Cache the result
            if self._cache:
                self.cache_result(column_name, result)
            
            return result
        
        # Step 4: Fall back to generic (use pattern result if available)
        if pattern_result:
            result = DetectionResult(
                workflow=pattern_result["workflow"],
                subtype=pattern_result["subtype"],
                confidence=pattern_result.get("confidence", 0.5),
                source=DetectionSource.PATTERN,
                matched_rule=pattern_result.get("pattern_name"),
            )
        else:
            result = self._detect_generic_type(sample_data)
        logger.debug(f"Generic fallback: {column_name} → {result.workflow}/{result.subtype}")
        
        return result
    
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
        if not sample_data:
            return self._get_default_result()
        
        # Try pattern analysis
        pattern_result = self._pattern_analyzer.analyze(sample_data)
        if pattern_result:
            return DetectionResult(
                workflow=pattern_result["workflow"],
                subtype=pattern_result["subtype"],
                confidence=pattern_result.get("confidence", 0.8),
                source=DetectionSource.PATTERN,
                matched_rule=pattern_result.get("pattern_name"),
            )
        
        # Fall back to generic
        return self._detect_generic_type(sample_data)
    
    def _detect_generic_type(self, sample_data: List[Any]) -> DetectionResult:
        """Detect generic type based on data characteristics"""
        if not sample_data:
            return self._get_default_result()
        
        # Filter non-null values
        non_null = [v for v in sample_data if v is not None and str(v).strip()]
        
        if not non_null:
            return self._get_default_result()
        
        # Check if mostly numeric (handle currency/European decimals)
        numeric_count = 0
        for v in non_null:
            str_v = str(v).strip()
            # Clean for numeric parsing
            clean = str_v.replace("$", "").replace("€", "").replace("£", "")
            clean = clean.replace(",", "")
            try:
                float(clean)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        if numeric_count / len(non_null) > 0.8:
            return DetectionResult(
                workflow="numeric",
                subtype="generic_numeric",
                confidence=0.7,
                source=DetectionSource.DEFAULT,
            )

        # === Alphanumeric Code Detection ===
        # Check for "Code-like" columns (low alpha ratio)
        # e.g. "05431", "B8037" -> low alpha (likely IDs)
        # vs "Miami", "John Doe" -> high alpha (freetext)
        
        low_alpha_count = 0
        total_valid = 0
        
        for v in non_null:
            s = str(v).strip()
            if not s: continue
            
            total_valid += 1
            # Count letters
            alpha_count = sum(c.isalpha() for c in s)
            ratio = alpha_count / len(s)
            
            # If less than 50% letters, it's likely a code/ID/number
            if ratio < 0.5:
                low_alpha_count += 1
                
        if total_valid > 0:
            low_alpha_ratio = low_alpha_count / total_valid
            
            # User Requirement: If > 70% valid data has low alpha ratio
            if low_alpha_ratio > 0.7:
                 logger.debug(f"Column {column_name if 'column_name' in locals() else 'unknown'} detected as IDENTIFIER via density check (Low Alpha Ratio: {low_alpha_ratio:.2f})")
                 return DetectionResult(
                    workflow="identifier",
                    subtype="pattern_id",
                    confidence=0.6,
                    source=DetectionSource.DEFAULT,
                )
        
        # Default to text/generic
        return DetectionResult(
            workflow="text",
            subtype="generic",
            confidence=0.5,
            source=DetectionSource.DEFAULT,
        )
    
    def _get_default_result(self) -> DetectionResult:
        """Get default detection result"""
        return DetectionResult(
            workflow="text",
            subtype="generic",
            confidence=0.3,
            source=DetectionSource.DEFAULT,
        )
    
    def cache_result(
        self,
        column_name: str,
        result: DetectionResult
    ) -> None:
        """Cache detection result"""
        if self._cache and result.cacheable:
            self._cache.save(column_name, result)
    
    def get_cached(
        self,
        column_name: str
    ) -> Optional[DetectionResult]:
        """Get cached detection result"""
        if self._cache:
            return self._cache.get(column_name)
        return None
    
    def clear_cache(self) -> None:
        """Clear the detection cache"""
        if self._cache:
            self._cache.clear()
