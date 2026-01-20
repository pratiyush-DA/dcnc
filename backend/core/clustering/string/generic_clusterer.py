"""
Generic String Clusterer
Production-grade frequency-based fuzzy matching for anomaly detection

Key Principles (from DataCorrectionTool):
- Frequent values = Reference (likely correct)
- Infrequent values with high similarity to reference = Typos (BAD)
- Infrequent values with low similarity = Anomalies (BAD)
- Conservative classification: when in doubt, mark as BAD
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter
import numpy as np

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz not installed. Install with: pip install rapidfuzz")

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)

# Reserved/placeholder words that should be flagged as bad
RESERVED_WORDS = {
    "invalid", "unknown", "test", "null", "n/a", "na", "none",
    "tbd", "undefined", "blank", "empty", "xxx", "abc", "asdf",
    "user", "admin", "guest", "default", "temp", "testing",
}


class GenericStringClusterer(BaseClusterer):
    """
    Production-grade clusterer for unknown/generic string data.
    
    Uses frequency-based fuzzy matching:
    1. Build reference from frequent values (appear >= min_frequency times)
    2. Score each value against reference using RapidFuzz
    3. Exact matches = GOOD
    4. High similarity (typos) = BAD (for correction)
    5. Low similarity + structural anomaly = BAD
    
    This approach ensures BAD data doesn't leak into GOOD cluster.
    """
    
    # Default configuration
    DEFAULT_SIMILARITY_THRESHOLD = 85  # RapidFuzz score threshold
    DEFAULT_MIN_FREQUENCY_RATIO = 0.1  # 10% of data or min 2
    DEFAULT_MIN_FREQUENCY_ABSOLUTE = 2  # At least 2 occurrences
    DEFAULT_TOP_N_REFERENCE = 10       # Max reference values to consider
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.similarity_threshold = config.get("similarity_threshold", self.DEFAULT_SIMILARITY_THRESHOLD) if config else self.DEFAULT_SIMILARITY_THRESHOLD
        self.min_frequency_ratio = config.get("min_frequency_ratio", self.DEFAULT_MIN_FREQUENCY_RATIO) if config else self.DEFAULT_MIN_FREQUENCY_RATIO
        self.min_frequency_absolute = config.get("min_frequency_absolute", self.DEFAULT_MIN_FREQUENCY_ABSOLUTE) if config else self.DEFAULT_MIN_FREQUENCY_ABSOLUTE
        self.top_n_reference = config.get("top_n_reference", self.DEFAULT_TOP_N_REFERENCE) if config else self.DEFAULT_TOP_N_REFERENCE
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster string data using frequency-based fuzzy matching.
        
        Algorithm:
        1. Build frequency table
        2. Identify reference values (frequent ones)
        3. Score each value against reference
        4. Classify based on similarity + structural checks
        """
        indices = self._prepare_indices(data, indices)
        
        # Separate valid strings from nulls
        valid_data = []
        valid_indices = []
        null_indices = []
        
        for i, (value, idx) in enumerate(zip(data, indices)):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                null_indices.append((i, idx, value))
            else:
                valid_data.append(str(value).strip())
                valid_indices.append((i, idx, str(value).strip()))
        
        # Handle edge cases
        if len(valid_data) == 0:
            return self._empty_result(null_indices, column_name)
        
        if len(valid_data) == 1:
            # Single value - consider it good
            return self._single_value_result(valid_data, valid_indices, null_indices, column_name)
        
        # STEP 1: Build frequency table
        value_counts = Counter(valid_data)
        
        # STEP 2: Identify reference values
        reference_values = self._build_reference_set(value_counts, len(valid_data))
        
        # STEP 3: Create fingerprint from reference
        fingerprint = self._create_fingerprint(
            valid_data, reference_values, value_counts, column_name
        )
        
        # STEP 4: Classify each value
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        classification_details = []
        
        for i, idx, value in valid_indices:
            classification = self._classify_value(value, reference_values, fingerprint)
            classification_details.append(classification)
            
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
        
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="frequency_fuzzy_matching",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "reference_count": len(reference_values),
                "reference_values": list(reference_values)[:10],
                "similarity_threshold": self.similarity_threshold,
                "classification_summary": self._summarize_classifications(classification_details),
            }
        )
    
    def _build_reference_set(
        self, 
        value_counts: Counter, 
        total_count: int
    ) -> Set[str]:
        """
        Build reference set from frequent values.
        
        Reference values are assumed to be correct (appear frequently).
        """
        # Calculate dynamic minimum frequency
        min_freq = max(
            self.min_frequency_absolute,
            int(total_count * self.min_frequency_ratio)
        )
        
        # Get values meeting minimum frequency
        frequent_values = [
            val for val, count in value_counts.items()
            if count >= min_freq
        ]
        
        # If no values meet threshold, use top N most frequent
        if not frequent_values:
            sorted_items = value_counts.most_common(self.top_n_reference)
            frequent_values = [val for val, count in sorted_items]
            logger.debug(f"No values meet min_freq={min_freq}, using top {len(frequent_values)}")
        
        # Limit to top N
        if len(frequent_values) > self.top_n_reference:
            # Sort by frequency and take top N
            frequent_values = [
                val for val, _ in value_counts.most_common(self.top_n_reference)
                if val in frequent_values
            ][:self.top_n_reference]
        
        return set(frequent_values)
    
    def _classify_value(
        self, 
        value: str, 
        reference_values: Set[str],
        fingerprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify a single value as good or bad.
        
        Classification logic:
        1. Gibberish/reserved word = BAD
        2. Exact match to reference = GOOD
        3. High similarity (>=threshold) to reference = BAD (typo)
        4. Low similarity + structural OK = Potential GOOD
        5. Low similarity + structural BAD = BAD (anomaly)
        """
        result = {
            "value": value,
            "is_good": False,
            "reason": "",
            "similarity_score": 0,
            "matched_reference": None,
        }
        
        # Check 0: Gibberish or reserved word detection
        if self._is_gibberish_or_reserved(value):
            result["reason"] = "gibberish_or_reserved"
            return result
        
        # Check 1: Exact match to reference
        if value in reference_values:
            result["is_good"] = True
            result["reason"] = "exact_reference_match"
            result["similarity_score"] = 100
            result["matched_reference"] = value
            return result
        
        # Check 2: Fuzzy match to reference
        if RAPIDFUZZ_AVAILABLE and reference_values:
            best_match = process.extractOne(
                value,
                list(reference_values),
                scorer=fuzz.ratio
            )
            
            if best_match:
                result["similarity_score"] = best_match[1]
                result["matched_reference"] = best_match[0]
                
                if best_match[1] >= self.similarity_threshold:
                    # High similarity but not exact = likely typo = BAD
                    result["is_good"] = False
                    result["reason"] = f"typo_of_{best_match[0]}"
                    return result
        
        # Check 3: Structural analysis for values with low similarity
        structural_check = self._check_structural_validity(value, fingerprint)
        
        if not structural_check["is_valid"]:
            result["is_good"] = False
            result["reason"] = f"structural_anomaly:{structural_check['reason']}"
            return result
        
        # Check 4: For values not matching reference, be conservative
        # If similarity to any reference is below a minimum threshold, likely a typo/variant
        # that we should flag for review/correction
        min_similarity_for_good = 60  # Minimum similarity to consider as valid variant
        
        if result["similarity_score"] < min_similarity_for_good:
            # Very low similarity to all reference values = suspicious
            # Could be a valid new value OR a typo of something not in reference
            # Be conservative and mark as BAD for correction
            result["is_good"] = False
            result["reason"] = f"low_similarity_to_reference"
            return result
        
        # Check 5: Moderate similarity (60-84%) - might be valid variant
        # Only accept if pattern score is very high
        pattern_score = self._calculate_pattern_match_score(value, fingerprint)
        
        if pattern_score >= 0.9:
            result["is_good"] = True
            result["reason"] = "pattern_match_with_moderate_similarity"
            return result
        
        # Default: Be conservative, mark as BAD
        result["is_good"] = False
        result["reason"] = "no_reference_match"
        return result
    
    def _check_structural_validity(
        self, 
        value: str, 
        fingerprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if value has valid structure based on fingerprint.
        """
        result = {"is_valid": True, "reason": ""}
        props = fingerprint.get("properties", {})
        
        # 1. Length check (3 sigma rule)
        mean_len = props.get("avg_length", len(value))
        std_len = props.get("length_std", 5)
        if std_len > 0 and abs(len(value) - mean_len) > 3 * std_len:
            result["is_valid"] = False
            result["reason"] = "length_outlier"
            return result
        
        # 2. Minimum length check
        min_len = props.get("min_length", 1)
        if len(value) < max(2, min_len - 2):  # Allow some tolerance
            # Exception for known abbreviations
            if value.upper() not in {"TX", "CA", "NY", "UK", "US", "FL", "PA"}:
                result["is_valid"] = False
                result["reason"] = "too_short"
                return result
        
        # 3. Case consistency check
        dominant_case = props.get("case_style", "mixed")
        if dominant_case == "title" and not value.istitle() and not value.isupper():
            # Title case expected but not found
            # Only flag if it's lowercase (typos often have wrong case)
            if value.islower() and len(value) > 2:
                result["is_valid"] = False
                result["reason"] = "case_mismatch"
                return result
        
        # 4. Character composition check
        alpha_ratio = sum(c.isalpha() for c in value) / max(len(value), 1)
        expected_alpha = props.get("avg_alpha_ratio", 0.9)
        if alpha_ratio < expected_alpha - 0.3:  # 30% tolerance
            result["is_valid"] = False
            result["reason"] = "low_alpha_ratio"
            return result
        
        # 5. Garbage detection (all same chars, random patterns)
        if len(set(value.lower())) <= 2 and len(value) > 3:
            result["is_valid"] = False
            result["reason"] = "low_entropy"
            return result
        
        return result
    
    def _is_gibberish_or_reserved(self, value: str) -> bool:
        """
        Detect gibberish, placeholder, or reserved word values.
        
        Flags:
        - Reserved words (invalid, unknown, test, null, etc.)
        - Low alpha ratio
        - Contains mostly digits (for name-like columns)
        - All same character
        """
        value_lower = value.lower().strip()
        
        # Check reserved words
        if value_lower in RESERVED_WORDS:
            return True
        
        # Check if it looks like an email address (for name columns)
        # ANY value with @ is likely not a name
        if "@" in value:
            return True
        
        # Check for email-like patterns (e.g., "bobgmailcom" - missing @ and .)
        email_domains = ["gmail", "yahoo", "hotmail", "outlook", "email", "mail", "test"]
        for domain in email_domains:
            if domain in value_lower and len(value) > 6:
                return True
        
        # Check if it's mostly digits (not for ID columns)
        digit_ratio = sum(c.isdigit() for c in value) / max(len(value), 1)
        if digit_ratio > 0.6 and len(value) > 2:
            return True
        
        # Check low alpha ratio
        alpha_ratio = sum(c.isalpha() for c in value) / max(len(value), 1)
        if alpha_ratio < 0.5 and len(value) > 2:
            return True
        
        # Check all same character
        if len(set(value.replace(" ", "").lower())) <= 1 and len(value) > 1:
            return True
        
        # Check very short with special characters
        if len(value) <= 2 and not value.isalpha():
            if value.upper() not in {"TX", "CA", "NY", "UK", "US", "FL", "PA", "OH", "IT", "HR"}:
                return True
        
        return False
    
    def _calculate_pattern_match_score(
        self, 
        value: str, 
        fingerprint: Dict[str, Any]
    ) -> float:
        """
        Calculate how well a value matches the fingerprint pattern.
        Returns score 0.0 to 1.0.
        """
        scores = []
        props = fingerprint.get("properties", {})
        
        # 1. Length similarity
        mean_len = props.get("avg_length", len(value))
        std_len = max(props.get("length_std", 1), 1)
        length_z = abs(len(value) - mean_len) / std_len
        scores.append(max(0, 1 - length_z / 3))
        
        # 2. Word count similarity
        word_count = len(value.split())
        avg_words = props.get("avg_word_count", 1)
        if avg_words > 0:
            word_ratio = min(word_count, avg_words) / max(word_count, avg_words)
            scores.append(word_ratio)
        
        # 3. Case pattern match
        case_style = props.get("case_style", "mixed")
        if case_style == "title" and value.istitle():
            scores.append(1.0)
        elif case_style == "upper" and value.isupper():
            scores.append(1.0)
        elif case_style == "lower" and value.islower():
            scores.append(1.0)
        elif case_style == "mixed":
            scores.append(0.8)
        else:
            scores.append(0.5)
        
        # 4. Alpha ratio similarity
        alpha_ratio = sum(c.isalpha() for c in value) / max(len(value), 1)
        expected_alpha = props.get("avg_alpha_ratio", 0.9)
        alpha_diff = abs(alpha_ratio - expected_alpha)
        scores.append(max(0, 1 - alpha_diff * 2))
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _create_fingerprint(
        self,
        values: List[str],
        reference_values: Set[str],
        value_counts: Counter,
        column_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create detailed fingerprint for the data.
        """
        if not values:
            return self._empty_fingerprint()
        
        str_values = [str(v) for v in values]
        lengths = [len(v) for v in str_values]
        word_counts = [len(v.split()) for v in str_values]
        
        # Detect dominant case style
        case_votes = {"upper": 0, "lower": 0, "title": 0, "mixed": 0}
        for v in str_values:
            if v.isupper():
                case_votes["upper"] += 1
            elif v.islower():
                case_votes["lower"] += 1
            elif v.istitle():
                case_votes["title"] += 1
            else:
                case_votes["mixed"] += 1
        
        dominant_case = max(case_votes, key=case_votes.get)
        case_consistency = case_votes[dominant_case] / len(str_values) if str_values else 0
        
        # Character composition
        alpha_ratios = [
            sum(c.isalpha() for c in v) / max(len(v), 1) 
            for v in str_values
        ]
        
        # Common patterns (for correction hints)
        common_prefixes = self._extract_common_affixes(list(reference_values), "prefix")
        common_suffixes = self._extract_common_affixes(list(reference_values), "suffix")
        
        return {
            "workflow": "string",
            "method": "frequency_fuzzy",
            "column_name": column_name,
            "sample_size": len(values),
            
            # Reference values (for correction)
            "reference_values": list(reference_values),
            "reference_frequencies": {
                v: value_counts.get(v, 0) for v in list(reference_values)[:10]
            },
            
            # Thresholds used
            "similarity_threshold": self.similarity_threshold,
            "min_frequency": max(
                self.min_frequency_absolute,
                int(len(values) * self.min_frequency_ratio)
            ),
            
            # Statistical properties
            "properties": {
                "avg_length": sum(lengths) / len(lengths) if lengths else 0,
                "length_std": float(np.std(lengths)) if lengths else 0,
                "min_length": min(lengths) if lengths else 0,
                "max_length": max(lengths) if lengths else 0,
                "avg_word_count": sum(word_counts) / len(word_counts) if word_counts else 0,
                "case_style": dominant_case,
                "case_consistency": case_consistency,
                "avg_alpha_ratio": sum(alpha_ratios) / len(alpha_ratios) if alpha_ratios else 0,
                "unique_count": len(set(str_values)),
                "common_prefixes": common_prefixes[:5],
                "common_suffixes": common_suffixes[:5],
            },
        }
    
    def _extract_common_affixes(
        self, 
        values: List[str], 
        affix_type: str,
        min_length: int = 2,
        max_length: int = 4
    ) -> List[str]:
        """
        Extract common prefixes or suffixes from values.
        """
        if not values:
            return []
        
        affix_counter = Counter()
        
        for value in values:
            if len(value) < min_length:
                continue
            
            for length in range(min_length, min(max_length + 1, len(value) + 1)):
                if affix_type == "prefix":
                    affix = value[:length]
                else:
                    affix = value[-length:]
                affix_counter[affix] += 1
        
        # Return affixes that appear in multiple values
        common = [
            affix for affix, count in affix_counter.most_common(10)
            if count >= 2
        ]
        
        return common
    
    def _summarize_classifications(
        self, 
        classifications: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Summarize classification reasons.
        """
        reason_counts = Counter(c["reason"] for c in classifications)
        return dict(reason_counts.most_common())
    
    def _empty_result(
        self, 
        null_indices: List[Tuple], 
        column_name: Optional[str]
    ) -> ClusteringResult:
        """
        Return result for empty/all-null data.
        """
        return ClusteringResult(
            good_data=[],
            bad_data=[n[2] for n in null_indices],
            good_indices=[],
            bad_indices=[n[1] for n in null_indices],
            fingerprint=self._empty_fingerprint(),
            method="frequency_fuzzy_empty",
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
        """
        Return result for single value.
        """
        return ClusteringResult(
            good_data=valid_data,
            bad_data=[n[2] for n in null_indices],
            good_indices=[v[1] for v in valid_indices],
            bad_indices=[n[1] for n in null_indices],
            fingerprint=self._create_fingerprint(valid_data, set(valid_data), Counter(valid_data), column_name),
            method="frequency_fuzzy_single",
            confidence=0.8,
            metadata={"column_name": column_name, "reason": "single_value"}
        )
    
    def _empty_fingerprint(self) -> Dict[str, Any]:
        """
        Return empty fingerprint structure.
        """
        return {
            "workflow": "string",
            "method": "frequency_fuzzy",
            "properties": {},
            "reference_values": [],
        }
