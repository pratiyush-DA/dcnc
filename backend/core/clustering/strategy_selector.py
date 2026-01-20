"""
Strategy Selector
Routes workflow/subtype combinations to appropriate clusterers
"""

import logging
from typing import Any, Dict, Optional, Tuple

from .base_clusterer import BaseClusterer

logger = logging.getLogger(__name__)


# Mapping of subtype -> (clusterer_path, config)
STRATEGY_MAP = {
    # ============================================
    # NUMERIC WORKFLOW
    # ============================================
    
    # Semantic constraints (known bounds)
    "age": ("numeric.semantic", {"min": 0, "max": 120, "type": "integer"}),
    "rating": ("numeric.semantic", {"min": 0, "max": 10, "outlier_detection": False}),
    "year": ("numeric.semantic", {"min": 1900, "max": 2100, "type": "integer"}),
    "latitude": ("numeric.semantic", {"min": -90, "max": 90}),
    "longitude": ("numeric.semantic", {"min": -180, "max": 180}),
    "percentage": ("numeric.semantic", {"min": 0, "max": 100, "outlier_detection": False}),
    "temperature": ("numeric.semantic", {"min": -273.15, "max": 1000}),
    
    # ML-based (unknown range)
    "salary": ("numeric.generic", {}),
    "amount": ("numeric.generic", {}),
    "count": ("numeric.generic", {}),
    "generic_numeric": ("numeric.generic", {}),
    
    # ============================================
    # STRING WORKFLOW
    # ============================================
    
    # Validator-based (deterministic)
    "email": ("string.validator", {"engine": "email"}),
    "phone": ("string.validator", {"engine": "phone"}),
    "url": ("string.validator", {"engine": "url"}),
    "uuid": ("string.validator", {"engine": "uuid"}),
    "ip_address": ("string.validator", {"engine": "ip_address"}),
    "zipcode": ("string.validator", {"engine": "zipcode"}),
    "boolean": ("string.validator", {"engine": "boolean"}),
    "ssn": ("string.validator", {"engine": "ssn"}),
    
    # Free-text columns (lenient validation)
    "name": ("string.freetext", {}),
    "company": ("string.freetext", {}),
    "address": ("string.freetext", {}),
    "job_title": ("string.freetext", {}),
    "notes": ("string.freetext", {}),
    "description": ("string.freetext", {}),
    "generic": ("string.freetext", {}),
    
    # Categorical (frequency-based fuzzy matching for repetitive data)
    "state": ("string.categorical", {}),
    "country": ("string.categorical", {}),
    
    # Dynamic routing - default freetext, but can be overridden by dynamic detection
    # Use get_dynamic_clusterer_for_subtype() for runtime decision
    "city": ("string.freetext", {}),      # Dynamic: categorical if cardinality < 0.3
    "location": ("string.freetext", {}),  # Dynamic: categorical if cardinality < 0.3
    
    # Username: always freetext (unique by nature)
    "username": ("string.freetext", {}),
    
    # Generic string (semi-structured data)
    "file_path": ("string.generic", {}),
    "product_title": ("string.generic", {}),
    "generic_string": ("string.generic", {}),
    
    # ============================================
    # DATETIME WORKFLOW
    # ============================================
    
    "date": ("datetime.format", {}),
    "datetime": ("datetime.format", {}),
    "generic_datetime": ("datetime.generic", {}),
    
    # ============================================
    # IDENTIFIER WORKFLOW
    # ============================================
    
    "pattern_id": ("identifier.pattern", {}),
    "numeric_id": ("identifier.pattern", {}),
    "generic_identifier": ("identifier.generic", {}),
}

# Cache for loaded clusterers
_clusterer_cache: Dict[str, BaseClusterer] = {}


def get_clusterer(
    workflow: str,
    subtype: str,
    config_override: Optional[Dict[str, Any]] = None
) -> BaseClusterer:
    """
    Get the appropriate clusterer for a workflow/subtype combination.
    
    Args:
        workflow: Workflow type (numeric, text, datetime, identifier)
        subtype: Specific subtype within workflow
        config_override: Optional config to override defaults
        
    Returns:
        BaseClusterer instance
    """
    # Normalize workflow name
    workflow = workflow.lower().replace("text", "string")
    
    # Look up strategy
    if subtype in STRATEGY_MAP:
        strategy_path, default_config = STRATEGY_MAP[subtype]
    else:
        # Fall back to generic for workflow
        fallback_key = f"generic_{workflow}"
        if fallback_key in STRATEGY_MAP:
            strategy_path, default_config = STRATEGY_MAP[fallback_key]
        else:
            # Ultimate fallback: generic string
            strategy_path, default_config = "string.generic", {}
    
    # Merge configs
    config = {**default_config}
    if config_override:
        config.update(config_override)
    
    # Load and cache clusterer
    cache_key = f"{strategy_path}:{hash(frozenset(config.items()))}"
    
    if cache_key not in _clusterer_cache:
        clusterer = _load_clusterer(strategy_path, config)
        _clusterer_cache[cache_key] = clusterer
    
    return _clusterer_cache[cache_key]


def _load_clusterer(strategy_path: str, config: Dict[str, Any]) -> BaseClusterer:
    """
    Dynamically load a clusterer by path.
    
    Args:
        strategy_path: Path like "numeric.semantic" or "string.generic"
        config: Configuration for the clusterer
        
    Returns:
        Instantiated BaseClusterer
    """
    parts = strategy_path.split(".")
    
    if len(parts) != 2:
        raise ValueError(f"Invalid strategy path: {strategy_path}")
    
    workflow_type, clusterer_type = parts
    
    # Import the appropriate module
    if workflow_type == "numeric":
        if clusterer_type == "semantic":
            from .numeric.semantic_clusterer import SemanticNumericClusterer
            return SemanticNumericClusterer(config)
        else:
            from .numeric.generic_clusterer import GenericNumericClusterer
            return GenericNumericClusterer(config)
    
    elif workflow_type == "string":
        if clusterer_type == "validator":
            from .string.validator_clusterer import ValidatorStringClusterer
            return ValidatorStringClusterer(config)
        elif clusterer_type == "categorical":
            from .string.categorical_clusterer import CategoricalStringClusterer
            return CategoricalStringClusterer(config)
        elif clusterer_type == "freetext":
            from .string.freetext_clusterer import FreeTextStringClusterer
            return FreeTextStringClusterer(config)
        else:
            from .string.generic_clusterer import GenericStringClusterer
            return GenericStringClusterer(config)
    
    elif workflow_type == "datetime":
        if clusterer_type == "format":
            from .datetime.format_clusterer import FormatDateTimeClusterer
            return FormatDateTimeClusterer(config)
        else:
            from .datetime.generic_clusterer import GenericDateTimeClusterer
            return GenericDateTimeClusterer(config)
    
    elif workflow_type == "identifier":
        if clusterer_type == "pattern":
            from .identifier.pattern_clusterer import PatternIdentifierClusterer
            return PatternIdentifierClusterer(config)
        else:
            from .identifier.generic_clusterer import GenericIdentifierClusterer
            return GenericIdentifierClusterer(config)
    
    raise ValueError(f"Unknown clusterer: {strategy_path}")


class StrategySelector:
    """
    Helper class for strategy selection with caching.
    """
    
    def __init__(self):
        self._cache: Dict[Tuple[str, str], BaseClusterer] = {}
    
    def get(
        self,
        workflow: str,
        subtype: str,
        **kwargs
    ) -> BaseClusterer:
        """Get clusterer for workflow/subtype."""
        return get_clusterer(workflow, subtype, kwargs.get("config"))
    
    @staticmethod
    def list_strategies() -> Dict[str, Tuple[str, Dict]]:
        """List all registered strategies."""
        return STRATEGY_MAP.copy()
