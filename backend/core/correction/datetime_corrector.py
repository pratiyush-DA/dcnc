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


# Format patterns for parsing
FORMAT_PATTERNS = [
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y"),
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
]


@register_corrector("datetime")
@register_corrector("date")
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
        return ["date", "datetime", "generic"]
    
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
            target_format = fingerprint.get("majority_format")
        if not target_format:
            target_format = kwargs.get("target_format", "%Y-%m-%d")
        
        # Try to parse
        parsed, current_format = self._parse_datetime(str_val)
        
        if not parsed:
            return self._make_rejected_result(value, "unparseable_datetime")
        
        # Check if already in target format
        if current_format == target_format:
            return self._make_unchanged_result(value)
        
        # Reformat to target
        try:
            corrected = parsed.strftime(target_format)
            changes.append("format_standardized")
            
            return self._make_corrected_result(value, corrected, changes, confidence=1.0)
        except Exception as e:
            logger.warning(f"Failed to reformat datetime: {e}")
            return self._make_rejected_result(value, str(e))
    
    def _parse_datetime(self, value: str) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Try to parse a datetime value.
        
        Returns:
            Tuple of (parsed_datetime, format_string) or (None, None)
        """
        for pattern, format_str in FORMAT_PATTERNS:
            if re.match(pattern, value):
                try:
                    parsed = datetime.strptime(value, format_str)
                    return parsed, format_str
                except ValueError:
                    continue
        
        # Try generic parsing
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value)
            return parsed, None
        except Exception:
            pass
        
        return None, None
