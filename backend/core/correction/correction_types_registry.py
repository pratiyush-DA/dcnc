"""
Correction Types Registry
Comprehensive mapping of workflow-subworkflow-method to correction types
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum


class CorrectionType(str, Enum):
    """Types of corrections that can be applied"""
    # Format corrections
    FORMAT_STANDARDIZATION = "format_standardized"
    CASE_NORMALIZATION = "case_normalized"
    PROTOCOL_ADDITION = "protocol_added"
    
    # Typo corrections
    DOUBLE_CHAR_FIX = "double_char_fixed"  # @@ → @, .. → .
    DOMAIN_TYPO_FIX = "domain_typo_fixed"
    MISSING_DOT_ADD = "domain_dot_added"
    
    # Semantic corrections
    RANGE_CLAMPING = "range_clamped"
    MIN_CLAMPED = "clamped_min"
    MAX_CLAMPED = "clamped_max"
    
    # Normalization
    BOOLEAN_NORMALIZED = "boolean_normalized"
    PHONE_FORMATTED = "phone_formatted"
    URL_PROTOCOL_ADDED = "url_protocol_added"
    
    # Pattern corrections
    PATTERN_ALIGNED = "pattern_aligned"
    PREFIX_ADDED = "prefix_added"
    SUFFIX_ADDED = "suffix_added"
    SEPARATOR_ADDED = "separator_added"
    ZERO_PADDED = "zero_padded"
    
    # Numeric corrections
    CURRENCY_STRIPPED = "currency_stripped"
    EUROPEAN_DECIMAL_CONVERTED = "european_decimal_converted"
    THOUSAND_SEPARATOR_REMOVED = "thousand_separator_removed"
    ROUNDED_TO_INTEGER = "rounded_to_integer"
    
    # Text corrections
    WHITESPACE_CLEANED = "whitespace_cleaned"
    TITLE_CASED = "title_cased"
    UPPERCASED = "uppercased"
    LOWERCASED = "lowercased"
    
    # Date/Time corrections
    DATE_FORMAT_STANDARDIZED = "date_format_standardized"
    TIME_FORMAT_STANDARDIZED = "time_format_standardized"
    DATETIME_FORMAT_STANDARDIZED = "datetime_format_standardized"
    TIMEZONE_NORMALIZED = "timezone_normalized"
    COMPONENT_FIXED = "component_fixed"  # Invalid month/day fixed


# Mapping: (workflow, subtype, method) -> List[CorrectionType]
CORRECTION_TYPE_MAP: Dict[Tuple[str, str, str], List[CorrectionType]] = {
    # Text Workflow
    ("text", "email", "validator_email"): [
        CorrectionType.DOUBLE_CHAR_FIX,
        CorrectionType.DOMAIN_TYPO_FIX,
        CorrectionType.MISSING_DOT_ADD,
        CorrectionType.CASE_NORMALIZATION,
    ],
    ("text", "phone", "validator_phone"): [
        CorrectionType.PHONE_FORMATTED,
        CorrectionType.FORMAT_STANDARDIZATION,
    ],
    ("text", "url", "validator_url"): [
        CorrectionType.PROTOCOL_ADDITION,
        CorrectionType.URL_PROTOCOL_ADDED,
    ],
    ("text", "boolean", "validator_boolean"): [
        CorrectionType.BOOLEAN_NORMALIZED,
    ],
    ("text", "name", "freetext_lenient"): [
        CorrectionType.CASE_NORMALIZATION,
        CorrectionType.WHITESPACE_CLEANED,
        CorrectionType.TITLE_CASED,
    ],
    ("text", "company", "freetext_lenient"): [
        CorrectionType.CASE_NORMALIZATION,
        CorrectionType.TITLE_CASED,
    ],
    ("text", "generic", "freetext_lenient"): [
        CorrectionType.WHITESPACE_CLEANED,
        CorrectionType.CASE_NORMALIZATION,
    ],
    
    # Numeric Workflow
    ("numeric", "age", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
        CorrectionType.MAX_CLAMPED,
        CorrectionType.ROUNDED_TO_INTEGER,
    ],
    ("numeric", "year", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
        CorrectionType.MAX_CLAMPED,
        CorrectionType.ROUNDED_TO_INTEGER,
    ],
    ("numeric", "rating", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MAX_CLAMPED,
    ],
    ("numeric", "latitude", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
        CorrectionType.MAX_CLAMPED,
    ],
    ("numeric", "longitude", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
        CorrectionType.MAX_CLAMPED,
    ],
    ("numeric", "salary", "generic_bounds_ensemble"): [
        CorrectionType.CURRENCY_STRIPPED,
        CorrectionType.THOUSAND_SEPARATOR_REMOVED,
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
    ],
    ("numeric", "amount", "generic_bounds_ensemble"): [
        CorrectionType.CURRENCY_STRIPPED,
        CorrectionType.EUROPEAN_DECIMAL_CONVERTED,
        CorrectionType.THOUSAND_SEPARATOR_REMOVED,
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MIN_CLAMPED,
    ],
    ("numeric", "percentage", "semantic_iqr"): [
        CorrectionType.RANGE_CLAMPING,
        CorrectionType.MAX_CLAMPED,
    ],
    ("numeric", "generic", "isolation_forest_iqr_zscore"): [
        CorrectionType.CURRENCY_STRIPPED,
        CorrectionType.EUROPEAN_DECIMAL_CONVERTED,
        CorrectionType.THOUSAND_SEPARATOR_REMOVED,
    ],
    
    # DateTime Workflow
    ("datetime", "date", "format_parser"): [
        CorrectionType.DATE_FORMAT_STANDARDIZED,
        CorrectionType.FORMAT_STANDARDIZATION,
        CorrectionType.COMPONENT_FIXED,
    ],
    ("datetime", "datetime", "format_parser"): [
        CorrectionType.DATETIME_FORMAT_STANDARDIZED,
        CorrectionType.FORMAT_STANDARDIZATION,
        CorrectionType.TIMEZONE_NORMALIZED,
        CorrectionType.COMPONENT_FIXED,
    ],
    ("datetime", "time", "format_parser"): [
        CorrectionType.TIME_FORMAT_STANDARDIZED,
        CorrectionType.FORMAT_STANDARDIZATION,
    ],
    ("datetime", "generic", "format_parser"): [
        CorrectionType.DATE_FORMAT_STANDARDIZED,
        CorrectionType.DATETIME_FORMAT_STANDARDIZED,
        CorrectionType.FORMAT_STANDARDIZATION,
    ],
    
    # Identifier Workflow
    ("identifier", "pattern_id", "pattern_signature"): [
        CorrectionType.PATTERN_ALIGNED,
        CorrectionType.PREFIX_ADDED,
        CorrectionType.SUFFIX_ADDED,
        CorrectionType.SEPARATOR_ADDED,
        CorrectionType.CASE_NORMALIZATION,
    ],
    ("identifier", "numeric_id", "pattern_signature"): [
        CorrectionType.ZERO_PADDED,
        CorrectionType.PATTERN_ALIGNED,
    ],
    ("identifier", "generic", "entropy_uniqueness"): [
        CorrectionType.CASE_NORMALIZATION,
        CorrectionType.PATTERN_ALIGNED,
    ],
}


def get_correction_types(workflow: str, subtype: str, method: str) -> List[CorrectionType]:
    """
    Get available correction types for a workflow-subtype-method combination.
    
    Args:
        workflow: Workflow type (text, numeric, datetime, identifier)
        subtype: Subtype (email, phone, date, etc.)
        method: Clustering method (validator_email, semantic_iqr, etc.)
        
    Returns:
        List of correction types that can be applied
    """
    key = (workflow, subtype, method)
    return CORRECTION_TYPE_MAP.get(key, [])


def get_all_correction_types_for_workflow(workflow: str) -> List[CorrectionType]:
    """Get all correction types available for a workflow"""
    types = set()
    for (w, s, m), correction_types in CORRECTION_TYPE_MAP.items():
        if w == workflow:
            types.update(correction_types)
    return list(types)
