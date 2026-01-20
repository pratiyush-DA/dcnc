"""
Person Name Validation Engine
Validates person name format and structure
"""

import re
from typing import List, Tuple

from .base_engine import BaseEngine
from ..registry import register_validator


@register_validator("name")
class NameEngine(BaseEngine):
    """
    Person name validation engine.
    
    Validates:
    - Word count (2-4 words typically)
    - Alpha ratio (>70%)
    - No excessive numbers
    - Reasonable length
    """
    
    # Common name prefixes/suffixes to preserve
    NAME_PREFIXES = {"Mr", "Mrs", "Ms", "Dr", "Prof"}
    NAME_SUFFIXES = {"Jr", "Sr", "II", "III", "IV", "PhD", "MD"}
    
    @property
    def name(self) -> str:
        return "name"
    
    @property
    def description(self) -> str:
        return "Validates person name format (2-4 words, high alpha ratio)"
    
    @property
    def patterns(self) -> List[str]:
        return []  # Use heuristic validation instead
    
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """Validate normalized name value"""
        # Remove punctuation except periods and hyphens
        clean = re.sub(r"[^\w\s.\-']", "", value)
        
        # Split into words
        words = clean.split()
        
        if not words:
            return False, 0.0
        
        # Check word count (1-5 words is reasonable)
        if len(words) < 1 or len(words) > 5:
            return False, 0.0
        
        # Calculate alpha ratio
        alpha_chars = sum(c.isalpha() for c in value)
        total_chars = len(value.replace(" ", ""))
        
        if total_chars == 0:
            return False, 0.0
        
        alpha_ratio = alpha_chars / total_chars
        
        # Names should be mostly letters
        if alpha_ratio < 0.7:
            return False, 0.0
        
        confidence = 1.0
        
        # Check for numbers (unusual in names)
        if any(c.isdigit() for c in value):
            confidence = 0.5
        
        # Check for all uppercase (could be abbreviation)
        if value.isupper() and len(value) <= 3:
            confidence = 0.6
        
        # Check word length (each word should be reasonable)
        for word in words:
            clean_word = word.strip(".-'")
            if len(clean_word) < 1:
                continue
            if len(clean_word) > 20:
                confidence = 0.7
        
        # Boost confidence for proper case
        if self._is_proper_case(value):
            confidence = min(1.0, confidence + 0.1)
        
        # Lower confidence for single word (might be first name only)
        if len(words) == 1:
            confidence = min(confidence, 0.8)
        
        return True, confidence
    
    def _is_proper_case(self, value: str) -> bool:
        """Check if name is in proper title case"""
        words = value.split()
        
        for word in words:
            clean = word.strip(".-'")
            if not clean:
                continue
            
            # Skip known prefixes/suffixes
            if clean in self.NAME_PREFIXES or clean in self.NAME_SUFFIXES:
                continue
            
            # First letter should be uppercase
            if clean[0].islower():
                return False
        
        return True
    
    def format_name(self, name: str) -> str:
        """Format name to proper title case"""
        words = name.split()
        formatted = []
        
        for word in words:
            # Check for suffixes that should stay uppercase
            clean = word.strip(".-'")
            if clean.upper() in self.NAME_SUFFIXES:
                formatted.append(clean.upper())
            elif clean.lower() in {"de", "von", "van", "la", "le"}:
                # Common lowercase particles
                formatted.append(clean.lower())
            else:
                formatted.append(word.title())
        
        return " ".join(formatted)
