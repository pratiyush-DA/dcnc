"""
File Utilities
==============
File handling utilities for the API
"""

import base64
import logging
from pathlib import Path
from typing import Optional
import tempfile

from ..config import TEMP_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


class FileHandler:
    """Handler for file operations."""
    
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def prepare_file(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[str] = None,
        job_id: str = None
    ) -> Path:
        """
        Prepare file for processing.
        
        Args:
            file_path: Path to file
            file_content: File content (base64 or raw)
            job_id: Job identifier
            
        Returns:
            Path to prepared file
        """
        if file_path:
            # Use provided file path
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            return path
        
        elif file_content:
            # Save content to temporary file
            # TODO: Handle base64 decoding
            temp_file = self.temp_dir / f"{job_id}_input.csv"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(file_content)
            return temp_file
        
        else:
            raise ValueError("Either file_path or file_content must be provided")
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate file before processing."""
        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size
        if file_path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_path.stat().st_size} bytes (max: {MAX_FILE_SIZE})")
        
        # Check file extension
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        return True
