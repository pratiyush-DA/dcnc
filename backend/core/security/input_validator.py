"""
Input Validator
Comprehensive input validation for all data sources.

Production-ready validation with:
- Column name validation
- Data value validation
- File validation
- Security pattern detection
- Resource limit enforcement
"""

import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class InputValidator:
    """
    Comprehensive input validation for all data sources.
    
    Features:
    - Column name validation (length, dangerous patterns)
    - Data value validation (length, control characters)
    - File validation (size, type, existence)
    - Security pattern detection (SQL injection, path traversal)
    - Resource limit enforcement
    """
    
    # Maximum limits
    MAX_COLUMN_NAME_LENGTH = 255
    MAX_VALUE_LENGTH = 10000
    MAX_SAMPLE_SIZE = 10000
    MAX_FILE_SIZE_MB = 100
    MAX_COLUMNS = 1000
    MAX_ROWS = 10_000_000
    MIN_ROWS = 1
    
    # Dangerous patterns for security
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
        r"(?i)(exec|execute|script|javascript:)",
        r"(?i)(--|\#|\/\*|\*\/)",  # SQL comments
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./", r"\.\.\\", r"\.\.%2f", r"\.\.%5c",  # Path traversal
        r"\.\.%252f", r"\.\.%255c",  # Double-encoded
    ]
    
    # Allowed file extensions
    ALLOWED_FILE_EXTENSIONS = {'.csv', '.tsv', '.txt'}
    
    def __init__(
        self,
        max_column_name_length: int = None,
        max_value_length: int = None,
        max_file_size_mb: int = None,
        strict_mode: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            max_column_name_length: Maximum column name length (default: 255)
            max_value_length: Maximum data value length (default: 10000)
            max_file_size_mb: Maximum file size in MB (default: 100)
            strict_mode: If True, reject invalid inputs; if False, return warnings
        """
        self.max_column_name_length = max_column_name_length or self.MAX_COLUMN_NAME_LENGTH
        self.max_value_length = max_value_length or self.MAX_VALUE_LENGTH
        self.max_file_size_mb = max_file_size_mb or self.MAX_FILE_SIZE_MB
        self.strict_mode = strict_mode
        
        # Compile patterns for performance
        self._sql_patterns = [re.compile(p) for p in self.SQL_INJECTION_PATTERNS]
        self._path_patterns = [re.compile(p) for p in self.PATH_TRAVERSAL_PATTERNS]
    
    def validate_column_name(
        self,
        column_name: str
    ) -> ValidationResult:
        """
        Validate column name for security and format.
        
        Args:
            column_name: Column name to validate
            
        Returns:
            ValidationResult with is_valid flag and optional error message
        """
        warnings = []
        
        # Check empty
        if not column_name:
            return ValidationResult(
                is_valid=False,
                error_message="Column name cannot be empty"
            )
        
        # Check length
        if len(column_name) > self.max_column_name_length:
            error = f"Column name too long: {len(column_name)} > {self.max_column_name_length}"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        # Check for SQL injection patterns
        for pattern in self._sql_patterns:
            if pattern.search(column_name):
                error = "Column name contains potentially dangerous SQL pattern"
                if self.strict_mode:
                    return ValidationResult(is_valid=False, error_message=error)
                warnings.append(error)
        
        # Check for path traversal patterns
        for pattern in self._path_patterns:
            if pattern.search(column_name):
                error = "Column name contains path traversal pattern"
                if self.strict_mode:
                    return ValidationResult(is_valid=False, error_message=error)
                warnings.append(error)
        
        # Check for null bytes
        if '\x00' in column_name:
            error = "Column name contains null byte"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings if warnings else None
        )
    
    def validate_data_value(
        self,
        value: Any,
        allow_null: bool = True
    ) -> ValidationResult:
        """
        Validate individual data value.
        
        Args:
            value: Data value to validate
            allow_null: Whether null values are allowed
            
        Returns:
            ValidationResult
        """
        warnings = []
        
        # Handle null values
        if value is None:
            if allow_null:
                return ValidationResult(is_valid=True)
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message="Null values are not allowed"
                )
        
        str_value = str(value)
        
        # Check length
        if len(str_value) > self.max_value_length:
            error = f"Value too long: {len(str_value)} > {self.max_value_length} characters"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        # Check for null bytes
        if '\x00' in str_value:
            error = "Value contains null byte"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        # Check for control characters (except newline, tab, carriage return)
        # Allow: \n (0x0A), \t (0x09), \r (0x0D)
        control_chars = re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', str_value)
        if control_chars:
            error = "Value contains invalid control characters"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(f"Control character found at position {control_chars.start()}")
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings if warnings else None
        )
    
    def validate_file(
        self,
        file_path: str
    ) -> ValidationResult:
        """
        Validate input file.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            ValidationResult
        """
        warnings = []
        path = Path(file_path)
        
        # Check file exists
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"File does not exist: {file_path}"
            )
        
        # Check if it's a file (not directory)
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path is not a file: {file_path}"
            )
        
        # Check file size
        try:
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                error = f"File too large: {file_size_mb:.2f}MB > {self.max_file_size_mb}MB"
                if self.strict_mode:
                    return ValidationResult(is_valid=False, error_message=error)
                warnings.append(error)
        except OSError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Cannot access file: {e}"
            )
        
        # Check file extension
        if path.suffix.lower() not in self.ALLOWED_FILE_EXTENSIONS:
            error = f"Unsupported file type: {path.suffix}. Allowed: {self.ALLOWED_FILE_EXTENSIONS}"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        # Check if file is readable
        if not path.stat().st_mode & 0o444:  # Check read permission
            return ValidationResult(
                is_valid=False,
                error_message="File is not readable"
            )
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings if warnings else None
        )
    
    def validate_dataset(
        self,
        row_count: int,
        column_count: int,
        empty_columns: List[str] = None,
        duplicate_columns: List[str] = None
    ) -> ValidationResult:
        """
        Validate dataset characteristics.
        
        Args:
            row_count: Number of rows in dataset
            column_count: Number of columns in dataset
            empty_columns: List of completely empty column names
            duplicate_columns: List of duplicate column names
            
        Returns:
            ValidationResult
        """
        warnings = []
        
        # Check row count
        if row_count < self.MIN_ROWS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Dataset has too few rows: {row_count} < {self.MIN_ROWS}"
            )
        
        if row_count > self.MAX_ROWS:
            warning = f"Dataset is very large: {row_count:,} rows (max recommended: {self.MAX_ROWS:,})"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=warning)
            warnings.append(warning)
        
        # Check column count
        if column_count > self.MAX_COLUMNS:
            error = f"Too many columns: {column_count} > {self.MAX_COLUMNS}"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        # Check for empty columns
        if empty_columns:
            warning = f"Empty columns detected: {empty_columns[:5]}"  # Show first 5
            if len(empty_columns) > 5:
                warning += f" (and {len(empty_columns) - 5} more)"
            warnings.append(warning)
        
        # Check for duplicate columns
        if duplicate_columns:
            error = f"Duplicate column names: {duplicate_columns}"
            if self.strict_mode:
                return ValidationResult(is_valid=False, error_message=error)
            warnings.append(error)
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings if warnings else None
        )
    
    def validate_sample_size(
        self,
        sample_size: int
    ) -> ValidationResult:
        """
        Validate sample size for detection.
        
        Args:
            sample_size: Number of samples
            
        Returns:
            ValidationResult
        """
        if sample_size < 1:
            return ValidationResult(
                is_valid=False,
                error_message="Sample size must be at least 1"
            )
        
        if sample_size > self.MAX_SAMPLE_SIZE:
            warning = f"Large sample size: {sample_size} (max recommended: {self.MAX_SAMPLE_SIZE})"
            return ValidationResult(
                is_valid=True,
                warnings=[warning]
            )
        
        return ValidationResult(is_valid=True)
