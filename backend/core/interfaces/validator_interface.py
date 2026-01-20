"""
Validator Interface
Base interface for all validation engines (Email, Phone, URL, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """
    Result of validation operation.
    """
    is_valid: bool
    confidence: float = 1.0
    
    # Specific issues found
    issues: List[str] = field(default_factory=list)
    
    # Normalized/cleaned value (if any cleaning was applied)
    normalized_value: Optional[Any] = None
    
    # Validation details
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context"""
        return self.is_valid


class IValidator(ABC):
    """
    Abstract base class for all validation engines.
    
    Validators check if data values conform to expected patterns/rules
    for a specific data type (email, phone, age, etc.).
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this validator"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this validator checks"""
        pass
    
    @property
    def patterns(self) -> List[str]:
        """Regex patterns used for validation (if any)"""
        return []
    
    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, float]:
        """
        Validate a single value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, confidence)
            - is_valid: Whether the value passes validation
            - confidence: 0.0 to 1.0 confidence in the result
        """
        pass
    
    def validate_detailed(self, value: Any) -> ValidationResult:
        """
        Validate with detailed results.
        
        Args:
            value: Value to validate
            
        Returns:
            ValidationResult with full details
        """
        is_valid, confidence = self.validate(value)
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=[] if is_valid else [f"Failed {self.name} validation"],
        )
    
    def validate_batch(
        self, 
        values: List[Any]
    ) -> List[Tuple[bool, float]]:
        """
        Validate multiple values.
        
        Args:
            values: List of values to validate
            
        Returns:
            List of (is_valid, confidence) tuples
        """
        return [self.validate(v) for v in values]
    
    def normalize(self, value: Any) -> Any:
        """
        Normalize/clean a value before validation.
        Override in subclasses for specific normalization.
        
        Args:
            value: Value to normalize
            
        Returns:
            Normalized value
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value
    
    def can_validate(self, value: Any) -> bool:
        """
        Check if this validator can handle the given value type.
        
        Args:
            value: Value to check
            
        Returns:
            True if validator can handle this value
        """
        return value is not None
    
    def get_pattern_match_ratio(self, values: List[Any]) -> float:
        """
        Calculate what ratio of values match this validator.
        Useful for auto-detecting data types.
        
        Args:
            values: Sample of values to check
            
        Returns:
            Ratio of values that pass validation (0.0 to 1.0)
        """
        if not values:
            return 0.0
        
        valid_count = sum(1 for v in values if self.validate(v)[0])
        return valid_count / len(values)
