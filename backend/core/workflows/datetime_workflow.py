"""
DateTime Workflow
Handles date and datetime data types
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from .base_workflow import BaseWorkflow
from ..interfaces import WorkflowType, ClusterResult
from ..registry import register_workflow
from ..clustering import get_clusterer

logger = logging.getLogger(__name__)


# Common date format patterns
FORMAT_PATTERNS = [
    # ISO formats
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    
    # US formats
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y"),
    
    # European formats
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),
    (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y"),
    
    # Other
    (r"^\d{8}$", "%Y%m%d"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
]


@register_workflow("datetime")
class DateTimeWorkflow(BaseWorkflow):
    """
    DateTime workflow handler.
    
    Key Features:
    - Accepts ALL valid datetime formats into good_data (Bug Fix #4)
    - Detects majority format for standardization during correction
    - Validates date components (month 1-12, day 1-31, etc.)
    
    Subtypes:
    - date
    - datetime
    - generic (fallback)
    """
    
    SUBTYPES = ["date", "datetime", "time", "generic"]
    
    @property
    def workflow_type(self) -> WorkflowType:
        return WorkflowType.DATETIME
    
    @property
    def supported_subtypes(self) -> List[str]:
        return self.SUBTYPES
    
    @property
    def default_subtype(self) -> str:
        return "generic"
    
    def detect_subtype(
        self,
        data: List[Any],
        column_name: Optional[str] = None
    ) -> Tuple[str, float]:
        """Detect datetime subtype (date, datetime, or time)"""
        if not data:
            return self.default_subtype, 0.3
        
        str_data = [str(v).strip() for v in data if v is not None and str(v).strip()]
        
        if not str_data:
            return self.default_subtype, 0.3
        
        # Check column name hints first
        if column_name:
            col_lower = column_name.lower()
            if "time" in col_lower and "date" not in col_lower:
                return "time", 0.9
            elif "date" in col_lower and "time" not in col_lower:
                return "date", 0.9
        
        # Analyze data patterns
        has_time = any(":" in s for s in str_data)
        has_date = any(
            any(char.isdigit() for char in s[:4]) and len(s) >= 8 
            for s in str_data
        )
        
        # Time-only pattern: HH:MM:SS or HH:MM (no date components)
        time_only_pattern = r'^\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?$'
        import re
        time_only_count = sum(1 for s in str_data if re.match(time_only_pattern, s))
        
        if time_only_count > len(str_data) * 0.7:  # 70% are time-only
            return "time", 0.85
        elif has_time and has_date:
            return "datetime", 0.8
        elif has_date:
            return "date", 0.8
        else:
            return self.default_subtype, 0.5
    
    def cluster(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        **kwargs
    ) -> ClusterResult:
        """
        Cluster datetime data.
        
        IMPORTANT: All valid datetime formats go to good_data.
        The majority format is recorded for correction phase.
        """
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        if indices is None:
            indices = list(range(len(data)))
        
        good_data = []
        bad_data = []
        good_indices = []
        bad_indices = []
        format_counts = Counter()
        
        for value, idx in zip(data, indices):
            # Skip nulls
            if value is None or str(value).strip() == "":
                bad_data.append(value)
                bad_indices.append(idx)
                continue
            
            str_val = str(value).strip()
            
            # Try to parse and validate
            parsed, detected_format = self._parse_datetime(str_val)
            
            if parsed:
                # Valid datetime - add to good regardless of format
                good_data.append(value)
                good_indices.append(idx)
                
                if detected_format:
                    format_counts[detected_format] += 1
            else:
                bad_data.append(value)
                bad_indices.append(idx)
        
        # Detect majority format for correction
        majority_format = None
        if format_counts:
            majority_format = format_counts.most_common(1)[0][0]
        
        # Generate fingerprint
        fingerprint_dict = None
        if good_data:
            fingerprint_dict = self.generate_fingerprint(good_data, subtype)
            fingerprint_dict["majority_format"] = majority_format
            fingerprint_dict["format_counts"] = dict(format_counts)
            fingerprint_dict["method"] = "format_parsing"  # Track method
        
        # Calculate confidence
        total = len(good_data) + len(bad_data)
        confidence = len(good_data) / total if total > 0 else 0.0
        
        # Determine method
        method = "format_parsing"  # DateTime always uses format parsing
        
        result = ClusterResult(
            good_data=good_data,
            bad_data=bad_data,
            workflow=self.workflow_type.value,
            subtype=subtype,
            confidence=confidence,
            fingerprint=fingerprint_dict,
            target_format=majority_format,  # For correction
            good_indices=good_indices,
            bad_indices=bad_indices,
            metadata={
                "column_name": column_name,
                "method": method,  # Track method
                "total_records": total,
                "majority_format": majority_format,
            }
        )
        
        return result
    
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
                    
                    # Validate date components
                    if not self._validate_date_components(parsed):
                        return None, None
                    
                    return parsed, format_str
                except ValueError:
                    continue
        
        # Try generic parsing as last resort
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value)
            
            if self._validate_date_components(parsed):
                return parsed, None  # Unknown format
        except Exception:
            pass
        
        return None, None
    
    def _validate_date_components(self, dt: datetime) -> bool:
        """
        Validate date components are realistic.
        Rejects invalid dates like 2023-13-45.
        """
        # Month check
        if dt.month < 1 or dt.month > 12:
            return False
        
        # Day check (basic - datetime parsing handles this)
        if dt.day < 1 or dt.day > 31:
            return False
        
        # Year check (reasonable range)
        if dt.year < 1900 or dt.year > 2100:
            return False
        
        return True
    
    def cluster_v2(
        self,
        data: List[Any],
        indices: Optional[List[int]] = None,
        column_name: Optional[str] = None,
        subtype: Optional[str] = None,
        use_ml: bool = True,
        **kwargs
    ) -> ClusterResult:
        """
        Production-grade clustering using fuzzy datetime parsing.
        
        Uses the new clustering module with:
        - Multi-format parsing for date/datetime subtypes
        - Fuzzy parsing (Unix timestamps, ISO 8601, natural language) for generic
        """
        if not use_ml:
            return self.cluster(data, indices, column_name, subtype, **kwargs)
        
        if not subtype:
            subtype, _ = self.detect_subtype(data, column_name)
        
        try:
            clusterer = get_clusterer("datetime", subtype)
            result = clusterer.cluster(data, indices, column_name, **kwargs)
            
            return ClusterResult(
                good_data=result.good_data,
                bad_data=result.bad_data,
                workflow=self.workflow_type.value,
                subtype=subtype,
                confidence=result.confidence,
                fingerprint=result.fingerprint,
                target_format=result.fingerprint.get("properties", {}).get("majority_format"),
                good_indices=result.good_indices,
                bad_indices=result.bad_indices,
                metadata={
                    "column_name": column_name,
                    "total_records": result.total_count,
                    "clustering_method": result.method,
                    **result.metadata,
                }
            )
        except Exception as e:
            logger.warning(f"ML clustering failed: {e}, falling back to legacy")
            return self.cluster(data, indices, column_name, subtype, **kwargs)

