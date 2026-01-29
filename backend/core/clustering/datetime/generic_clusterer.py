"""
Generic DateTime Clusterer
Production-grade fuzzy datetime parsing for unknown formats
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


class GenericDateTimeClusterer(BaseClusterer):
    """
    Production-grade clusterer for unknown datetime formats.
    
    Handles:
    - Unix timestamps (seconds and milliseconds)
    - ISO 8601 with timezones
    - Natural language dates ("Jan 1, 2024")
    - Various regional formats
    - Time-only values
    
    All valid datetimes go to good_data, invalid to bad_data.
    """
    
    # Comprehensive format patterns
    KNOWN_FORMATS = [
        # ISO formats
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        
        # US formats
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m-%d-%Y",
        "%m-%d-%y",
        
        # European formats
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        
        # Compact formats
        "%Y%m%d",
        "%Y%m%d%H%M%S",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        
        # Month name formats (short)
        "%b %d, %Y",
        "%b %d %Y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%Y-%b-%d",
        
        # Month name formats (full)
        "%B %d, %Y",
        "%B %d %Y",
        "%d %B %Y",
        "%d %B, %Y",
        
        # Month name with time
        "%b %d, %Y %H:%M:%S",
        "%B %d, %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S",
        
        # RFC 2822 / Email format
        "%a, %d %b %Y %H:%M:%S",
        
        # Time formats
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
        
        # SQL datetime formats
        "%Y-%m-%d %H:%M:%S.%f",
        
        # Slash with time (common in logs)
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.min_year = config.get("min_year", 1900) if config else 1900
        self.max_year = config.get("max_year", 2100) if config else 2100
        self.min_timestamp = config.get("min_timestamp", 0) if config else 0
        self.max_timestamp = config.get("max_timestamp", 4102444800) if config else 4102444800  # 2100-01-01
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster datetime data using fuzzy parsing.
        """
        indices = self._prepare_indices(data, indices)
        
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        format_counts = Counter()
        detected_type = Counter()  # Track what type of datetime we're seeing
        
        for value, idx in zip(data, indices):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            str_val = str(value).strip()
            parsed, fmt, dt_type = self._try_parse(str_val)
            
            if parsed and self._validate_components(parsed):
                good_data.append(value)
                good_indices.append(idx)
                format_counts[fmt or "fuzzy"] += 1
                detected_type[dt_type] += 1
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        majority_format = format_counts.most_common(1)[0][0] if format_counts else None
        majority_type = detected_type.most_common(1)[0][0] if detected_type else "unknown"
        
        fingerprint = self._generate_fingerprint(
            good_data, format_counts, majority_format, majority_type
        )
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="fuzzy_datetime_parser",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "majority_format": majority_format,
                "datetime_type": majority_type,
                "format_distribution": dict(format_counts),
            }
        )
    
    def _try_parse(self, value: str) -> Tuple[Optional[datetime], Optional[str], str]:
        """
        Try to parse datetime value using multiple strategies.
        
        Returns:
            Tuple of (parsed_datetime, format_string, datetime_type)
        """
        # 1. Check for Unix timestamp (pure digits)
        if re.match(r"^\d{10,13}$", value):
            return self._parse_timestamp(value)
        
        # 2. Strip timezone suffix for parsing
        clean_val = self._strip_timezone(value)
        
        # 3. Try known formats
        for fmt in self.KNOWN_FORMATS:
            try:
                parsed = datetime.strptime(clean_val, fmt)
                dt_type = "datetime" if "H" in fmt else "date"
                if dt_type == "date" and ":" in clean_val:
                    dt_type = "time"
                return parsed, fmt, dt_type
            except ValueError:
                continue
        
        # 4. Fuzzy parsing with dateutil
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value, fuzzy=True)
            
            # Determine type based on parsed values
            if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
                dt_type = "date"
                detected_format = "%Y-%m-%d"  # ISO date format
            else:
                dt_type = "datetime"
                detected_format = "%Y-%m-%dT%H:%M:%S"  # ISO datetime format
            
            return parsed, detected_format, dt_type
        except Exception:
            pass
        
        return None, None, "unknown"
    
    def _parse_timestamp(self, value: str) -> Tuple[Optional[datetime], Optional[str], str]:
        """Parse Unix timestamp (seconds or milliseconds)."""
        try:
            ts = int(value)
            
            # Detect if milliseconds
            if ts > 1e12:
                ts = ts / 1000
            
            # Validate range
            if ts < self.min_timestamp or ts > self.max_timestamp:
                return None, None, "unknown"
            
            parsed = datetime.fromtimestamp(ts)
            return parsed, "unix_timestamp", "timestamp"
            
        except (ValueError, OSError):
            return None, None, "unknown"
    
    def _strip_timezone(self, value: str) -> str:
        """Strip timezone suffix for parsing."""
        # Remove Z suffix
        clean = value.replace("Z", "")
        
        # Remove +HH:MM or -HH:MM timezone
        clean = re.sub(r"[+-]\d{2}:?\d{2}$", "", clean)
        
        # Remove microseconds beyond 6 digits
        if "." in clean:
            base, frac = clean.rsplit(".", 1)
            frac = frac[:6]  # strptime supports only 6 digits
            clean = f"{base}.{frac}"
        
        return clean.strip()
    
    def _validate_components(self, dt: datetime) -> bool:
        """Validate date components are realistic."""
        if dt.year < self.min_year or dt.year > self.max_year:
            return False
        return True
    
    def _generate_fingerprint(
        self,
        values: List[Any],
        format_counts: Counter,
        majority_format: Optional[str],
        majority_type: str
    ) -> Dict[str, Any]:
        """Generate fingerprint from parsed datetimes."""
        return {
            "workflow": "datetime",
            "method": "fuzzy_generic",
            "sample_size": len(values),
            "properties": {
                "majority_format": majority_format,
                "datetime_type": majority_type,
                "format_distribution": dict(format_counts),
                "unique_formats": len(format_counts),
            }
        }
