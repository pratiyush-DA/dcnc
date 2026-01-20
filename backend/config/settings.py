"""
Application Settings and Configuration
Loads settings from environment variables and configuration files
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class LLMSettings:
    """LLM-specific settings"""
    api_key: str = ""
    model: str = "llama3-8b-8192"
    provider: str = "groq"
    max_retries: int = 3
    timeout: int = 30


@dataclass
class DetectionSettings:
    """Detection layer settings"""
    cache_path: str = "data/detection_cache.db"
    enable_caching: bool = True
    confidence_threshold: float = 0.7


@dataclass
class PipelineSettings:
    """Pipeline execution settings"""
    enable_llm_verification: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    batch_size: int = 1000


@dataclass
class OutputSettings:
    """Output generation settings"""
    output_dir: str = "output"
    generate_detailed_report: bool = True
    include_rejected: bool = True


@dataclass
class Settings:
    """
    Main application settings container.
    Loads configuration from environment variables with sensible defaults.
    """
    llm: LLMSettings = field(default_factory=LLMSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "Settings":
        """
        Load settings from environment variables.
        
        Args:
            env_file: Optional path to .env file
            
        Returns:
            Settings instance with loaded configuration
        """
        # Load environment file if specified or exists
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        settings = cls()
        
        # LLM Settings
        settings.llm.api_key = os.getenv("GROQ_API_KEY", "")
        settings.llm.model = os.getenv("LLM_MODEL", "llama3-8b-8192")
        settings.llm.provider = os.getenv("LLM_PROVIDER", "groq")
        settings.llm.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        settings.llm.timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        
        # Detection Settings
        settings.detection.cache_path = os.getenv(
            "DETECTION_CACHE_PATH", 
            "data/detection_cache.db"
        )
        settings.detection.enable_caching = os.getenv(
            "ENABLE_PATTERN_CACHING", 
            "true"
        ).lower() == "true"
        settings.detection.confidence_threshold = float(
            os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.7")
        )
        
        # Pipeline Settings
        settings.pipeline.enable_llm_verification = os.getenv(
            "ENABLE_LLM_VERIFICATION", 
            "true"
        ).lower() == "true"
        settings.pipeline.parallel_processing = os.getenv(
            "PARALLEL_PROCESSING", 
            "true"
        ).lower() == "true"
        settings.pipeline.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        settings.pipeline.batch_size = int(os.getenv("BATCH_SIZE", "1000"))
        
        # Output Settings
        settings.output.output_dir = os.getenv("OUTPUT_DIR", "output")
        settings.output.generate_detailed_report = os.getenv(
            "GENERATE_DETAILED_REPORT", 
            "true"
        ).lower() == "true"
        
        # Logging
        settings.log_level = os.getenv("LOG_LEVEL", "INFO")
        settings.log_file = os.getenv("LOG_FILE")
        
        return settings
    
    def get_cache_path(self) -> Path:
        """Get absolute path to detection cache"""
        return self.project_root / self.detection.cache_path
    
    def get_output_dir(self) -> Path:
        """Get absolute path to output directory"""
        return self.project_root / self.output.output_dir


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance, loading if necessary"""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings
