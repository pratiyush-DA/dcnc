"""
Clustering Rules Configuration Loader
Loads and provides access to clustering rules with per-client override support

This module provides:
- Loading default rules from YAML configuration
- Per-client override support via database
- Rule access API for clusterers
"""

import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

logger = logging.getLogger(__name__)


class ClusteringRulesConfig:
    """
    Loads and provides access to clustering rules.
    
    Supports per-client overrides via database.
    Uses caching for performance.
    
    Example:
        >>> config = ClusteringRulesConfig()
        >>> rules = config.get_workflow_rules("text", "email")
        >>> case_rule = config.get_rule("text", "email", "case_sensitivity")
    """
    
    _instance: Optional['ClusteringRulesConfig'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls, config_path: Optional[str] = None, client_id: Optional[str] = None):
        """Singleton pattern to avoid reloading config files."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        client_id: Optional[str] = None
    ):
        if self._initialized:
            return
            
        self._config = self._load_default_config(config_path)
        self._client_id = client_id
        self._client_overrides: Dict[str, Any] = {}
        
        if client_id:
            self._load_client_overrides(client_id)
        
        self._initialized = True
        logger.info(f"ClusteringRulesConfig initialized (client: {client_id or 'default'})")
    
    def _load_default_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load default configuration from YAML file."""
        if config_path is None:
            # Default path relative to this file
            config_path = Path(__file__).parent / "clustering_rules.yaml"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_hardcoded_defaults()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded config from {config_path}")
                return config or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_hardcoded_defaults()
    
    def _get_hardcoded_defaults(self) -> Dict[str, Any]:
        """Fallback hardcoded defaults if config file is missing."""
        return {
            "defaults": {
                "string": {
                    "case_sensitivity": {"enabled": True, "strategy": "majority"},
                    "format_consistency": {"enabled": True, "strategy": "majority"},
                    "gibberish_detection": {
                        "enabled": True,
                        "min_alpha_ratio": 0.7,
                        "reserved_words": ["invalid", "unknown", "test", "null", "n/a"]
                    },
                    "frequency_analysis": {
                        "enabled": True,
                        "min_frequency_absolute": 2,
                        "similarity_threshold": 85,
                        "min_similarity_for_good": 60
                    }
                },
                "numeric": {
                    "outlier_detection": {"enabled": True, "method": "iqr", "iqr_factor": 1.5}
                },
                "datetime": {
                    "format_consistency": {"enabled": True, "strategy": "majority"}
                }
            },
            "workflows": {}
        }
    
    def _load_client_overrides(self, client_id: str):
        """Load client-specific overrides from database."""
        try:
            # Import here to avoid circular imports
            from ..detection.detection_cache import DetectionCache
            
            cache = DetectionCache()
            conn = cache._get_connection()
            
            # Check if table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='client_clustering_rules'
            """)
            
            if cursor.fetchone() is None:
                # Create table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS client_clustering_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT NOT NULL,
                        workflow TEXT NOT NULL,
                        subtype TEXT,
                        rule_name TEXT NOT NULL,
                        rule_value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(client_id, workflow, subtype, rule_name)
                    )
                """)
                conn.commit()
                logger.debug("Created client_clustering_rules table")
                return
            
            # Load overrides
            cursor = conn.execute("""
                SELECT workflow, subtype, rule_name, rule_value 
                FROM client_clustering_rules 
                WHERE client_id = ?
            """, (client_id,))
            
            for row in cursor.fetchall():
                workflow, subtype, rule_name, rule_value = row
                key = f"{workflow}.{subtype or 'default'}.{rule_name}"
                try:
                    import json
                    self._client_overrides[key] = json.loads(rule_value)
                except json.JSONDecodeError:
                    self._client_overrides[key] = rule_value
            
            logger.debug(f"Loaded {len(self._client_overrides)} client overrides")
            
        except Exception as e:
            logger.warning(f"Failed to load client overrides: {e}")
    
    def get_workflow_rules(
        self, 
        workflow: str, 
        subtype: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all rules for a specific workflow/subtype.
        
        Merges defaults with workflow-specific and client overrides.
        
        Args:
            workflow: Workflow type (text, numeric, datetime, identifier)
            subtype: Subtype within workflow (email, phone, age, etc.)
            
        Returns:
            Dictionary of rules for this workflow/subtype
        """
        # Start with defaults for the workflow type
        workflow_type = self._get_workflow_category(workflow)
        defaults = self._config.get("defaults", {}).get(workflow_type, {}).copy()
        
        # Merge with workflow-specific rules
        workflow_rules = self._config.get("workflows", {}).get(workflow, {})
        
        if subtype and subtype in workflow_rules:
            # Merge subtype-specific rules
            subtype_rules = workflow_rules.get(subtype, {})
            defaults = self._deep_merge(defaults, subtype_rules)
        elif "generic" in workflow_rules:
            # Fall back to generic rules for this workflow
            defaults = self._deep_merge(defaults, workflow_rules.get("generic", {}))
        
        # Apply client overrides
        if self._client_overrides:
            for key, value in self._client_overrides.items():
                parts = key.split(".")
                if len(parts) >= 3 and parts[0] == workflow:
                    if parts[1] == "default" or parts[1] == subtype:
                        rule_name = parts[2]
                        if isinstance(defaults.get(rule_name), dict) and isinstance(value, dict):
                            defaults[rule_name] = self._deep_merge(defaults[rule_name], value)
                        else:
                            defaults[rule_name] = value
        
        return defaults
    
    def get_rule(
        self, 
        workflow: str, 
        subtype: Optional[str], 
        rule_name: str,
        default: Any = None
    ) -> Any:
        """
        Get a specific rule value.
        
        Args:
            workflow: Workflow type
            subtype: Subtype within workflow
            rule_name: Name of the rule
            default: Default value if rule not found
            
        Returns:
            Rule value or default
        """
        rules = self.get_workflow_rules(workflow, subtype)
        return rules.get(rule_name, default)
    
    def is_rule_enabled(
        self, 
        workflow: str, 
        subtype: Optional[str], 
        rule_name: str
    ) -> bool:
        """
        Check if a rule is enabled.
        
        Args:
            workflow: Workflow type
            subtype: Subtype within workflow
            rule_name: Name of the rule
            
        Returns:
            True if rule is enabled
        """
        rule = self.get_rule(workflow, subtype, rule_name, {})
        if isinstance(rule, dict):
            return rule.get("enabled", False)
        return bool(rule)
    
    def get_reserved_words(
        self, 
        workflow: str, 
        subtype: Optional[str]
    ) -> List[str]:
        """Get list of reserved/invalid words for this workflow."""
        gibberish = self.get_rule(workflow, subtype, "gibberish_detection", {})
        return gibberish.get("reserved_words", [])
    
    def get_invalid_patterns(
        self, 
        workflow: str, 
        subtype: Optional[str]
    ) -> List[str]:
        """Get list of invalid regex patterns for this workflow."""
        return self.get_rule(workflow, subtype, "invalid_patterns", [])
    
    def get_similarity_threshold(
        self, 
        workflow: str, 
        subtype: Optional[str]
    ) -> int:
        """Get similarity threshold for fuzzy matching."""
        freq = self.get_rule(workflow, subtype, "frequency_analysis", {})
        return freq.get("similarity_threshold", 85)
    
    def get_case_strategy(
        self, 
        workflow: str, 
        subtype: Optional[str]
    ) -> str:
        """Get case sensitivity strategy."""
        case_rule = self.get_rule(workflow, subtype, "case_sensitivity", {})
        return case_rule.get("strategy", "preserve")
    
    def _get_workflow_category(self, workflow: str) -> str:
        """Map workflow to category (string/numeric/datetime)."""
        if workflow in ("text", "string"):
            return "string"
        elif workflow in ("numeric", "number"):
            return "numeric"
        elif workflow in ("datetime", "date", "time"):
            return "datetime"
        return "string"  # Default
    
    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        cls._instance = None
    
    def reload(self, config_path: Optional[str] = None):
        """Reload configuration from file."""
        self._config = self._load_default_config(config_path)
        if self._client_id:
            self._load_client_overrides(self._client_id)
        logger.info("Configuration reloaded")


# Convenience function for getting config instance
def get_rules_config(
    config_path: Optional[str] = None,
    client_id: Optional[str] = None
) -> ClusteringRulesConfig:
    """
    Get or create the rules configuration instance.
    
    Args:
        config_path: Optional path to config file
        client_id: Optional client ID for overrides
        
    Returns:
        ClusteringRulesConfig instance
    """
    return ClusteringRulesConfig(config_path, client_id)
