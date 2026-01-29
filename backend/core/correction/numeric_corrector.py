"""
Numeric Corrector
Correction engine for numeric data types
Handles currency formats, European decimals, and semantic constraints
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from .base_corrector import BaseCorrector
from ..interfaces import CorrectionResult, CorrectionStatus
from ..registry import register_corrector

logger = logging.getLogger(__name__)


@register_corrector("numeric")
@register_corrector("generic_numeric")
@register_corrector("age")
@register_corrector("rating")
@register_corrector("salary")
@register_corrector("amount")
@register_corrector("percentage")
@register_corrector("year")
class NumericCorrector(BaseCorrector):
    """
    Correction engine for numeric data.
    
    Corrections supported:
    - Currency parsing ($150,000 → 150000)
    - European decimal handling (4,9 → 4.9)
    - Range clamping based on semantic constraints
    - Integer rounding
    - Decimal place adjustment
    """
    
    # Currency symbols to strip
    CURRENCY_SYMBOLS = {"$", "€", "£", "¥", "₹", "CHF", "USD", "EUR", "GBP"}
    
    @property
    def name(self) -> str:
        return "numeric_corrector"
    
    @property
    def description(self) -> str:
        return "Corrects numeric data including currency and European formats"
    
    @property
    def supported_subtypes(self) -> List[str]:
        return [
            "age", "year", "salary", "amount", "count",
            "rating", "percentage", "temperature",
            "latitude", "longitude", "generic",
        ]
    
    def _correct_value(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]],
        learned_patterns: Dict[str, Any],
        subtype: Optional[str],
        column_name: Optional[str],
        **kwargs
    ) -> CorrectionResult:
        """Correct numeric value"""
        # Handle NaN/null values early
        import math
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return self._make_rejected_result(value, "null_or_nan")
        
        str_val = str(value).strip()
        
        # Check for NaN string representations
        if str_val.lower() in ["nan", "null", "none", "na", "n/a", ""]:
            return self._make_rejected_result(value, "null_or_nan")
        
        changes = []
        
        # Step 0: Fix subtype detection using column name hints (for coordinates)
        # This ensures longitude_coord uses longitude constraints, not latitude
        actual_subtype = self._determine_actual_subtype(subtype, column_name)
        
        # Step 1: Parse the value (handle currency, European decimals)
        parsed_value, parse_changes = self._parse_numeric(str_val)
        
        if parsed_value is None or math.isnan(parsed_value):
            return self._make_rejected_result(value, "not_numeric")
        
        changes.extend(parse_changes)
        corrected = parsed_value
        
        # Step 2: Get constraints using actual subtype
        constraints = self._get_semantic_constraints(actual_subtype)
        if learned_patterns:
            # Override with fingerprint constraints if available
            if "min" in learned_patterns:
                constraints["min"] = learned_patterns["min"]
            if "max" in learned_patterns:
                constraints["max"] = learned_patterns["max"]
            if "is_integer" in learned_patterns:
                constraints["type"] = "integer" if learned_patterns["is_integer"] else "float"
        
        # Step 3: Apply semantic constraints with smart clamping
        min_val = constraints.get("min")
        max_val = constraints.get("max")
        is_integer = constraints.get("type") == "integer"
        
        # Smart clamping: Use fingerprint statistics for better reference values
        if fingerprint:
            stats = fingerprint.get("statistics", {})
            if actual_subtype in ("latitude", "longitude"):
                # For coordinates, use median from good data instead of hard bounds
                median = stats.get("median")
                if median is not None:
                    # Clamp to reasonable range around median
                    if actual_subtype == "latitude":
                        min_val = max(-90, min_val or -90)
                        max_val = min(90, max_val or 90)
                    else:  # longitude
                        min_val = max(-180, min_val or -180)
                        max_val = min(180, max_val or 180)
                    
                    # If value is way out of bounds, clamp to median instead of edge
                    if corrected < min_val:
                        corrected = max(min_val, median - 10)  # Clamp closer to median
                        changes.append(f"clamped_min_{corrected:.4f}")
                    elif corrected > max_val:
                        corrected = min(max_val, median + 10)  # Clamp closer to median
                        changes.append(f"clamped_max_{corrected:.4f}")
                else:
                    # Fallback to standard clamping
                    if min_val is not None and corrected < min_val:
                        corrected = min_val
                        changes.append(f"clamped_min_{min_val}")
                    if max_val is not None and corrected > max_val:
                        corrected = max_val
                        changes.append(f"clamped_max_{max_val}")
            else:
                # Standard clamping for other numeric types
                if min_val is not None and corrected < min_val:
                    corrected = min_val
                    changes.append(f"clamped_min_{min_val}")
                if max_val is not None and corrected > max_val:
                    corrected = max_val
                    changes.append(f"clamped_max_{max_val}")
        else:
            # No fingerprint - use standard clamping
            if min_val is not None and corrected < min_val:
                corrected = min_val
                changes.append(f"clamped_min_{min_val}")
            if max_val is not None and corrected > max_val:
                corrected = max_val
                changes.append(f"clamped_max_{max_val}")
        
        # Integer rounding
        if is_integer and corrected != int(corrected):
            corrected = round(corrected)
            changes.append("rounded_to_integer")
        
        if changes:
            # Format output
            output = int(corrected) if is_integer else corrected
            return self._make_corrected_result(value, output, changes)
        
        return self._make_unchanged_result(value)
    
    def _parse_numeric(self, value: str) -> Tuple[Optional[float], List[str]]:
        """
        Parse numeric value, handling various formats.
        
        Handles:
        - Currency: $150,000 → 150000
        - European decimal: 4,9 → 4.9
        - Thousand separators: 1,000,000 → 1000000
        
        Returns:
            Tuple of (parsed_value, list_of_changes)
        """
        changes = []
        clean = value.strip()
        
        # Check for currency symbols
        has_currency = False
        for symbol in self.CURRENCY_SYMBOLS:
            if symbol in clean:
                clean = clean.replace(symbol, "")
                has_currency = True
        
        if has_currency:
            changes.append("currency_stripped")
        
        clean = clean.strip()
        
        # Handle different formats
        
        # Case 1: European decimal (e.g., "4,9" or "1234,56")
        # Pattern: digits followed by comma and 1-2 digits at end
        if re.match(r"^\d+,\d{1,2}$", clean):
            clean = clean.replace(",", ".")
            changes.append("european_decimal_converted")
        
        # Case 2: US/UK thousand separators (e.g., "1,000,000")
        # Pattern: comma every 3 digits
        elif re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", clean):
            clean = clean.replace(",", "")
            changes.append("thousand_separator_removed")
        
        # Case 3: European thousand separators (e.g., "1.000.000,50")
        elif re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", clean):
            clean = clean.replace(".", "").replace(",", ".")
            changes.append("european_format_converted")
        
        # Case 4: Simple number with commas (just remove all commas)
        elif "," in clean:
            clean = clean.replace(",", "")
            if "." not in clean:
                changes.append("comma_removed")
        
        # Try to parse
        try:
            result = float(clean)
            return result, changes
        except (ValueError, TypeError):
            return None, []
    
    def _determine_actual_subtype(self, subtype: Optional[str], column_name: Optional[str]) -> str:
        """
        Determine actual subtype using column name hints.
        Fixes cases where longitude is misclassified as latitude.
        """
        if not column_name:
            return subtype or "generic"
        
        column_lower = column_name.lower()
        
        # Priority: Check column name patterns first
        if "longitude" in column_lower or "lng" in column_lower or "lon" in column_lower:
            if "latitude" not in column_lower:  # Don't override if both present
                return "longitude"
        
        if "latitude" in column_lower or "lat" in column_lower:
            if "longitude" not in column_lower:  # Don't override if both present
                return "latitude"
        
        # Return detected subtype if column name doesn't provide hints
        return subtype or "generic"
    
    def _get_semantic_constraints(self, subtype: Optional[str]) -> Dict[str, Any]:
        """Get semantic constraints for a subtype"""
        constraints = {
            "age": {"min": 0, "max": 120, "type": "integer"},
            "rating": {"min": 0, "max": 10, "type": "float"},
            "year": {"min": 1900, "max": 2100, "type": "integer"},
            "latitude": {"min": -90, "max": 90, "type": "float"},
            "longitude": {"min": -180, "max": 180, "type": "float"},
            "percentage": {"min": 0, "max": 100, "type": "float"},
            "temperature": {"min": -273.15, "max": 1000, "type": "float"},
            "salary": {"min": 0, "type": "float"},  # No max for salary
            "amount": {"min": 0, "type": "float"},  # No max for amount
            "count": {"min": 0, "type": "integer"},
        }
        return constraints.get(subtype, {})
    
    def can_correct(
        self,
        value: Any,
        fingerprint: Optional[Dict[str, Any]] = None,
        subtype: Optional[str] = None,
    ) -> Tuple[bool, float]:
        """Check if value can be corrected"""
        if value is None:
            return False, 0.0
        
        str_val = str(value).strip()
        if not str_val:
            return False, 0.0
        
        # Try to parse
        parsed, _ = self._parse_numeric(str_val)
        if parsed is not None:
            return True, 0.9
        
        return False, 0.0
