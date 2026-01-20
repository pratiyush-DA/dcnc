"""
Base Validation Engine
Abstract base class for all validation engines with strict validation
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..interfaces import IValidator, ValidationResult

logger = logging.getLogger(__name__)


class BaseEngine(IValidator, ABC):
    """
    Base class for all validation engines.
    
    Provides:
    - Common pattern matching logic
    - Validation result formatting
    - Pattern match ratio calculation for clustering
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    @abstractmethod
    def patterns(self) -> List[str]:
        """Regex patterns for validation (compiled on first use)"""
        pass
    
    _compiled_patterns: Optional[List[re.Pattern]] = None
    
    def _get_compiled_patterns(self) -> List[re.Pattern]:
        """Get compiled regex patterns"""
        if self._compiled_patterns is None:
            self._compiled_patterns = []
            for pattern in self.patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns.append(compiled)
                except re.error as e:
                    logger.warning(f"Invalid pattern in {self.name}: {pattern} - {e}")
        return self._compiled_patterns
    
    def validate(self, value: Any) -> Tuple[bool, float]:
        """
        Validate a value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, confidence)
        """
        if value is None:
            return False, 0.0
        
        str_val = str(value).strip()
        if not str_val:
            return False, 0.0
        
        # Normalize
        normalized = self.normalize(str_val)
        
        # Check patterns first (strict)
        for pattern in self._get_compiled_patterns():
            if pattern.fullmatch(normalized):
                # Additional validation
                is_valid, confidence = self._validate_normalized(normalized)
                return is_valid, confidence
        
        # Pattern didn't match - invalid
        return False, 0.0
    
    @abstractmethod
    def _validate_normalized(self, value: str) -> Tuple[bool, float]:
        """
        Validate normalized value. Override in subclasses.
        
        Args:
            value: Normalized string value
            
        Returns:
            Tuple of (is_valid, confidence)
        """
        pass
    
    def normalize(self, value: str) -> str:
        """
        Normalize value for validation.
        Override in subclasses for specific normalization.
        
        Args:
            value: Raw string value
            
        Returns:
            Normalized value
        """
        return value.strip()
    
    def get_pattern_match_ratio(self, data: List[str]) -> float:
        """
        Calculate ratio of values matching validation patterns.
        Used for subtype detection and clustering.
        
        Args:
            data: List of string values
            
        Returns:
            Ratio of matching values (0.0 to 1.0)
        """
        if not data:
            return 0.0
        
        match_count = 0
        for value in data:
            is_valid, confidence = self.validate(value)
            if is_valid and confidence >= 0.5:
                match_count += 1
        
        return match_count / len(data)
    
    def get_correction_suggestion(
        self,
        value: str
    ) -> Optional[str]:
        """
        Get correction suggestion for invalid value.
        Override in subclasses for specific corrections.
        
        Args:
            value: Invalid value
            
        Returns:
            Suggested correction or None
        """
        return None
