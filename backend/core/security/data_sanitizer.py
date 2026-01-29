"""
Data Sanitizer
Sanitizes data values for safe processing.

Production-ready sanitization with:
- Null byte removal
- Whitespace normalization
- Control character removal
- Column name sanitization
- Format preservation options
"""

import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataSanitizer:
    """
    Sanitizes data values for safe processing.
    
    Features:
    - Removes dangerous characters (null bytes, control chars)
    - Normalizes whitespace (configurable)
    - Sanitizes column names
    - Preserves data format when possible
    """
    
    # Control characters to remove (keep newline, tab, carriage return)
    # \x00-\x08: null, start of heading, start of text, etc.
    # \x0b-\x0c: vertical tab, form feed
    # \x0e-\x1f: shift out, data link escape, etc.
    # \x7f: DEL
    CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]')
    
    # Excessive whitespace patterns
    MULTIPLE_SPACES = re.compile(r'[ \t]+')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')
    
    def __init__(
        self,
        preserve_format: bool = True,
        normalize_whitespace: bool = True,
        max_length: int = 10000
    ):
        """
        Initialize sanitizer.
        
        Args:
            preserve_format: If True, preserve whitespace structure; if False, normalize completely
            normalize_whitespace: If True, normalize excessive whitespace
            max_length: Maximum length after sanitization (truncate if longer)
        """
        self.preserve_format = preserve_format
        self.normalize_whitespace = normalize_whitespace
        self.max_length = max_length
    
    def sanitize_value(
        self,
        value: Any,
        preserve_format: Optional[bool] = None
    ) -> Any:
        """
        Sanitize a data value while preserving format when possible.
        
        Args:
            value: Data value to sanitize
            preserve_format: Override instance setting (optional)
            
        Returns:
            Sanitized value (same type as input if possible)
        """
        if value is None:
            return None
        
        preserve = preserve_format if preserve_format is not None else self.preserve_format
        original_type = type(value)
        str_value = str(value)
        
        # Remove null bytes (always remove, dangerous)
        str_value = str_value.replace('\x00', '')
        
        # Remove control characters (except newline, tab, carriage return)
        str_value = self.CONTROL_CHAR_PATTERN.sub('', str_value)
        
        # Normalize whitespace
        if self.normalize_whitespace:
            if preserve:
                # Preserve structure: normalize excessive whitespace only
                str_value = self.MULTIPLE_SPACES.sub(' ', str_value)  # Multiple spaces -> single
                str_value = self.MULTIPLE_NEWLINES.sub('\n\n', str_value)  # Multiple newlines -> double
            else:
                # Complete normalization: collapse all whitespace
                str_value = ' '.join(str_value.split())
        
        # Trim
        str_value = str_value.strip()
        
        # Enforce max length
        if len(str_value) > self.max_length:
            logger.warning(f"Value truncated from {len(str_value)} to {self.max_length} characters")
            str_value = str_value[:self.max_length]
        
        # Try to return in original type if possible
        if original_type == int:
            try:
                return int(str_value)
            except ValueError:
                pass
        elif original_type == float:
            try:
                return float(str_value)
            except ValueError:
                pass
        elif original_type == bool:
            # Preserve boolean type
            return str_value.lower() in ('true', '1', 'yes', 'y', 't')
        
        return str_value
    
    def sanitize_column_name(
        self,
        column_name: str,
        max_length: int = 255
    ) -> str:
        """
        Sanitize column name for safe use.
        
        Args:
            column_name: Column name to sanitize
            max_length: Maximum length (default: 255)
            
        Returns:
            Sanitized column name
        """
        if not column_name:
            return "unnamed_column"
        
        # Remove dangerous characters (keep alphanumeric, spaces, hyphens, underscores)
        sanitized = re.sub(r'[^\w\s-]', '', str(column_name))
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        
        # Remove leading/trailing underscores/hyphens
        sanitized = sanitized.strip('_-')
        
        # Ensure it's not empty after sanitization
        if not sanitized:
            sanitized = "unnamed_column"
        
        # Enforce max length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip('_-')
        
        # Ensure it doesn't start with a number (invalid in many systems)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        
        return sanitized
    
    def sanitize_batch(
        self,
        values: list,
        preserve_format: Optional[bool] = None
    ) -> list:
        """
        Sanitize a batch of values.
        
        Args:
            values: List of values to sanitize
            preserve_format: Override instance setting (optional)
            
        Returns:
            List of sanitized values
        """
        return [
            self.sanitize_value(value, preserve_format)
            for value in values
        ]
    
    def sanitize_dataframe_columns(
        self,
        column_names: list
    ) -> dict:
        """
        Sanitize all column names in a dataframe.
        
        Args:
            column_names: List of column names
            
        Returns:
            Dictionary mapping original -> sanitized names
        """
        mapping = {}
        seen = set()
        counter = 1
        
        for col in column_names:
            sanitized = self.sanitize_column_name(col)
            
            # Handle duplicates
            original_sanitized = sanitized
            while sanitized in seen:
                sanitized = f"{original_sanitized}_{counter}"
                counter += 1
            
            seen.add(sanitized)
            mapping[col] = sanitized
        
        return mapping
