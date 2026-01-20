"""
String Fingerprint Generator
Captures characteristics of string/text data
"""

import re
from typing import Any, Dict, List, Optional
from collections import Counter

from .base_fingerprint import BaseFingerprint
from ..registry import register_fingerprint


@register_fingerprint("text")
class StringFingerprint(BaseFingerprint):
    """
    Fingerprint generator for string/text data.
    
    Captures:
    - Length statistics (avg, min, max, std)
    - Case style (title, upper, lower, mixed)
    - Word count statistics
    - Character composition (alpha, numeric, special)
    - Pattern signatures
    - Common prefixes/suffixes
    """
    
    @property
    def workflow_type(self) -> str:
        return "text"
    
    def _generate_properties(
        self,
        data: List[Any],
        subtype: str
    ) -> Dict[str, Any]:
        """Generate string-specific properties"""
        if not data:
            return {}
        
        # Convert all to strings
        str_data = [str(d) for d in data]
        
        # Length statistics
        lengths = [len(s) for s in str_data]
        
        # Word count statistics  
        word_counts = [len(s.split()) for s in str_data]
        
        # Character composition
        alpha_ratios = []
        numeric_ratios = []
        special_ratios = []
        
        for s in str_data:
            if len(s) > 0:
                alpha_ratios.append(sum(c.isalpha() for c in s) / len(s))
                numeric_ratios.append(sum(c.isdigit() for c in s) / len(s))
                special_ratios.append(
                    sum(not c.isalnum() and not c.isspace() for c in s) / len(s)
                )
        
        # Detect case style
        case_style = self._detect_case_style(str_data)
        
        # Find common prefixes/suffixes
        prefixes = self._find_common_affixes(str_data, prefix=True)
        suffixes = self._find_common_affixes(str_data, prefix=False)
        
        # Check for patterns
        has_numbers = any(any(c.isdigit() for c in s) for s in str_data)
        has_special = any(any(not c.isalnum() and not c.isspace() for c in s) for s in str_data)
        
        # Detect charset
        charset = self._detect_charset(str_data)
        
        return {
            # Length properties
            "avg_length": self.safe_mean(lengths),
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
            "length_std": self.safe_stdev(lengths),
            
            # Word count properties
            "avg_word_count": self.safe_mean(word_counts),
            "min_word_count": min(word_counts) if word_counts else 0,
            "max_word_count": max(word_counts) if word_counts else 0,
            
            # Character composition
            "avg_alpha_ratio": self.safe_mean(alpha_ratios),
            "avg_numeric_ratio": self.safe_mean(numeric_ratios),
            "avg_special_ratio": self.safe_mean(special_ratios),
            
            # Style
            "case_style": case_style,
            "has_numbers": has_numbers,
            "has_special_chars": has_special,
            
            # Common patterns
            "common_prefixes": prefixes,
            "common_suffixes": suffixes,
            
            # Charset
            "charset": charset,
            
            # Subtype-specific
            "subtype": subtype,
        }
    
    def _detect_case_style(self, data: List[str]) -> str:
        """
        Detect the predominant case style.
        
        Returns:
            'upper', 'lower', 'title', 'sentence', or 'mixed'
        """
        if not data:
            return "mixed"
        
        styles = Counter()
        
        for s in data:
            s = s.strip()
            if not s:
                continue
            
            if s.isupper():
                styles["upper"] += 1
            elif s.islower():
                styles["lower"] += 1
            elif s.istitle():
                styles["title"] += 1
            elif s[0].isupper() and s[1:].islower() if len(s) > 1 else s[0].isupper():
                styles["sentence"] += 1
            else:
                styles["mixed"] += 1
        
        if not styles:
            return "mixed"
        
        # Return most common style if it's dominant
        most_common = styles.most_common(1)[0]
        if most_common[1] / len(data) > 0.6:
            return most_common[0]
        
        return "mixed"
    
    def _find_common_affixes(
        self, 
        data: List[str], 
        prefix: bool = True,
        min_length: int = 2,
        max_length: int = 5
    ) -> List[str]:
        """Find common prefixes or suffixes"""
        if not data or len(data) < 3:
            return []
        
        affix_counter = Counter()
        
        for s in data:
            s = s.strip()
            for length in range(min_length, min(max_length + 1, len(s))):
                if prefix:
                    affix = s[:length]
                else:
                    affix = s[-length:]
                affix_counter[affix] += 1
        
        # Return affixes that appear in at least 30% of data
        threshold = len(data) * 0.3
        common = [
            affix for affix, count in affix_counter.most_common(5)
            if count >= threshold
        ]
        
        return common
    
    def _detect_charset(self, data: List[str]) -> str:
        """Detect the character set used"""
        all_chars = "".join(data)
        
        try:
            all_chars.encode("ascii")
            return "ascii"
        except UnicodeEncodeError:
            pass
        
        try:
            all_chars.encode("latin-1")
            return "latin-1"
        except UnicodeEncodeError:
            pass
        
        return "unicode"
    
    def _generate_signature(self, data: List[Any]) -> Optional[str]:
        """
        Generate a pattern signature representing the data structure.
        
        Uses:
        - A = uppercase letter
        - a = lowercase letter
        - 9 = digit
        - _ = space
        - * = other character
        """
        if not data:
            return None
        
        signatures = []
        for value in data[:20]:  # Sample first 20
            sig = self._value_to_signature(str(value))
            signatures.append(sig)
        
        # Return most common signature
        sig_counter = Counter(signatures)
        most_common = sig_counter.most_common(1)
        
        if most_common:
            return most_common[0][0]
        
        return None
    
    def _value_to_signature(self, value: str) -> str:
        """Convert a value to its pattern signature"""
        sig = []
        prev_char_type = None
        
        for char in value:
            if char.isupper():
                char_type = "A"
            elif char.islower():
                char_type = "a"
            elif char.isdigit():
                char_type = "9"
            elif char.isspace():
                char_type = "_"
            else:
                char_type = char  # Keep actual special character
            
            # Collapse consecutive same types (except specials)
            if char_type in "Aa9_" and char_type == prev_char_type:
                continue
            
            sig.append(char_type)
            prev_char_type = char_type
        
        return "".join(sig)
    
    def get_correction_hints(
        self,
        fingerprint: FingerprintData,
        bad_value: Any
    ) -> Dict[str, Any]:
        """Get string-specific correction hints"""
        props = fingerprint.properties
        bad_str = str(bad_value)
        
        hints = {
            "target_pattern": fingerprint.pattern_signature,
            "target_case": props.get("case_style", "mixed"),
            "target_length_range": (
                props.get("min_length", 0),
                props.get("max_length", 100)
            ),
            "issues": [],
        }
        
        # Detect issues
        if len(bad_str) < props.get("min_length", 0):
            hints["issues"].append("too_short")
        if len(bad_str) > props.get("max_length", 1000):
            hints["issues"].append("too_long")
        
        # Case mismatch
        target_case = props.get("case_style", "mixed")
        if target_case == "title" and not bad_str.istitle():
            hints["issues"].append("wrong_case")
        elif target_case == "upper" and not bad_str.isupper():
            hints["issues"].append("wrong_case")
        elif target_case == "lower" and not bad_str.islower():
            hints["issues"].append("wrong_case")
        
        return hints
    
    def calculate_similarity(
        self,
        fingerprint: FingerprintData,
        value: Any
    ) -> float:
        """Calculate string similarity to fingerprint"""
        props = fingerprint.properties
        val_str = str(value)
        
        scores = []
        
        # Length similarity
        avg_len = props.get("avg_length", len(val_str))
        if avg_len > 0:
            len_score = 1 - abs(len(val_str) - avg_len) / avg_len
            scores.append(max(0, len_score))
        
        # Case match
        if props.get("case_style") == self._detect_case_style([val_str]):
            scores.append(1.0)
        else:
            scores.append(0.3)
        
        # Pattern match
        val_sig = self._value_to_signature(val_str)
        if val_sig == fingerprint.pattern_signature:
            scores.append(1.0)
        else:
            scores.append(0.5)
        
        return sum(scores) / len(scores) if scores else 0.5
