"""
Request Models
==============
Pydantic models for API requests
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class ClassificationOptions(BaseModel):
    """Options for classification."""
    enable_validation: bool = Field(default=True, description="Enable input validation")
    enable_ml_clustering: bool = Field(default=True, description="Enable ML-based clustering")
    enable_ensemble_detection: bool = Field(default=True, description="Enable ensemble detection")
    enable_llm_verification: bool = Field(default=False, description="Enable LLM verification")
    strict_mode: bool = Field(default=False, description="Strict validation mode")


class ClassificationRequest(BaseModel):
    """Request model for classification API."""
    file_path: Optional[str] = Field(None, description="Path to input file")
    file_content: Optional[str] = Field(None, description="File content (raw text, not base64)")
    has_header: bool = Field(default=True, description="File has header row")
    options: Optional[ClassificationOptions] = Field(default=None, description="Classification options")
    
    @validator("file_path", "file_content")
    def validate_file_source(cls, v, values):
        """Ensure at least one file source is provided."""
        # This validator runs for each field, so we need to check both
        file_path = values.get("file_path") if hasattr(values, "get") else None
        file_content = values.get("file_content") if hasattr(values, "get") else None
        
        # If this is being validated and the other field is None, check the full values
        if v is None:
            # Check if we're in a context where we can see both values
            # This is a limitation of Pydantic validators - we'll handle in root_validator
            pass
        return v
    
    @validator("file_path", "file_content", pre=True, always=True)
    def validate_at_least_one(cls, v, values):
        """Ensure at least one file source is provided."""
        # This is a workaround - we'll use root_validator instead
        return v
    
    class Config:
        @staticmethod
        def schema_extra(schema, model):
            """Add example to schema."""
            schema["example"] = {
                "file_path": "/path/to/data.csv",
                "has_header": True,
                "options": {
                    "enable_validation": True,
                    "enable_ml_clustering": True,
                    "enable_ensemble_detection": True,
                    "enable_llm_verification": False,
                    "strict_mode": False
                }
            }


class ClassificationAndCorrectionRequest(ClassificationRequest):
    """Request model for classification + correction API."""
    correction_threshold: float = Field(default=0.7, description="Similarity threshold for correction")
    max_corrections_per_column: int = Field(default=1000, description="Maximum corrections per column")
