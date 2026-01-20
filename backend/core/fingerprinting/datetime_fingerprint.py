"""
DateTime Fingerprint Generator
Captures format and pattern characteristics of date/time data
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime

from .base_fingerprint import BaseFingerprint
from ..registry import register_fingerprint


@register_fingerprint("datetime")
class DateTimeFingerprint(BaseFingerprint):
    """
    Fingerprint generator for datetime data.
    
    Captures:
    - Date formats detected
    - Majority format (for standardization)
    - Time presence
    - Timezone awareness
    - Date range
    - Separator characters
    """
    
    # Common date format patterns
    FORMAT_PATTERNS = [
        # ISO formats
        (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S", "iso_datetime"),
        (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S", "standard_datetime"),
        (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d", "iso_date"),
        
        # US formats
        (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y", "us_date"),
        (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y", "us_date_short"),
        
        # European formats
        (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y", "eu_date"),
        (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y", "de_date"),
        
        # Other formats
        (r"^\d{8}$", "%Y%m%d", "compact_date"),
        (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d", "slash_date"),
    ]
    
    @property
    def workflow_type(self) -> str:
        return "datetime"
    
    def _generate_properties(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """Generate datetime-specific properties"""
        if not data:
            return {}
        
        str_data = [str(d).strip() for d in data if d is not None]
        
        # Detect formats
        format_counts = Counter()
        format_names = {}
        parsed_dates = []
        
        for value in str_data:
            detected_format, format_name = self._detect_format(value)
            if detected_format:
                format_counts[detected_format] += 1
                format_names[detected_format] = format_name
                
                # Try to parse
                try:
                    parsed = datetime.strptime(value, detected_format)
                    parsed_dates.append(parsed)
                except ValueError:
                    pass
        
        # Find majority format
        majority_format = None
        majority_name = None
        if format_counts:
            majority_format = format_counts.most_common(1)[0][0]
            majority_name = format_names.get(majority_format)
        
        # Detect time presence
        has_time = any(":" in str(d) for d in str_data)
        
        # Detect timezone
        tz_aware = any(
            "Z" in str(d) or "+" in str(d)[-6:] or "-" in str(d)[-6:]
            for d in str_data
        )
        
        # Date range
        date_range = None
        if parsed_dates:
            min_date = min(parsed_dates)
            max_date = max(parsed_dates)
            date_range = {
                "min": min_date.isoformat(),
                "max": max_date.isoformat(),
                "span_days": (max_date - min_date).days,
            }
        
        # Separator detection
        separator = self._detect_separator(str_data)
        
        return {
            # Format information
            "majority_format": majority_format,
            "majority_format_name": majority_name,
            "formats_detected": dict(format_counts),
            "format_count": len(format_counts),
            
            # Time properties
            "has_time": has_time,
            "has_timezone": tz_aware,
            
            # Date range
            "date_range": date_range,
            
            # Style
            "separator": separator,
            
            # Subtype
            "subtype": subtype,
        }
    
    def _detect_format(self, value: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect the date format of a value.
        
        Returns:
            Tuple of (format_string, format_name) or (None, None)
        """
        for pattern, format_str, name in self.FORMAT_PATTERNS:
            if re.match(pattern, value):
                return format_str, name
        
        return None, None
    
    def _detect_separator(self, data: List[str]) -> str:
        """Detect the common date separator"""
        separators = Counter()
        
        for value in data:
            for sep in ["-", "/", "."]:
                if sep in value:
                    separators[sep] += value.count(sep)
        
        if separators:
            return separators.most_common(1)[0][0]
        
        return "-"
    
    def _generate_signature(self, data: List[Any]) -> Optional[str]:
        """Generate format signature for datetime data"""
        if not data:
            return None
        
        # Count formats
        format_counts = Counter()
        
        for value in data:
            detected, name = self._detect_format(str(value))
            if detected:
                format_counts[detected] += 1
        
        if format_counts:
            return format_counts.most_common(1)[0][0]
        
        return None
    
    def _generate_patterns(self, data: List[Any]) -> List[str]:
        """Generate regex patterns for datetime data"""
        patterns = []
        
        for value in data[:5]:
            detected, _ = self._detect_format(str(value))
            if detected:
                # Convert format to regex pattern
                regex = self._format_to_regex(detected)
                if regex and regex not in patterns:
                    patterns.append(regex)
        
        return patterns
    
    def _format_to_regex(self, format_str: str) -> str:
        """Convert strftime format to regex"""
        replacements = {
            "%Y": r"\d{4}",
            "%y": r"\d{2}",
            "%m": r"\d{1,2}",
            "%d": r"\d{1,2}",
            "%H": r"\d{1,2}",
            "%M": r"\d{2}",
            "%S": r"\d{2}",
        }
        
        regex = format_str
        for fmt, pattern in replacements.items():
            regex = regex.replace(fmt, pattern)
        
        return f"^{regex}$"
    
    def get_correction_hints(
        self,
        fingerprint: FingerprintData,
        bad_value: Any
    ) -> Dict[str, Any]:
        """Get datetime-specific correction hints"""
        props = fingerprint.properties
        bad_str = str(bad_value)
        
        hints = {
            "target_format": props.get("majority_format"),
            "target_format_name": props.get("majority_format_name"),
            "expected_separator": props.get("separator", "-"),
            "should_have_time": props.get("has_time", False),
            "issues": [],
        }
        
        # Detect issues
        detected_format, _ = self._detect_format(bad_str)
        
        if not detected_format:
            hints["issues"].append("unrecognized_format")
        elif detected_format != props.get("majority_format"):
            hints["issues"].append("format_mismatch")
        
        return hints
    
    def calculate_similarity(
        self,
        fingerprint: FingerprintData,
        value: Any
    ) -> float:
        """Calculate datetime similarity to fingerprint"""
        props = fingerprint.properties
        val_str = str(value)
        
        # Check if format matches
        detected_format, _ = self._detect_format(val_str)
        
        if not detected_format:
            return 0.1  # Unrecognized format
        
        if detected_format == props.get("majority_format"):
            return 1.0  # Matches majority
        
        # Different but valid format
        return 0.7
