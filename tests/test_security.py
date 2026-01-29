"""
Test Suite for Security Components
Tests for input validation, sanitization, and audit logging.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from backend.core.security import InputValidator, DataSanitizer, AuditLogger
from backend.core.security.input_validator import ValidationResult


class TestInputValidator:
    """Tests for InputValidator."""
    
    def test_validate_column_name_valid(self):
        """Test validation of valid column names."""
        validator = InputValidator()
        
        result = validator.validate_column_name("user_email")
        assert result.is_valid is True
        assert result.error_message is None
    
    def test_validate_column_name_empty(self):
        """Test validation of empty column name."""
        validator = InputValidator()
        
        result = validator.validate_column_name("")
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()
    
    def test_validate_column_name_too_long(self):
        """Test validation of column name that's too long."""
        validator = InputValidator(max_column_name_length=10)
        
        result = validator.validate_column_name("a" * 20)
        assert result.is_valid is False
        assert "too long" in result.error_message.lower()
    
    def test_validate_column_name_sql_injection(self):
        """Test detection of SQL injection patterns."""
        validator = InputValidator()
        
        result = validator.validate_column_name("user'; DROP TABLE users; --")
        assert result.is_valid is False
        assert "dangerous" in result.error_message.lower() or "sql" in result.error_message.lower()
    
    def test_validate_column_name_path_traversal(self):
        """Test detection of path traversal patterns."""
        validator = InputValidator()
        
        result = validator.validate_column_name("../../etc/passwd")
        assert result.is_valid is False
        assert "path" in result.error_message.lower() or "traversal" in result.error_message.lower()
    
    def test_validate_data_value_valid(self):
        """Test validation of valid data values."""
        validator = InputValidator()
        
        result = validator.validate_data_value("test@example.com")
        assert result.is_valid is True
    
    def test_validate_data_value_null_allowed(self):
        """Test validation of null values when allowed."""
        validator = InputValidator()
        
        result = validator.validate_data_value(None, allow_null=True)
        assert result.is_valid is True
    
    def test_validate_data_value_null_not_allowed(self):
        """Test validation of null values when not allowed."""
        validator = InputValidator()
        
        result = validator.validate_data_value(None, allow_null=False)
        assert result.is_valid is False
    
    def test_validate_data_value_too_long(self):
        """Test validation of value that's too long."""
        validator = InputValidator(max_value_length=10)
        
        result = validator.validate_data_value("a" * 20)
        assert result.is_valid is False
        assert "too long" in result.error_message.lower()
    
    def test_validate_data_value_control_chars(self):
        """Test detection of control characters."""
        validator = InputValidator()
        
        result = validator.validate_data_value("test\x00value")
        assert result.is_valid is False
        assert "control" in result.error_message.lower() or "null" in result.error_message.lower()
    
    def test_validate_file_valid(self):
        """Test validation of valid file."""
        validator = InputValidator()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("test,data\n1,2\n")
            temp_path = f.name
        
        try:
            result = validator.validate_file(temp_path)
            assert result.is_valid is True
        finally:
            Path(temp_path).unlink()
    
    def test_validate_file_not_exists(self):
        """Test validation of non-existent file."""
        validator = InputValidator()
        
        result = validator.validate_file("/nonexistent/file.csv")
        assert result.is_valid is False
        assert "not exist" in result.error_message.lower() or "does not exist" in result.error_message.lower()
    
    def test_validate_file_wrong_extension(self):
        """Test validation of file with wrong extension."""
        validator = InputValidator()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("test")
            temp_path = f.name
        
        try:
            result = validator.validate_file(temp_path)
            assert result.is_valid is False
            assert "unsupported" in result.error_message.lower() or "extension" in result.error_message.lower()
        finally:
            Path(temp_path).unlink()
    
    def test_validate_dataset_valid(self):
        """Test validation of valid dataset."""
        validator = InputValidator()
        
        result = validator.validate_dataset(
            row_count=100,
            column_count=10
        )
        assert result.is_valid is True
    
    def test_validate_dataset_too_few_rows(self):
        """Test validation of dataset with too few rows."""
        validator = InputValidator()
        
        result = validator.validate_dataset(row_count=0, column_count=10)
        assert result.is_valid is False
        assert "too few" in result.error_message.lower()
    
    def test_validate_dataset_too_many_columns(self):
        """Test validation of dataset with too many columns."""
        validator = InputValidator()
        
        result = validator.validate_dataset(
            row_count=100,
            column_count=2000,
            strict_mode=True
        )
        assert result.is_valid is False
        assert "too many" in result.error_message.lower()


class TestDataSanitizer:
    """Tests for DataSanitizer."""
    
    def test_sanitize_value_basic(self):
        """Test basic value sanitization."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_value("  test  ")
        assert result == "test"
    
    def test_sanitize_value_null_bytes(self):
        """Test removal of null bytes."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_value("test\x00value")
        assert "\x00" not in result
    
    def test_sanitize_value_control_chars(self):
        """Test removal of control characters."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_value("test\x01value")
        assert "\x01" not in result
    
    def test_sanitize_value_preserve_format(self):
        """Test format preservation."""
        sanitizer = DataSanitizer(preserve_format=True)
        
        result = sanitizer.sanitize_value("test   value\n\nline2")
        assert "   " not in result  # Multiple spaces normalized
        assert "\n" in result  # Newlines preserved
    
    def test_sanitize_value_normalize_whitespace(self):
        """Test complete whitespace normalization."""
        sanitizer = DataSanitizer(preserve_format=False)
        
        result = sanitizer.sanitize_value("test   value\n\nline2")
        assert "\n" not in result  # All whitespace normalized to spaces
    
    def test_sanitize_column_name_basic(self):
        """Test basic column name sanitization."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_column_name("user email")
        assert result == "user_email"
        assert " " not in result
    
    def test_sanitize_column_name_dangerous_chars(self):
        """Test removal of dangerous characters."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_column_name("user@email#test")
        assert "@" not in result
        assert "#" not in result
    
    def test_sanitize_column_name_starts_with_number(self):
        """Test handling of column names starting with numbers."""
        sanitizer = DataSanitizer()
        
        result = sanitizer.sanitize_column_name("123column")
        assert result.startswith("col_")
    
    def test_sanitize_batch(self):
        """Test batch sanitization."""
        sanitizer = DataSanitizer()
        
        values = ["  test1  ", "test\x002", "test3"]
        results = sanitizer.sanitize_batch(values)
        
        assert len(results) == 3
        assert results[0] == "test1"
        assert "\x00" not in results[1]
        assert results[2] == "test3"


class TestAuditLogger:
    """Tests for AuditLogger."""
    
    def test_log_detection(self):
        """Test detection logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir, hash_sensitive=False)
            
            logger.log_detection(
                column_name="test_column",
                workflow="text",
                subtype="email",
                confidence=0.9,
                sample_size=100
            )
            
            # Check log file was created
            log_file = Path(tmpdir) / "audit.log"
            assert log_file.exists()
            
            # Check log entry
            with open(log_file) as f:
                lines = f.readlines()
                assert len(lines) == 1
                
                entry = json.loads(lines[0])
                assert entry["event_type"] == "detection"
                assert entry["column_name"] == "test_column"
                assert entry["workflow"] == "text"
                assert entry["subtype"] == "email"
    
    def test_log_clustering(self):
        """Test clustering logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir, hash_sensitive=False)
            
            logger.log_clustering(
                column_name="test_column",
                workflow="text",
                subtype="email",
                method="validator",
                good_count=80,
                bad_count=20,
                confidence=0.8
            )
            
            log_file = Path(tmpdir) / "audit.log"
            with open(log_file) as f:
                entry = json.loads(f.readline())
                assert entry["event_type"] == "clustering"
                assert entry["good_count"] == 80
                assert entry["bad_count"] == 20
    
    def test_log_llm_call(self):
        """Test LLM call logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir, hash_sensitive=False)
            
            logger.log_llm_call(
                purpose="pattern_generation",
                column_name="test_column",
                tokens_used=100,
                cost_usd=0.001,
                from_cache=False
            )
            
            log_file = Path(tmpdir) / "audit.log"
            with open(log_file) as f:
                entry = json.loads(f.readline())
                assert entry["event_type"] == "llm_call"
                assert entry["tokens_used"] == 100
                assert entry["cost_usd"] == 0.001
    
    def test_hash_sensitive(self):
        """Test sensitive data hashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir, hash_sensitive=True)
            
            logger.log_detection(
                column_name="sensitive_column",
                workflow="text",
                subtype="email",
                confidence=0.9,
                sample_size=100
            )
            
            log_file = Path(tmpdir) / "audit.log"
            with open(log_file) as f:
                entry = json.loads(f.readline())
                # Column name should be hashed
                assert entry["column_name"] != "sensitive_column"
                assert len(entry["column_name"]) == 16  # SHA-256 first 16 chars
    
    def test_log_security_event(self):
        """Test security event logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir, hash_sensitive=False)
            
            logger.log_security_event(
                event_type="injection_attempt",
                description="SQL injection pattern detected",
                severity="high"
            )
            
            log_file = Path(tmpdir) / "audit.log"
            with open(log_file) as f:
                entry = json.loads(f.readline())
                assert entry["event_type"] == "security_event"
                assert entry["severity"] == "high"
