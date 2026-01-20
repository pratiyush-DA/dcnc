"""
Identifier Fingerprint Generator
Captures pattern characteristics of ID/identifier data
"""

import re
from typing import Any, Dict, List, Optional
from collections import Counter

from .base_fingerprint import BaseFingerprint
from ..registry import register_fingerprint


@register_fingerprint("identifier")
class IdentifierFingerprint(BaseFingerprint):
    """
    Fingerprint generator for identifier data.
    
    Captures:
    - Pattern signature (e.g., AAA-9999)
    - Length characteristics
    - Separator type
    - Prefix/suffix patterns
    - Numeric padding
    - Case style
    """
    
    @property
    def workflow_type(self) -> str:
        return "identifier"
    
    def _generate_properties(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """Generate identifier-specific properties"""
        if not data:
            return {}
        
        str_data = [str(d).strip() for d in data if d is not None]
        
        if not str_data:
            return {}
        
        # Length statistics
        lengths = [len(s) for s in str_data]
        
        # Separator detection
        separator = self._detect_separator(str_data)
        
        # Pattern analysis
        patterns = [self._value_to_pattern(s) for s in str_data]
        pattern_counts = Counter(patterns)
        majority_pattern = pattern_counts.most_common(1)[0][0] if patterns else None
        
        # Part analysis (split by separator)
        parts_analysis = self._analyze_parts(str_data, separator)
        
        # Prefix/suffix detection
        prefix = self._detect_common_prefix(str_data)
        suffix = self._detect_common_suffix(str_data)
        
        # Case style
        case_style = self._detect_case_style(str_data)
        
        # Numeric padding detection
        padding = self._detect_numeric_padding(str_data)
        
        # Check if pure numeric
        is_pure_numeric = all(s.isdigit() for s in str_data)
        
        return {
            # Length
            "avg_length": self.safe_mean(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "fixed_length": len(set(lengths)) == 1,
            
            # Pattern
            "pattern_signature": majority_pattern,
            "pattern_consistency": pattern_counts[majority_pattern] / len(str_data) if majority_pattern else 0,
            "unique_patterns": len(pattern_counts),
            
            # Structure
            "separator": separator,
            "parts_count": parts_analysis.get("count", 1),
            "parts_types": parts_analysis.get("types", []),
            
            # Affixes
            "prefix": prefix,
            "suffix": suffix,
            
            # Style
            "case_style": case_style,
            "numeric_padding": padding,
            "is_pure_numeric": is_pure_numeric,
            
            # Subtype
            "subtype": subtype,
        }
    
    def _value_to_pattern(self, value: str) -> str:
        """
        Convert a value to its pattern signature.
        
        Uses:
        - A = uppercase letter(s)
        - a = lowercase letter(s)
        - 9 = digit(s)
        - Keeps separator characters as-is
        """
        pattern = []
        prev_type = None
        
        for char in value:
            if char.isupper():
                curr_type = "A"
            elif char.islower():
                curr_type = "a"
            elif char.isdigit():
                curr_type = "9"
            else:
                # Separator or special char - keep as is
                pattern.append(char)
                prev_type = None
                continue
            
            # Only add if different from previous
            if curr_type != prev_type:
                pattern.append(curr_type)
                prev_type = curr_type
        
        return "".join(pattern)
    
    def _detect_separator(self, data: List[str]) -> Optional[str]:
        """Detect the common separator character"""
        separators = Counter()
        candidates = ["-", "_", "/", ".", " ", ":"]
        
        for value in data:
            for sep in candidates:
                if sep in value:
                    separators[sep] += value.count(sep)
        
        if separators:
            # Return most common separator
            most_common = separators.most_common(1)[0]
            if most_common[1] >= len(data) * 0.5:
                return most_common[0]
        
        return None
    
    def _analyze_parts(
        self, 
        data: List[str], 
        separator: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze ID parts separated by separator"""
        if not separator:
            return {"count": 1, "types": ["mixed"]}
        
        parts_info = Counter()
        
        for value in data:
            parts = value.split(separator)
            parts_count = len(parts)
            
            # Analyze each part
            part_types = []
            for part in parts:
                if part.isdigit():
                    part_types.append("numeric")
                elif part.isalpha():
                    part_types.append("alpha")
                else:
                    part_types.append("mixed")
            
            parts_info[(parts_count, tuple(part_types))] += 1
        
        if parts_info:
            most_common = parts_info.most_common(1)[0][0]
            return {
                "count": most_common[0],
                "types": list(most_common[1]),
            }
        
        return {"count": 1, "types": ["mixed"]}
    
    def _detect_common_prefix(self, data: List[str]) -> Optional[str]:
        """Detect common prefix"""
        if not data or len(data) < 2:
            return None
        
        # Find longest common prefix
        prefix = data[0]
        for value in data[1:]:
            while not value.startswith(prefix) and prefix:
                prefix = prefix[:-1]
        
        # Only return if meaningful (at least 2 chars, appears in 70%+)
        if len(prefix) >= 2:
            match_ratio = sum(1 for v in data if v.startswith(prefix)) / len(data)
            if match_ratio >= 0.7:
                return prefix
        
        return None
    
    def _detect_common_suffix(self, data: List[str]) -> Optional[str]:
        """Detect common suffix"""
        if not data or len(data) < 2:
            return None
        
        # Find longest common suffix
        suffix = data[0]
        for value in data[1:]:
            while not value.endswith(suffix) and suffix:
                suffix = suffix[1:]
        
        # Only return if meaningful
        if len(suffix) >= 2:
            match_ratio = sum(1 for v in data if v.endswith(suffix)) / len(data)
            if match_ratio >= 0.7:
                return suffix
        
        return None
    
    def _detect_case_style(self, data: List[str]) -> str:
        """Detect predominant case style"""
        styles = Counter()
        
        for value in data:
            alpha_chars = "".join(c for c in value if c.isalpha())
            if alpha_chars:
                if alpha_chars.isupper():
                    styles["upper"] += 1
                elif alpha_chars.islower():
                    styles["lower"] += 1
                else:
                    styles["mixed"] += 1
            else:
                styles["none"] += 1
        
        if styles:
            return styles.most_common(1)[0][0]
        
        return "none"
    
    def _detect_numeric_padding(self, data: List[str]) -> Optional[int]:
        """Detect zero-padding width for numeric parts"""
        paddings = Counter()
        
        for value in data:
            # Find numeric sequences
            numeric_parts = re.findall(r"\d+", value)
            for part in numeric_parts:
                if part.startswith("0"):
                    paddings[len(part)] += 1
        
        if paddings:
            return paddings.most_common(1)[0][0]
        
        return None
    
    def _generate_signature(self, data: List[Any]) -> Optional[str]:
        """Generate majority pattern signature"""
        if not data:
            return None
        
        patterns = [self._value_to_pattern(str(d)) for d in data]
        pattern_counts = Counter(patterns)
        
        if pattern_counts:
            return pattern_counts.most_common(1)[0][0]
        
        return None
    
    def get_correction_hints(
        self,
        fingerprint: FingerprintData,
        bad_value: Any
    ) -> Dict[str, Any]:
        """Get identifier-specific correction hints"""
        props = fingerprint.properties
        bad_str = str(bad_value)
        
        hints = {
            "target_pattern": props.get("pattern_signature"),
            "target_length": int(props.get("avg_length", len(bad_str))),
            "separator": props.get("separator"),
            "prefix": props.get("prefix"),
            "suffix": props.get("suffix"),
            "case_style": props.get("case_style"),
            "numeric_padding": props.get("numeric_padding"),
            "issues": [],
        }
        
        # Detect issues
        bad_pattern = self._value_to_pattern(bad_str)
        
        if bad_pattern != props.get("pattern_signature"):
            hints["issues"].append("pattern_mismatch")
        
        if props.get("fixed_length") and len(bad_str) != props.get("avg_length"):
            hints["issues"].append("length_mismatch")
        
        if props.get("prefix") and not bad_str.startswith(props["prefix"]):
            hints["issues"].append("missing_prefix")
        
        if props.get("suffix") and not bad_str.endswith(props["suffix"]):
            hints["issues"].append("missing_suffix")
        
        return hints
    
    def calculate_similarity(
        self,
        fingerprint: FingerprintData,
        value: Any
    ) -> float:
        """Calculate identifier similarity to fingerprint"""
        props = fingerprint.properties
        val_str = str(value)
        
        scores = []
        
        # Pattern match
        val_pattern = self._value_to_pattern(val_str)
        if val_pattern == props.get("pattern_signature"):
            scores.append(1.0)
        else:
            scores.append(0.3)
        
        # Length match
        if props.get("fixed_length"):
            if len(val_str) == props.get("avg_length"):
                scores.append(1.0)
            else:
                scores.append(0.2)
        else:
            min_len = props.get("min_length", 0)
            max_len = props.get("max_length", 100)
            if min_len <= len(val_str) <= max_len:
                scores.append(0.8)
            else:
                scores.append(0.3)
        
        # Prefix/suffix match
        if props.get("prefix"):
            if val_str.startswith(props["prefix"]):
                scores.append(1.0)
            else:
                scores.append(0.2)
        
        return sum(scores) / len(scores) if scores else 0.5
