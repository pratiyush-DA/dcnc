"""
API Configuration
=================
Configuration settings for the API framework
"""

import os
from pathlib import Path
from typing import Optional

# API Settings
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))
API_TITLE: str = "DCNC Data Quality API"
API_VERSION: str = "1.0.0"
API_DESCRIPTION: str = "Production-ready API for data classification and correction"

# Output Settings
# API always uses output/api subdirectory to separate from CLI outputs
_base_output = os.getenv("OUTPUT_DIR", "output")
OUTPUT_DIR: Path = Path(_base_output) / "api"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# File Settings
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
ALLOWED_EXTENSIONS: list = [".csv", ".tsv", ".xlsx", ".xls"]
TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "temp"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Processing Settings
ENABLE_ML_CLUSTERING: bool = os.getenv("ENABLE_ML_CLUSTERING", "true").lower() == "true"
ENABLE_ENSEMBLE_DETECTION: bool = os.getenv("ENABLE_ENSEMBLE_DETECTION", "true").lower() == "true"
ENABLE_LLM_VERIFICATION: bool = os.getenv("ENABLE_LLM_VERIFICATION", "false").lower() == "true"
DEFAULT_CONFIDENCE_THRESHOLD: float = float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.7"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# CORS
CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

# Job Settings
JOB_TIMEOUT: int = int(os.getenv("JOB_TIMEOUT", "300"))  # 5 minutes
CLEANUP_OLD_JOBS: bool = os.getenv("CLEANUP_OLD_JOBS", "true").lower() == "true"
JOB_RETENTION_HOURS: int = int(os.getenv("JOB_RETENTION_HOURS", "24"))
