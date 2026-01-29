"""
Custom Exception Hierarchy
Structured exceptions for better error handling and debugging.
"""

from typing import Any, Dict, Optional


class DataQualityError(Exception):
    """Base exception for all data quality issues."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class DetectionError(DataQualityError):
    """Error during detection phase."""
    
    def __init__(
        self,
        message: str,
        column_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.column_name = column_name
        self.details = details or {}
        self.details["column_name"] = column_name


class ClusteringError(DataQualityError):
    """Error during clustering phase."""
    
    def __init__(
        self,
        message: str,
        workflow: str,
        subtype: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.workflow = workflow
        self.subtype = subtype
        self.details = details or {}
        self.details["workflow"] = workflow
        self.details["subtype"] = subtype


class CorrectionError(DataQualityError):
    """Error during correction phase."""
    
    def __init__(
        self,
        message: str,
        original_value: Any,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.original_value = original_value
        self.details = details or {}
        self.details["original_value"] = str(original_value)[:100]  # Truncate long values


class ValidationError(DataQualityError):
    """Error during validation phase."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.field_name = field_name
        self.details = details or {}
        if field_name:
            self.details["field_name"] = field_name


class SecurityError(DataQualityError):
    """Security-related error."""
    
    def __init__(
        self,
        message: str,
        event_type: str,
        severity: str = "medium",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.event_type = event_type
        self.severity = severity
        self.details = details or {}
        self.details["event_type"] = event_type
        self.details["severity"] = severity


class CircuitBreakerOpenError(DataQualityError):
    """Error when circuit breaker is open."""
    
    def __init__(
        self,
        service_name: str,
        failure_count: int,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Circuit breaker is open for {service_name} (failures: {failure_count})"
        super().__init__(message, details)
        self.service_name = service_name
        self.failure_count = failure_count
        self.details = details or {}
        self.details["service_name"] = service_name
        self.details["failure_count"] = failure_count
