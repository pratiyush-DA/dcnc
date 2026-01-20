"""
Pattern Analyzer
Content-based pattern analysis for type detection
PRIORITY: Content patterns are checked FIRST, before heuristics
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    Analyzes data content to detect type patterns.
    
    This is the PRIMARY detection method - content patterns
    override heuristic rules for robustness.
    
    Detection Philosophy:
    - If data looks like an email, it's an email (regardless of column name)
    - If data looks like a date, it's a date (even if column is "last_login")
    - Heuristics only guide when content is ambiguous
    """
    
    # Built-in strong patterns (override heuristics)
    STRONG_PATTERNS = {
        "email": {
            "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "threshold": 0.7,
            "workflow": "text",
            "subtype": "email",
            "priority": 1,
        },
        "uuid": {
            "regex": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            "threshold": 0.8,
            "workflow": "text",
            "subtype": "uuid",
            "priority": 2,
        },
        "ip_address": {
            "regex": r"^(?:\d{1,3}\.){3}\d{1,3}$",
            "threshold": 0.7,
            "workflow": "text",
            "subtype": "ip_address",
            "priority": 3,
            "extra_validator": "_validate_ip_octets",
        },
        "datetime_iso": {
            "regex": r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}",
            "threshold": 0.6,
            "workflow": "datetime",
            "subtype": "datetime",
            "priority": 4,
        },
        "date_iso": {
            "regex": r"^\d{4}-\d{2}-\d{2}$",
            "threshold": 0.7,
            "workflow": "datetime",
            "subtype": "date",
            "priority": 5,
        },
        "date_us": {
            "regex": r"^\d{1,2}/\d{1,2}/\d{2,4}$",
            "threshold": 0.7,
            "workflow": "datetime",
            "subtype": "date",
            "priority": 6,
        },
        "url": {
            "regex": r"^(https?://|www\.)[^\s]+$",
            "threshold": 0.6,
            "workflow": "text",
            "subtype": "url",
            "priority": 7,
        },
        "phone": {
            "regex": r"^[\d\s\-\(\)\+\.]{7,20}$",
            "threshold": 0.6,
            "workflow": "text",
            "subtype": "phone",
            "priority": 8,
            "extra_check": "digit_count",
        },
        "zipcode_us": {
            "regex": r"^\d{5}(-\d{4})?$",
            "threshold": 0.8,
            "workflow": "text",
            "subtype": "zipcode",
            "priority": 9,
        },
        "boolean": {
            "regex": r"^(true|false|yes|no|1|0|y|n|t|f)$",
            "threshold": 0.8,
            "workflow": "text",
            "subtype": "boolean",
            "priority": 10,
            "flags": re.IGNORECASE,
        },
        "ssn": {
            "regex": r"^\d{3}-\d{2}-\d{4}$",
            "threshold": 0.6,
            "workflow": "text",
            "subtype": "ssn",
            "priority": 7,  # Higher than phone (8)
        },
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize pattern analyzer"""
        self._patterns = self.STRONG_PATTERNS.copy()
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        
        # Load additional patterns from config if available
        if config_path:
            self._load_config_patterns(config_path)
        else:
            default_path = Path(__file__).parent.parent.parent / "config" / "heuristic_rules.yaml"
            if default_path.exists():
                self._load_config_patterns(str(default_path))
        
        self._compile_patterns()
    
    def _load_config_patterns(self, path: str):
        """Load patterns from YAML config"""
        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
            
            if config and "content_patterns" in config:
                for name, pattern_config in config["content_patterns"].items():
                    self._patterns[name] = {
                        "regex": pattern_config.get("regex", ""),
                        "threshold": pattern_config.get("min_match_ratio", 0.7),
                        "workflow": pattern_config.get("workflow", "text"),
                        "subtype": pattern_config.get("subtype", "generic"),
                        "priority": pattern_config.get("priority", 999),
                    }
                    if pattern_config.get("case_insensitive"):
                        self._patterns[name]["flags"] = re.IGNORECASE
        except Exception as e:
            logger.warning(f"Could not load config patterns: {e}")
    
    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        for name, config in self._patterns.items():
            try:
                flags = config.get("flags", 0)
                self._compiled_patterns[name] = re.compile(
                    config["regex"], flags
                )
            except re.error as e:
                logger.error(f"Invalid regex for {name}: {e}")
    
    def analyze(
        self,
        data: List[Any],
        min_samples: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze data samples to detect type patterns.
        
        This is the PRIMARY detection method.
        Returns the best matching pattern or None.
        
        Args:
            data: Sample data to analyze
            min_samples: Minimum samples for reliable detection
            
        Returns:
            Detection result dict or None
        """
        if not data or len(data) < min_samples:
            return None
        
        # Convert to strings and filter nulls
        str_data = [
            str(v).strip() 
            for v in data 
            if v is not None and str(v).strip()
        ]
        
        if len(str_data) < min_samples:
            return None
        
        # Check each pattern in priority order
        results = []
        sorted_patterns = sorted(
            self._patterns.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        
        for name, config in sorted_patterns:
            match_ratio = self._get_match_ratio(str_data, name, config)
            threshold = config.get("threshold", 0.7)
            
            if match_ratio >= threshold:
                results.append({
                    "pattern_name": name,
                    "workflow": config["workflow"],
                    "subtype": config["subtype"],
                    "match_ratio": match_ratio,
                    "confidence": min(0.95, match_ratio),
                    "priority": config.get("priority", 999),
                })
        
        if not results:
            # Check if it's numeric data
            numeric_result = self._check_numeric(str_data)
            if numeric_result:
                return numeric_result
            
            return None
        
        # Return best match (highest priority = lowest number)
        results.sort(key=lambda r: (r["priority"], -r["match_ratio"]))
        return results[0]
    
    def _get_match_ratio(
        self,
        data: List[str],
        pattern_name: str,
        config: Dict[str, Any]
    ) -> float:
        """Calculate match ratio for a pattern"""
        compiled = self._compiled_patterns.get(pattern_name)
        if not compiled:
            return 0.0
        
        match_count = 0
        
        for value in data:
            if compiled.match(value):
                # Extra validation for some patterns
                extra_check = config.get("extra_check")
                extra_validator = config.get("extra_validator")
                
                if extra_check == "digit_count":
                    # Phone numbers need 7-15 digits
                    digits = sum(c.isdigit() for c in value)
                    if 7 <= digits <= 15:
                        match_count += 1
                elif extra_validator == "_validate_ip_octets":
                    if self._validate_ip_octets(value):
                        match_count += 1
                else:
                    match_count += 1
        
        return match_count / len(data) if data else 0.0
    
    def _validate_ip_octets(self, ip: str) -> bool:
        """Validate IP address octets are 0-255"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except ValueError:
            return False
    
    def _check_numeric(
        self,
        data: List[str],
        threshold: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """Check if data is numeric"""
        numeric_count = 0
        
        for value in data:
            # Handle currency and European decimals
            clean_value = self._clean_numeric(value)
            try:
                float(clean_value)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        ratio = numeric_count / len(data) if data else 0
        
        if ratio >= threshold:
            return {
                "pattern_name": "numeric",
                "workflow": "numeric",
                "subtype": "generic_numeric",
                "match_ratio": ratio,
                "confidence": ratio * 0.8,
                "priority": 1000,
            }
        
        return None
    
    def _clean_numeric(self, value: str) -> str:
        """Clean numeric value for parsing"""
        # Remove currency symbols and thousand separators
        clean = value.strip()
        clean = clean.replace("$", "").replace("€", "").replace("£", "")
        clean = clean.replace(",", "")  # Thousand separator OR European decimal
        
        # If it looks like European decimal (ends with comma + digits)
        if re.match(r"^\d+,\d{1,2}$", value):
            clean = value.replace(",", ".")
        
        return clean
    
    def detect_data_type(self, data: List[Any]) -> Tuple[str, str, float]:
        """
        Detect basic data type from content.
        
        Returns:
            Tuple of (workflow, subtype, confidence)
        """
        result = self.analyze(data)
        
        if result:
            return result["workflow"], result["subtype"], result["confidence"]
        
        # Fall back to text/generic
        return "text", "generic", 0.3
