"""
Categorical String Clusterer
Production-grade clusterer for categorical/repetitive string data

Uses frequency-based fuzzy matching (adapted from SmartDataCorrectionEngine):
- Frequency analysis to identify reference values
- RapidFuzz similarity scoring 
- Column profiling for auto-configuration
- Anomaly validation

Best for: Country, State, City, Category, Status, and similar categorical columns
"""

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter
import numpy as np

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    warnings.warn("rapidfuzz not installed. Install with: pip install rapidfuzz")

from ..base_clusterer import BaseClusterer, ClusteringResult

# Try to import rules config - handle gracefully if not available
try:
    from backend.config.rules_config import get_rules_config
except ImportError:
    # Fallback: create a simple dummy config
    def get_rules_config(*args, **kwargs):
        class DummyConfig:
            def get_workflow_rules(self, *args, **kwargs):
                return {}
        return DummyConfig()

logger = logging.getLogger(__name__)


class CategoricalStringClusterer(BaseClusterer):
    """
    Clusterer for categorical string data with repeating values.
    
    Designed for columns like:
    - Country, State, City
    - Category, Status, Type
    - Any column with limited unique values (high repetition)
    
    Algorithm:
    1. Profile column to detect if categorical
    2. Build reference set from frequent values
    3. Score each value against reference using fuzzy matching
    4. Classify based on similarity thresholds
    
    Features:
    - Case sensitivity enforcement
    - Gibberish/placeholder detection
    - Format consistency
    - Detailed fingerprinting for correction
    """
    
    # Default thresholds
    DEFAULT_SIMILARITY_THRESHOLD = 85
    DEFAULT_MIN_FREQUENCY = 2
    DEFAULT_CARDINALITY_THRESHOLD = 0.3  # < 30% unique = categorical
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Load rules from configuration
        self._rules_config = get_rules_config()
        
        # Override defaults from config
        if config:
            self.similarity_threshold = config.get(
                "similarity_threshold", self.DEFAULT_SIMILARITY_THRESHOLD
            )
            self.min_frequency = config.get(
                "min_frequency", self.DEFAULT_MIN_FREQUENCY
            )
            self.cardinality_threshold = config.get(
                "cardinality_threshold", self.DEFAULT_CARDINALITY_THRESHOLD
            )
        else:
            self.similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD
            self.min_frequency = self.DEFAULT_MIN_FREQUENCY
            self.cardinality_threshold = self.DEFAULT_CARDINALITY_THRESHOLD
        
        # History tracking
        self.validation_history: List[Dict] = []
        self.correction_history: List[Dict] = []
    
    @property
    def name(self) -> str:
        return "CategoricalStringClusterer"
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        reference_values: Optional[List[str]] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster categorical string data.
        
        Args:
            data: List of values to cluster
            indices: Optional row indices
            column_name: Column name for rule lookup
            reference_values: Optional pre-defined reference values
            
        Returns:
            ClusteringResult with good/bad separation and fingerprint
        """
        indices = self._prepare_indices(data, indices)
        
        # Get subtype-specific rules
        subtype = kwargs.get("subtype", "generic")
        rules = self._rules_config.get_workflow_rules("text", subtype)
        
        # Prepare values
        valid_data = []
        valid_indices = []
        null_indices = []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                null_indices.append((i, idx, value))
            else:
                clean_value = str(value).strip()
                valid_data.append(clean_value)
                valid_indices.append((i, idx, clean_value))
        
        # Handle edge cases
        if len(valid_data) == 0:
            return self._empty_result(null_indices, column_name)
        
        if len(valid_data) == 1:
            return self._single_value_result(valid_data, valid_indices, null_indices, column_name)
        
        # Profile the column
        profile = self._profile_column(valid_data, rules)
        
        # Build reference set
        if reference_values:
            reference_set = set(str(v).strip() for v in reference_values)
        else:
            reference_set = self._build_reference_set(valid_data, profile)
        
        # Create fingerprint
        fingerprint = self._create_fingerprint(
            valid_data, reference_set, profile, column_name, rules
        )
        
        # Classify each value
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        classifications = []
        
        for i, idx, value in valid_indices:
            classification = self._classify_value(
                value, reference_set, fingerprint, rules
            )
            classifications.append(classification)
            
            if classification["is_good"]:
                good_data.append(value)
                good_indices.append(idx)
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Add nulls to bad
        for i, idx, value in null_indices:
            bad_data.append(value)
            bad_indices.append(idx)
        
        confidence = self._calculate_confidence(profile, len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="categorical_frequency_fuzzy",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "is_categorical": profile.get("is_categorical", True),
                "cardinality": profile.get("cardinality", 0),
                "reference_count": len(reference_set),
                "classification_summary": self._summarize_classifications(classifications),
            }
        )
    
    def _profile_column(
        self, 
        values: List[str],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Profile the column to determine characteristics.
        """
        value_counts = Counter(values)
        unique_count = len(value_counts)
        total_count = len(values)
        cardinality = unique_count / max(total_count, 1)
        
        # Case analysis
        case_votes = {"upper": 0, "lower": 0, "title": 0, "mixed": 0}
        for v in values:
            if v.isupper():
                case_votes["upper"] += 1
            elif v.islower():
                case_votes["lower"] += 1
            elif v.istitle():
                case_votes["title"] += 1
            else:
                case_votes["mixed"] += 1
        
        dominant_case = max(case_votes, key=case_votes.get)
        case_consistency = case_votes[dominant_case] / total_count if total_count > 0 else 0
        
        # Length statistics
        lengths = [len(v) for v in values]
        
        return {
            "total_count": total_count,
            "unique_count": unique_count,
            "cardinality": cardinality,
            "is_categorical": cardinality < self.cardinality_threshold,
            "value_counts": value_counts,
            "dominant_case": dominant_case,
            "case_consistency": case_consistency,
            "case_votes": case_votes,
            "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            "std_length": float(np.std(lengths)) if len(lengths) > 1 else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
        }
    
    def _build_reference_set(
        self, 
        values: List[str], 
        profile: Dict[str, Any]
    ) -> Set[str]:
        """
        Build reference set from frequent values.
        
        Enhanced with:
        1. Cardinality-aware thresholds (relax for high cardinality)
        2. Typo filtering (remove values too similar to other references)
        """
        value_counts = profile.get("value_counts", Counter(values))
        total = len(values)
        cardinality = profile.get("cardinality", 0)
        
        # Cardinality-aware minimum frequency
        if cardinality > 0.7:
            # Very high cardinality - likely not truly categorical
            # Accept top values but be more lenient
            min_freq = 1
            logger.debug(f"High cardinality {cardinality:.2f}, using min_freq=1")
        elif cardinality > 0.4:
            # Medium cardinality - relaxed threshold
            min_freq = max(1, int(total * 0.03))  # 3% threshold
        else:
            # Low cardinality - strict (current behavior)
            min_freq = max(
                self.min_frequency,
                int(total * 0.05)  # At least 5% of data
            )
        
        # Get values meeting minimum frequency
        frequent_values = [
            val for val, count in value_counts.items()
            if count >= min_freq
        ]
        
        # If no values meet threshold, use top N
        if not frequent_values:
            top_n = min(10, len(value_counts))
            frequent_values = [v for v, _ in value_counts.most_common(top_n)]
            logger.debug(f"No values meet min_freq={min_freq}, using top {len(frequent_values)}")
        
        # Filter out typos from reference set
        # If two values are 80-99% similar, keep only the more frequent one
        reference_set = self._filter_typos_from_reference(frequent_values, value_counts)
        
        return reference_set
    
    def _filter_typos_from_reference(
        self, 
        candidates: List[str], 
        value_counts: Counter
    ) -> Set[str]:
        """
        Filter typos from reference candidates.
        
        If two values are 80-99% similar (but not exact), 
        keep only the more frequent one.
        """
        if not RAPIDFUZZ_AVAILABLE or len(candidates) < 2:
            return set(candidates)
        
        # Sort by frequency (most frequent first)
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: value_counts.get(x, 0), 
            reverse=True
        )
        
        final_reference = set()
        
        for candidate in sorted_candidates:
            is_likely_typo = False
            
            for ref in final_reference:
                if candidate.lower() == ref.lower():
                    # Exact match (case insensitive) - could be case variant
                    # Keep more frequent one (already in reference)
                    is_likely_typo = True
                    break
                
                similarity = fuzz.ratio(candidate.lower(), ref.lower())
                
                if 80 <= similarity < 100:
                    # Too similar but not exact = likely typo
                    # Keep the more frequent one (already in final_reference)
                    logger.debug(
                        f"Filtering '{candidate}' as typo of '{ref}' "
                        f"(similarity={similarity}%)"
                    )
                    is_likely_typo = True
                    break
            
            if not is_likely_typo:
                final_reference.add(candidate)
        
        return final_reference
    
    def _classify_value(
        self,
        value: str,
        reference_set: Set[str],
        fingerprint: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify a single value as good or bad.
        """
        result = {
            "value": value,
            "is_good": False,
            "reason": "",
            "similarity_score": 0,
            "matched_reference": None,
        }
        
        # Check 1: Gibberish/Reserved words
        if self._is_gibberish(value, rules):
            result["reason"] = "gibberish_or_reserved"
            return result
        
        # Check 2: Exact match to reference
        if value in reference_set:
            result["is_good"] = True
            result["reason"] = "exact_reference_match"
            result["similarity_score"] = 100
            result["matched_reference"] = value
            return result
        
        # Check 3: Case-normalized match
        case_rule = rules.get("case_sensitivity", {})
        if case_rule.get("enabled", False):
            strategy = case_rule.get("strategy", "majority")
            expected_case = fingerprint.get("properties", {}).get("case_style", "mixed")
            
            # Check if value matches expected case
            if not self._matches_case(value, expected_case, strategy):
                # Check if lowercase version is in reference
                for ref in reference_set:
                    if value.lower() == ref.lower():
                        result["reason"] = f"case_mismatch_to_{ref}"
                        result["matched_reference"] = ref
                        result["similarity_score"] = 95
                        return result
        
        # Check 4: Fuzzy match
        if RAPIDFUZZ_AVAILABLE and reference_set:
            best_match = process.extractOne(
                value,
                list(reference_set),
                scorer=fuzz.ratio
            )
            
            if best_match:
                result["similarity_score"] = best_match[1]
                result["matched_reference"] = best_match[0]
                
                if best_match[1] >= self.similarity_threshold:
                    # High similarity = likely typo = BAD
                    result["reason"] = f"typo_of_{best_match[0]}"
                    return result
        
        # Check 5: Low similarity - be conservative
        min_similarity = rules.get("frequency_analysis", {}).get("min_similarity_for_good", 60)
        
        if result["similarity_score"] < min_similarity:
            result["reason"] = "low_similarity_to_reference"
            return result
        
        # Default: mark as BAD for review
        result["reason"] = "no_reference_match"
        return result
    
    def _is_gibberish(self, value: str, rules: Dict[str, Any]) -> bool:
        """
        Detect gibberish or placeholder values.
        """
        gibberish_rules = rules.get("gibberish_detection", {})
        if not gibberish_rules.get("enabled", True):
            return False
        
        value_lower = value.lower().strip()
        
        # Reserved words check
        reserved_words = gibberish_rules.get("reserved_words", [])
        if value_lower in [w.lower() for w in reserved_words]:
            return True
        
        # Alpha ratio check
        min_alpha = gibberish_rules.get("min_alpha_ratio", 0.7)
        alpha_ratio = sum(c.isalpha() for c in value) / max(len(value), 1)
        if alpha_ratio < min_alpha:
            return True
        
        # Length check
        min_length = gibberish_rules.get("min_length", 2)
        if len(value.strip()) < min_length:
            return True
        
        # Digit check (optional, for names)
        if gibberish_rules.get("reject_with_digits", False):
            if any(c.isdigit() for c in value):
                return True
        
        return False
    
    def _matches_case(self, value: str, expected_case: str, strategy: str) -> bool:
        """
        Check if value matches expected case pattern.
        """
        if strategy == "preserve" or expected_case == "mixed":
            return True
        
        if expected_case == "title":
            return value.istitle() or value.isupper()
        elif expected_case == "upper":
            return value.isupper()
        elif expected_case == "lower":
            return value.islower()
        
        return True
    
    def _create_fingerprint(
        self,
        values: List[str],
        reference_set: Set[str],
        profile: Dict[str, Any],
        column_name: Optional[str],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create detailed fingerprint for correction and audit.
        """
        return {
            "workflow": "string",
            "method": "categorical_frequency_fuzzy",
            "column_name": column_name,
            "sample_size": len(values),
            
            # Reference values for correction
            "reference_values": list(reference_set),
            "reference_frequencies": {
                v: profile["value_counts"].get(v, 0) 
                for v in list(reference_set)[:10]
            },
            
            # Configuration used
            "similarity_threshold": self.similarity_threshold,
            "min_frequency": self.min_frequency,
            
            # Properties for correction hints
            "properties": {
                "is_categorical": profile.get("is_categorical", True),
                "cardinality": profile.get("cardinality", 0),
                "avg_length": profile.get("avg_length", 0),
                "length_std": profile.get("std_length", 0),
                "case_style": profile.get("dominant_case", "mixed"),
                "case_consistency": profile.get("case_consistency", 0),
            },
            
            # Correction hints for downstream correction engine
            "correction_hints": {
                "expected_case": profile.get("dominant_case", "mixed"),
                "use_fuzzy_matching": True,
                "similarity_threshold": self.similarity_threshold,
            },
            
            # Rules applied (for audit)
            "rules_applied": {
                "case_sensitivity": rules.get("case_sensitivity", {}).get("enabled", False),
                "gibberish_detection": rules.get("gibberish_detection", {}).get("enabled", True),
                "frequency_analysis": rules.get("frequency_analysis", {}).get("enabled", True),
            },
        }
    
    def _summarize_classifications(
        self, 
        classifications: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Summarize classification reasons.
        """
        reason_counts = Counter(c["reason"] for c in classifications)
        return dict(reason_counts.most_common())
    
    def _calculate_confidence(
        self, 
        profile: Dict[str, Any],
        good_count: int,
        total_count: int
    ) -> float:
        """
        Calculate confidence score.
        """
        if total_count == 0:
            return 0.0
        
        base_confidence = 0.7
        
        # Boost for categorical data
        if profile.get("is_categorical"):
            base_confidence += 0.1
        
        # Boost for high case consistency
        if profile.get("case_consistency", 0) > 0.8:
            base_confidence += 0.1
        
        # Penalty for high cardinality
        if profile.get("cardinality", 0) > 0.5:
            base_confidence -= 0.1
        
        return min(1.0, max(0.0, base_confidence))
    
    def _empty_result(
        self, 
        null_indices: List[Tuple],
        column_name: Optional[str]
    ) -> ClusteringResult:
        """Return result for empty data."""
        return ClusteringResult(
            good_data=[],
            bad_data=[n[2] for n in null_indices],
            good_indices=[],
            bad_indices=[n[1] for n in null_indices],
            fingerprint={"workflow": "string", "method": "categorical_empty"},
            method="categorical_empty",
            confidence=0.0,
            metadata={"column_name": column_name, "reason": "no_valid_data"}
        )
    
    def _single_value_result(
        self,
        valid_data: List[str],
        valid_indices: List[Tuple],
        null_indices: List[Tuple],
        column_name: Optional[str]
    ) -> ClusteringResult:
        """Return result for single value."""
        return ClusteringResult(
            good_data=valid_data,
            bad_data=[n[2] for n in null_indices],
            good_indices=[v[1] for v in valid_indices],
            bad_indices=[n[1] for n in null_indices],
            fingerprint={
                "workflow": "string",
                "method": "categorical_single",
                "reference_values": valid_data,
            },
            method="categorical_single",
            confidence=0.8,
            metadata={"column_name": column_name, "reason": "single_value"}
        )
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_anomaly_detection(
        self,
        good_data: List[str],
        bad_data: List[str],
        threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate anomaly detection results by checking if bad data
        can be corrected to good data using fuzzy matching.
        
        Use this to verify your anomaly detector is working correctly.
        
        Args:
            good_data: List of values considered correct
            bad_data: List of values flagged as anomalies
            threshold: Similarity threshold
            
        Returns:
            Validation report with accuracy and false positive candidates
        """
        threshold = threshold or self.similarity_threshold
        
        report = {
            "total_bad_data": len(bad_data),
            "correctable": [],
            "uncorrectable": [],
            "false_positive_candidates": [],
            "validation_accuracy": 0.0,
            "avg_similarity": 0.0
        }
        
        if not bad_data:
            return report
        
        similarities = []
        
        for bad_value in bad_data:
            if not RAPIDFUZZ_AVAILABLE:
                break
                
            match = process.extractOne(bad_value, good_data, scorer=fuzz.ratio)
            
            if match and match[1] >= threshold:
                report["correctable"].append({
                    "original": bad_value,
                    "suggested_correction": match[0],
                    "similarity": match[1]
                })
                similarities.append(match[1])
            else:
                report["uncorrectable"].append(bad_value)
                
                if not match or match[1] < 60:
                    report["false_positive_candidates"].append({
                        "value": bad_value,
                        "best_match": match[0] if match else None,
                        "similarity": match[1] if match else 0,
                        "reason": "Very low similarity to any good value"
                    })
                similarities.append(match[1] if match else 0)
        
        if bad_data:
            report["validation_accuracy"] = (len(report["correctable"]) / len(bad_data)) * 100
        report["avg_similarity"] = float(np.mean(similarities)) if similarities else 0
        
        self.validation_history.append(report)
        return report
    
    def detect_categorical_column(self, values: List[Any]) -> bool:
        """
        Detect if a list of values represents a categorical column.
        
        Returns True if:
        - Cardinality < threshold
        - Values are strings
        - Has repeating patterns
        """
        if not values:
            return False
        
        clean_values = [str(v).strip() for v in values if v is not None]
        if not clean_values:
            return False
        
        unique_count = len(set(clean_values))
        total_count = len(clean_values)
        cardinality = unique_count / total_count
        
        return cardinality < self.cardinality_threshold and unique_count < 1000
