"""
Dynamic Clusterer Selector Utilities
Production-grade utilities for determining optimal clusterer based on data characteristics

Adapted from SmartDataCorrectionEngine patterns.
"""

import logging
from typing import Any, List, Optional, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


def is_categorical(values: List[Any], threshold: float = 0.3, max_unique: int = 1000) -> bool:
    """
    Check if a list of values represents categorical data.
    
    Based on SmartDataCorrectionEngine._is_categorical logic:
    - Cardinality < threshold (default 30% unique)
    - Unique count < max_unique (default 1000)
    
    Args:
        values: List of values to check
        threshold: Maximum cardinality ratio for categorical (default 0.3)
        max_unique: Maximum unique values for categorical (default 1000)
        
    Returns:
        True if data appears categorical, False otherwise
        
    Example:
        >>> is_categorical(["NY", "CA", "TX", "NY", "CA", "NY"])  # True
        >>> is_categorical(["abc123", "def456", "ghi789", ...])   # False (high cardinality)
    """
    if not values:
        return False
    
    # Clean values
    clean_values = [str(v).strip() for v in values if v is not None and str(v).strip()]
    
    if not clean_values:
        return False
    
    unique_count = len(set(clean_values))
    total_count = len(clean_values)
    cardinality = unique_count / total_count
    
    result = cardinality < threshold and unique_count < max_unique
    
    logger.debug(
        f"is_categorical check: cardinality={cardinality:.2f}, "
        f"unique={unique_count}, threshold={threshold}, result={result}"
    )
    
    return result


def is_freetext(values: List[Any], min_avg_length: float = 3, min_alpha_ratio: float = 0.8) -> bool:
    """
    Check if a list of values represents free-text data.
    
    Based on SmartDataCorrectionEngine._is_text logic:
    - Average length > min_avg_length
    - Most values contain letters
    
    Args:
        values: List of values to check
        min_avg_length: Minimum average length for text
        min_alpha_ratio: Minimum ratio of values with letters
        
    Returns:
        True if data appears to be free-text
    """
    if not values:
        return False
    
    clean_values = [str(v).strip() for v in values if v is not None]
    
    if not clean_values:
        return False
    
    # Check average length
    avg_length = sum(len(v) for v in clean_values) / len(clean_values)
    
    # Check alpha ratio
    has_letters_count = sum(1 for v in clean_values if any(c.isalpha() for c in v))
    alpha_ratio = has_letters_count / len(clean_values)
    
    return avg_length > min_avg_length and alpha_ratio > min_alpha_ratio


def detect_optimal_clusterer(
    values: List[Any],
    subtype: str,
    column_name: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Dynamically determine optimal clusterer based on data characteristics.
    
    Decision flow:
    1. If subtype has validator (email, phone, etc.) -> use validator
    2. If data is categorical (cardinality < 30%) -> use categorical
    3. Otherwise -> use freetext
    
    Args:
        values: Sample of values to analyze
        subtype: Detected subtype from heuristics
        column_name: Column name for context
        
    Returns:
        Tuple of (clusterer_path, config)
    """
    # Subtypes with dedicated validators - always use them
    VALIDATOR_SUBTYPES = {
        "email", "phone", "url", "ssn", "zipcode", "boolean", "uuid", "ip_address"
    }
    
    if subtype in VALIDATOR_SUBTYPES:
        return f"string.validator", {"engine": subtype}
    
    # For semantic/categorical subtypes like state, country - check if actually categorical
    CATEGORICAL_CANDIDATES = {"state", "country", "city", "location", "category", "status"}
    
    if subtype in CATEGORICAL_CANDIDATES or (column_name and any(c in column_name.lower() for c in CATEGORICAL_CANDIDATES)):
        if is_categorical(values):
            # Use 1% min_frequency for high-cardinality categorical (from SmartDataCorrectionEngine)
            cardinality = len(set(str(v) for v in values if v)) / max(len(values), 1)
            if cardinality > 0.5:
                # High cardinality - use 1% threshold
                min_freq = max(1, int(len(values) * 0.01))
            else:
                # Low cardinality - use 5% threshold
                min_freq = max(2, int(len(values) * 0.05))
                
            return "string.categorical", {"min_frequency": min_freq}
        else:
            # Not truly categorical - use freetext
            logger.info(f"Column '{column_name}' ({subtype}) has high cardinality, using freetext")
            return "string.freetext", {}
    
    # Subtypes that should always use freetext
    FREETEXT_SUBTYPES = {"name", "company", "address", "job_title", "notes", "description", "generic"}
    
    if subtype in FREETEXT_SUBTYPES:
        return "string.freetext", {}
    
    # Username should be freetext (unique by nature)
    if subtype == "username":
        return "string.freetext", {}
    
    # Default fallback - check data characteristics
    if is_categorical(values):
        return "string.categorical", {}
    else:
        return "string.freetext", {}


def get_dynamic_clusterer_for_subtype(
    subtype: str,
    values: Optional[List[Any]] = None,
    column_name: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Get clusterer path with dynamic detection when values are available.
    
    This is the main entry point for dynamic clusterer selection.
    
    Args:
        subtype: Detected subtype
        values: Optional sample values for dynamic detection
        column_name: Optional column name for context
        
    Returns:
        Tuple of (clusterer_path, config)
    """
    if values is not None and len(values) > 0:
        return detect_optimal_clusterer(values, subtype, column_name)
    
    # Without values, use static mapping
    STATIC_MAP = {
        # Validators
        "email": ("string.validator", {"engine": "email"}),
        "phone": ("string.validator", {"engine": "phone"}),
        "url": ("string.validator", {"engine": "url"}),
        "ssn": ("string.validator", {"engine": "ssn"}),
        "zipcode": ("string.validator", {"engine": "zipcode"}),
        "boolean": ("string.validator", {"engine": "boolean"}),
        "uuid": ("string.validator", {"engine": "uuid"}),
        "ip_address": ("string.validator", {"engine": "ip_address"}),
        
        # Categorical
        "state": ("string.categorical", {}),
        "country": ("string.categorical", {}),
        
        # Dynamic - default to freetext without data
        "city": ("string.freetext", {}),
        "location": ("string.freetext", {}),
        
        # Freetext
        "name": ("string.freetext", {}),
        "company": ("string.freetext", {}),
        "address": ("string.freetext", {}),
        "job_title": ("string.freetext", {}),
        "notes": ("string.freetext", {}),
        "description": ("string.freetext", {}),
        "username": ("string.freetext", {}),
        "generic": ("string.freetext", {}),
    }
    
    return STATIC_MAP.get(subtype, ("string.freetext", {}))
