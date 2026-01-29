"""
Heuristic Matcher
Rule-based column name matching with priority ordering
Uses ONLY when content pattern analysis doesn't find a strong match
"""

import re
import fnmatch
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class HeuristicMatcher:
    """
    Matches column names against priority-ordered heuristic rules.
    
    Used as SECONDARY detection method (after content pattern analysis).
    Rules are loaded from YAML configuration.
    More specific patterns have higher priority (lower number).
    """
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize matcher.
        
        Args:
            rules_path: Path to heuristic_rules.yaml
        """
        self._rules: List[Dict[str, Any]] = []
        
        if rules_path:
            self._load_rules(rules_path)
        else:
            # Try default path
            default_path = Path(__file__).parent.parent.parent / "config" / "heuristic_rules.yaml"
            if default_path.exists():
                self._load_rules(str(default_path))
            else:
                # Use built-in rules
                self._rules = self._get_default_rules()
        
        # Sort by priority (lower = higher priority)
        self._rules.sort(key=lambda r: r.get("priority", 999))
        
        logger.info(f"HeuristicMatcher loaded {len(self._rules)} rules")
    
    def _load_rules(self, path: str):
        """Load rules from YAML file"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config and "rules" in config:
                self._rules = config["rules"]
                logger.debug(f"Loaded {len(self._rules)} rules from {path}")
        except Exception as e:
            logger.error(f"Failed to load heuristic rules: {e}")
            self._rules = self._get_default_rules()
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """Get built-in default rules (priority ordered)"""
        return [
            # Identifiers
            {"name": "id_generic", "patterns": ["*_id", "id_*", "*identifier*"], "workflow": "identifier", "subtype": "pattern_id", "priority": 1},
            
            # Contact (high priority)
            {"name": "email", "patterns": ["*email*", "*e_mail*"], "workflow": "text", "subtype": "email", "priority": 21},
            {"name": "phone", "patterns": ["*phone*", "*mobile*", "*cell*"], "workflow": "text", "subtype": "phone", "priority": 22},
            {"name": "url", "patterns": ["*url*", "*website*", "*link*"], "workflow": "text", "subtype": "url", "priority": 23},
            {"name": "ip_address", "patterns": ["*ip*", "*ip_address*"], "workflow": "text", "subtype": "ip_address", "priority": 24},
            {"name": "ssn", "patterns": ["*ssn*", "*social_security*", "*sin*"], "workflow": "text", "subtype": "ssn", "priority": 25},
            
            # Location (specific before generic)
            {"name": "city", "patterns": ["*city*", "*town*"], "workflow": "text", "subtype": "location", "priority": 41},
            {"name": "state", "patterns": ["*state*", "*province*"], "workflow": "text", "subtype": "state", "priority": 42},
            {"name": "zipcode", "patterns": ["*zip*", "*postal*"], "workflow": "text", "subtype": "zipcode", "priority": 43},
            {"name": "country", "patterns": ["*country*"], "workflow": "text", "subtype": "country", "priority": 44},
            {"name": "address", "patterns": ["*address*", "*street*"], "workflow": "text", "subtype": "address", "priority": 50},
            
            # Names
            {"name": "company", "patterns": ["*company*", "*org*", "*business*"], "workflow": "text", "subtype": "company", "priority": 61},
            {"name": "name", "patterns": ["*name*"], "workflow": "text", "subtype": "name", "priority": 70},
            
            # Numeric
            {"name": "age", "patterns": ["*age*"], "workflow": "numeric", "subtype": "age", "priority": 81},
            {"name": "rating", "patterns": ["*rating*", "*score*"], "workflow": "numeric", "subtype": "rating", "priority": 82},
            {"name": "salary", "patterns": ["*salary*", "*wage*", "*pay*"], "workflow": "numeric", "subtype": "salary", "priority": 83},
            {"name": "amount", "patterns": ["*amount*", "*price*", "*total*"], "workflow": "numeric", "subtype": "amount", "priority": 84},
            {"name": "latitude", "patterns": ["*latitude*", "*lat*"], "workflow": "numeric", "subtype": "latitude", "priority": 85},
            {"name": "longitude", "patterns": ["*longitude*", "*lng*", "*lon*"], "workflow": "numeric", "subtype": "longitude", "priority": 86},
            
            # DateTime
            {"name": "datetime", "patterns": ["*datetime*", "*timestamp*", "*_at"], "workflow": "datetime", "subtype": "datetime", "priority": 101},
            {"name": "date", "patterns": ["*date*", "*dob*", "*created*"], "workflow": "datetime", "subtype": "date", "priority": 102},
            
            # Boolean
            {"name": "boolean", "patterns": ["*is_*", "*has_*", "*active*", "*enabled*"], "workflow": "text", "subtype": "boolean", "priority": 121},
            
            # Other
            {"name": "title", "patterns": ["*title*", "*role*", "*job*"], "workflow": "text", "subtype": "job_title", "priority": 132},
        ]
    
    def match(self, column_name: str) -> Optional[Dict[str, Any]]:
        """
        Match column name against heuristic rules.
        
        Args:
            column_name: Column name to match
            
        Returns:
            Match result dict or None
        """
        column_lower = column_name.lower()
        
        # Priority check: longitude must be detected before latitude
        # (since latitude patterns might match "longitude" partially)
        if "longitude" in column_lower or "lng" in column_lower or "lon" in column_lower:
            if "latitude" not in column_lower:  # Don't override if both present
                return {
                    "workflow": "numeric",
                    "subtype": "longitude",
                    "confidence": 0.95,
                    "rule_name": "longitude_priority",
                    "matched_pattern": "longitude",
                }
        
        for rule in self._rules:
            # Check exclusions first
            exclude_patterns = rule.get("exclude_patterns", [])
            excluded = False
            for exclude in exclude_patterns:
                if fnmatch.fnmatch(column_lower, exclude.lower()):
                    excluded = True
                    break
            
            if excluded:
                continue

            patterns = rule.get("patterns", [])
            
            for pattern in patterns:
                # Use fnmatch for glob-style matching
                if fnmatch.fnmatch(column_lower, pattern.lower()):
                    return {
                        "workflow": rule.get("workflow"),
                        "subtype": rule.get("subtype"),
                        "confidence": 0.9,
                        "rule_name": rule.get("name"),
                        "matched_pattern": pattern,
                    }
        
        return None
    
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Get all loaded rules"""
        return self._rules.copy()
    
    def add_rule(
        self,
        name: str,
        patterns: List[str],
        workflow: str,
        subtype: str,
        priority: int = 50
    ):
        """
        Add a new rule dynamically.
        
        Args:
            name: Rule name
            patterns: List of glob patterns
            workflow: Target workflow
            subtype: Target subtype
            priority: Rule priority (lower = higher)
        """
        rule = {
            "name": name,
            "patterns": patterns,
            "workflow": workflow,
            "subtype": subtype,
            "priority": priority,
        }
        
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.get("priority", 999))
