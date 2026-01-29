"""
DateTime Corrector
Correction engine for date and datetime data types
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base_corrector import BaseCorrector
from ..interfaces import CorrectionResult, CorrectionStatus
from ..registry import register_corrector

logger = logging.getLogger(__name__)


# Format patterns for parsing (comprehensive list)
FORMAT_PATTERNS = [
    # ISO datetime formats
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?$", "%Y-%m-%d %H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", "%Y-%m-%d %H:%M:%S"),
    
    # ISO date formats
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    
    # US date formats
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y"),
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%m-%d-%Y"),
    
    # European date formats
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),
    (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%d/%m/%Y"),
    
    # Compact formats
    (r"^\d{8}$", "%Y%m%d"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
    (r"^\d{14}(?:\.\d+)?Z?$", "%Y%m%d%H%M%S"),
    
    # Time formats
    (r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$", "%H:%M:%S"),
    (r"^\d{2}:\d{2}$", "%H:%M"),
    (r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?$", "%I:%M:%S %p"),  # 12-hour format
    
    # Month name formats
    (r"^\w{3}\s+\d{1,2},?\s+\d{4}$", "%b %d, %Y"),
    (r"^\d{1,2}\s+\w{3}\s+\d{4}$", "%d %b %Y"),
    (r"^\w+\s+\d{1,2},?\s+\d{4}$", "%B %d, %Y"),
]


@register_corrector("datetime")
@register_corrector("date")
@register_corrector("time")
class DatetimeCorrector(BaseCorrector):
    """
    Correction engine for datetime data.
    
    Key feature: Standardizes all dates to the MAJORITY format
    detected in good data (Bug Fix #4).
    
    Corrections supported:
    - Format standardization to majority format
    - Component fixing (invalid month/day)
    - Time zone handling
    """
    
    @property
    def name(self) -> str:
        return "datetime_corrector"
    
    @property
    def description(self) -> str:
        return "Standardizes datetime to majority format"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return ["date", "datetime", "time", "generic"]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct datetime value"""
        str_val = str(value).strip()
        changes = []
        
        # Get target format from fingerprint or kwargs
        target_format = learned_patterns.get("majority_format")
        if not target_format and fingerprint:
            # Check both top-level and nested properties
            target_format = fingerprint.get("majority_format") or fingerprint.get("properties", {}).get("majority_format")
        if not target_format:
            target_format = kwargs.get("target_format")
        
        # Determine default format based on subtype
        if not target_format:
            if subtype == "datetime":
                target_format = "%Y-%m-%dT%H:%M:%S"
            elif subtype == "time":
                target_format = "%H:%M:%S"
            elif subtype == "date":
                target_format = "%Y-%m-%d"
            else:  # generic
                target_format = "%Y-%m-%d"
        
        # Handle special format markers (from dateutil parsing)
        if target_format in ("dateutil", "dateutil_fuzzy"):
            # Use default format based on subtype
            if subtype == "datetime":
                target_format = "%Y-%m-%dT%H:%M:%S"
            else:
                target_format = "%Y-%m-%d"
        
        # Try to parse
        parsed, current_format = self._parse_datetime(str_val, subtype)
        
        if not parsed:
            return self._make_rejected_result(value, "unparseable_datetime")
        
        # Normalize current_format if it's a dateutil marker
        if current_format in ("dateutil", "dateutil_fuzzy", None):
            # Detect format from parsed datetime
            if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
                current_format = "%Y-%m-%d"
            else:
                current_format = "%Y-%m-%dT%H:%M:%S"
        
        # Check if already in target format
        if current_format == target_format:
            # Verify the string representation matches
            try:
                formatted = parsed.strftime(target_format)
                if str_val == formatted or str_val.replace(" ", "T") == formatted:
                    return self._make_unchanged_result(value)
            except:
                pass
        
        # Reformat to target
        try:
            corrected = parsed.strftime(target_format)
            changes.append("format_standardized")
            
            return self._make_corrected_result(value, corrected, changes, confidence=1.0)
        except Exception as e:
            logger.warning(f"Failed to reformat datetime: {e}")
            return self._make_rejected_result(value, str(e))
    
    def _parse_datetime(self, value: str, subtype: Optional[str] = None) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Try to parse a datetime value with comprehensive format support.
        
        Returns:
            Tuple of (parsed_datetime, format_string) or (None, None)
        """
        # Handle time-only values
        if subtype == "time":
            time_patterns = [
                (r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$", "%H:%M:%S"),
                (r"^\d{2}:\d{2}$", "%H:%M"),
                (r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?$", "%I:%M:%S %p"),
            ]
            for pattern, fmt in time_patterns:
                if re.match(pattern, value, re.IGNORECASE):
                    try:
                        # For time-only, use a default date (1900-01-01) for parsing
                        from datetime import time as dt_time
                        if "%p" in fmt:  # 12-hour format
                            parsed = datetime.strptime(value, fmt)
                        else:
                            time_parts = value.split(":")
                            hour = int(time_parts[0])
                            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                            second = int(time_parts[2]) if len(time_parts) > 2 else 0
                            t = dt_time(hour, minute, second)
                            parsed = datetime.combine(datetime(1900, 1, 1), t)
                        return parsed, fmt
                    except (ValueError, IndexError):
                        continue
        
        # Try known format patterns first
        for pattern, format_str in FORMAT_PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                try:
                    # Handle ISO format timezone suffix
                    clean_val = re.sub(r"[+-]\d{2}:?\d{2}$", "", value)
                    clean_val = clean_val.replace("Z", "").split(".")[0]
                    
                    # Handle 12-hour format with AM/PM
                    if "%p" in format_str or "%I" in format_str:
                        parsed = datetime.strptime(value, format_str)
                    else:
                        parsed = datetime.strptime(clean_val, format_str)
                    return parsed, format_str
                except ValueError:
                    continue
        
        # Try generic parsing with dateutil (comprehensive fallback)
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value, fuzzy=True)
            
            # Detect format from parsed datetime
            has_time = parsed.hour != 0 or parsed.minute != 0 or parsed.second != 0
            
            if subtype == "time":
                detected_format = "%H:%M:%S"
            elif not has_time:
                detected_format = "%Y-%m-%d"
            else:
                detected_format = "%Y-%m-%dT%H:%M:%S"
            
            return parsed, detected_format
        except Exception:
            pass
        
        return None, None
