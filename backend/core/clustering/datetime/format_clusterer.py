"""
Format DateTime Clusterer
For known date/datetime subtypes with standard formats
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from ..base_clusterer import BaseClusterer, ClusteringResult

logger = logging.getLogger(__name__)


# Common date format patterns with regex and strptime format
FORMAT_PATTERNS = [
    # ISO formats
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", "%Y-%m-%d %H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    
    # US formats
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y"),
    
    # European formats
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),
    (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y"),
    
    # Compact formats
    (r"^\d{8}$", "%Y%m%d"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
    (r"^\d{14}(?:\.0)?Z?$", "%Y%m%d%H%M%S"),  # Added for sp_when_created (20120411203253.0Z)
    
    # Month name formats
    (r"^\w{3}\s+\d{1,2},?\s+\d{4}$", "%b %d, %Y"),
    (r"^\d{1,2}\s+\w{3}\s+\d{4}$", "%d %b %Y"),
]


class FormatDateTimeClusterer(BaseClusterer):
    """
    Clusterer for date/datetime data with known formats.
    
    All valid dates (any format) go to good_data.
    Invalid dates go to bad_data.
    Tracks majority format for correction phase.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.min_year = config.get("min_year", 1900) if config else 1900
        self.max_year = config.get("max_year", 2100) if config else 2100
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        **kwargs
    ) -> ClusteringResult:
        """
        Cluster datetime data - only majority format goes to good.
        Other valid formats go to bad for correction.
        """
        indices = self._prepare_indices(data, indices)
        
        # Phase 1: Parse all values and count formats
        parsed_results = []  # (value, idx, parsed, format)
        format_counts = Counter()
        
        for value, idx in zip(data, indices):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                parsed_results.append((value, idx, None, None))
                continue
            
            str_val = str(value).strip()
            parsed, fmt = self._parse_datetime(str_val)
            
            if parsed and self._validate_components(parsed):
                parsed_results.append((value, idx, parsed, fmt))
                format_counts[fmt or "unknown"] += 1
            else:
                parsed_results.append((value, idx, None, None))
        
        # Determine majority format
        majority_format = None
        if format_counts:
            majority_format = format_counts.most_common(1)[0][0]
        
        # Phase 2: Classify based on format consistency
        good_data, bad_data = [], []
        good_indices, bad_indices = [], []
        
        for value, idx, parsed, fmt in parsed_results:
            if parsed is None:
                # Invalid date
                bad_data.append(value)
                bad_indices.append(idx)
            elif fmt == majority_format:
                # Matches majority format - GOOD
                good_data.append(value)
                good_indices.append(idx)
            else:
                # Valid date but different format - BAD for correction
                bad_data.append(value)
                bad_indices.append(idx)
        
        fingerprint = self._generate_fingerprint(good_data, format_counts, majority_format)
        confidence = self._calculate_confidence(len(good_data), len(data))
        
        return ClusteringResult(
            good_data=good_data,
            bad_data=bad_data,
            good_indices=good_indices,
            bad_indices=bad_indices,
            fingerprint=fingerprint,
            method="datetime_format_parser",
            confidence=confidence,
            metadata={
                "column_name": column_name,
                "majority_format": majority_format,
                "format_distribution": dict(format_counts),
                "format_consistency_enforced": True,
            }
        )
    
    def _parse_datetime(self, value: str) -> Tuple[Optional[datetime], Optional[str]]:
        """Try to parse datetime value with known formats."""
        # Try pattern matching first
        for pattern, fmt in FORMAT_PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                try:
                    # Handle ISO format timezone suffix
                    clean_val = re.sub(r"[+-]\d{2}:?\d{2}$", "", value)
                    clean_val = clean_val.replace("Z", "").split(".")[0]
                    
                    parsed = datetime.strptime(clean_val, fmt)
                    return parsed, fmt
                except ValueError:
                    continue
        
        # Fallback to dateutil for natural language
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value)
            return parsed, "dateutil"
        except Exception:
            pass
        
        return None, None
    
    def _validate_components(self, dt: datetime) -> bool:
        """Validate date components are realistic."""
        if dt.year < self.min_year or dt.year > self.max_year:
            return False
        # Month and day are already validated by parsing
        return True
    
    def _generate_fingerprint(
        self,
        values: List[Any],
        format_counts: Counter,
        majority_format: Optional[str]
    ) -> Dict[str, Any]:
        """Generate fingerprint from parsed dates."""
        return {
            "workflow": "datetime",
            "method": "format_parser",
            "sample_size": len(values),
            "properties": {
                "majority_format": majority_format,
                "format_distribution": dict(format_counts),
                "unique_formats": len(format_counts),
            },
            "correction_hints": {
                "expected_format": majority_format,
                "enforce_format_consistency": True,
            },
            "rules_applied": {
                "format_consistency": True,
            }
        }
