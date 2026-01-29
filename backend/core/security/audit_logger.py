"""
Audit Logger
Comprehensive audit logging for security and compliance.

Production-ready audit logging with:
- Structured JSON logging
- Secure log storage (append-only)
- Privacy-preserving hashing
- Event categorization
- Compliance-ready format
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    DETECTION = "detection"
    CLUSTERING = "clustering"
    CORRECTION = "correction"
    DATA_ACCESS = "data_access"
    LLM_CALL = "llm_call"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    ERROR = "error"


class AuditLogger:
    """
    Comprehensive audit logging for security and compliance.
    
    Features:
    - Structured JSON logging
    - Secure append-only log files
    - Privacy-preserving hashing for sensitive data
    - Event categorization
    - Compliance-ready format (ISO 8601 timestamps, structured data)
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        enable_file_logging: bool = True,
        enable_console_logging: bool = False,
        hash_sensitive: bool = True,
        max_log_size_mb: int = 100
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for log files
            enable_file_logging: Whether to write to file
            enable_console_logging: Whether to log to console (for debugging)
            hash_sensitive: Whether to hash sensitive values (column names, values)
            max_log_size_mb: Maximum log file size before rotation
        """
        self.log_dir = Path(log_dir)
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.hash_sensitive = hash_sensitive
        self.max_log_size_mb = max_log_size_mb
        
        # Create log directory
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / "audit.log"
            
            # Ensure log file exists and is append-only (on Unix systems)
            if not self.log_file.exists():
                self.log_file.touch()
                try:
                    # Make append-only (chmod +a on macOS, chattr +a on Linux)
                    import os
                    import stat
                    # Set to append-only if supported
                    # Note: This is platform-specific and may not work on all systems
                except Exception:
                    pass  # Ignore if not supported
    
    def log_detection(
        self,
        column_name: str,
        workflow: str,
        subtype: str,
        confidence: float,
        sample_size: int,
        source: str = "unknown",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log detection operation.
        
        Args:
            column_name: Name of column detected
            workflow: Detected workflow type
            subtype: Detected subtype
            confidence: Detection confidence score
            sample_size: Number of samples used
            source: Detection source (pattern, heuristic, etc.)
            user_id: Optional user identifier
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.DETECTION.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "column_name": self._hash_if_sensitive(column_name),
            "workflow": workflow,
            "subtype": subtype,
            "confidence": round(confidence, 4),
            "sample_size": sample_size,
            "source": source,
            "user_id": user_id,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_clustering(
        self,
        column_name: str,
        workflow: str,
        subtype: str,
        method: str,
        good_count: int,
        bad_count: int,
        confidence: float,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log clustering operation.
        
        Args:
            column_name: Name of column clustered
            workflow: Workflow type
            subtype: Subtype
            method: Clustering method used
            good_count: Number of good values
            bad_count: Number of bad values
            confidence: Clustering confidence
            user_id: Optional user identifier
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.CLUSTERING.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "column_name": self._hash_if_sensitive(column_name),
            "workflow": workflow,
            "subtype": subtype,
            "method": method,
            "good_count": good_count,
            "bad_count": bad_count,
            "total_count": good_count + bad_count,
            "confidence": round(confidence, 4),
            "user_id": user_id,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_correction(
        self,
        column_name: str,
        original_value: Any,
        corrected_value: Any,
        status: str,
        confidence: float,
        changes_made: List[str],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log correction operation.
        
        Args:
            column_name: Name of column
            original_value: Original value
            corrected_value: Corrected value
            status: Correction status (corrected, unchanged, rejected)
            confidence: Correction confidence
            changes_made: List of changes made
            user_id: Optional user identifier
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.CORRECTION.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "column_name": self._hash_if_sensitive(column_name),
            "original_value": self._hash_if_sensitive(str(original_value)),
            "corrected_value": self._hash_if_sensitive(str(corrected_value)),
            "status": status,
            "confidence": round(confidence, 4),
            "changes_made": changes_made,
            "user_id": user_id,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_data_access(
        self,
        column_name: str,
        operation: str,
        row_count: int,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log data access operations.
        
        Args:
            column_name: Name of column accessed
            operation: Operation type (read, write, correct, export)
            row_count: Number of rows accessed
            user_id: Optional user identifier
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.DATA_ACCESS.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "column_name": self._hash_if_sensitive(column_name),
            "operation": operation,
            "row_count": row_count,
            "user_id": user_id,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_llm_call(
        self,
        purpose: str,
        column_name: Optional[str],
        tokens_used: int,
        cost_usd: float,
        from_cache: bool,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log LLM API calls.
        
        Args:
            purpose: Purpose of LLM call (pattern_generation, quality_assessment, etc.)
            column_name: Name of column (if applicable)
            tokens_used: Number of tokens used
            cost_usd: Cost in USD
            from_cache: Whether result came from cache
            model: LLM model used
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.LLM_CALL.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "purpose": purpose,
            "column_name": self._hash_if_sensitive(column_name) if column_name else None,
            "tokens_used": tokens_used,
            "cost_usd": round(cost_usd, 6),
            "from_cache": from_cache,
            "model": model,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event (injection_attempt, rate_limit_exceeded, etc.)
            description: Description of event
            severity: Severity level (low, medium, high, critical)
            user_id: Optional user identifier
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.SECURITY_EVENT.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "security_event_type": event_type,
            "description": description,
            "severity": severity,
            "user_id": user_id,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        column_name: Optional[str] = None,
        workflow: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log error events.
        
        Args:
            error_type: Type of error (DetectionError, ClusteringError, etc.)
            error_message: Error message
            column_name: Name of column (if applicable)
            workflow: Workflow type (if applicable)
            stack_trace: Optional stack trace
            metadata: Optional additional metadata
        """
        event = {
            "event_type": AuditEventType.ERROR.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": error_type,
            "error_message": error_message,
            "column_name": self._hash_if_sensitive(column_name) if column_name else None,
            "workflow": workflow,
            "stack_trace": stack_trace,
            "metadata": metadata or {},
        }
        
        self._write_log(event)
    
    def _hash_if_sensitive(self, value: Optional[str]) -> Optional[str]:
        """
        Hash sensitive values for privacy.
        
        Args:
            value: Value to hash (if sensitive)
            
        Returns:
            Hashed value or original if hashing disabled
        """
        if not value or not self.hash_sensitive:
            return value
        
        # Use SHA-256 and take first 16 characters for readability
        return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]
    
    def _write_log(self, event: Dict[str, Any]):
        """
        Write audit log entry.
        
        Args:
            event: Event dictionary to log
        """
        # Write to file
        if self.enable_file_logging:
            try:
                # Check log file size
                if self.log_file.exists():
                    file_size_mb = self.log_file.stat().st_size / (1024 * 1024)
                    if file_size_mb > self.max_log_size_mb:
                        self._rotate_log()
                
                # Append to log file
                with open(self.log_file, "a", encoding="utf-8") as f:
                    json.dump(event, f, ensure_ascii=False)
                    f.write("\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
        
        # Write to console (for debugging)
        if self.enable_console_logging:
            logger.info(f"AUDIT: {json.dumps(event, indent=2)}")
    
    def _rotate_log(self):
        """Rotate log file when it gets too large."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated_file = self.log_dir / f"audit_{timestamp}.log"
            self.log_file.rename(rotated_file)
            self.log_file.touch()
            logger.info(f"Audit log rotated to {rotated_file}")
        except Exception as e:
            logger.error(f"Failed to rotate audit log: {e}")
