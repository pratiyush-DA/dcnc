"""
Response Models
==============
Pydantic models for API responses
"""

from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FilePaths(BaseModel):
    """File paths in response."""
    good_data: str = Field(..., description="Path to good data file")
    bad_data: str = Field(..., description="Path to bad data file")
    reject_data: str = Field(..., description="Path to reject data file")
    fingerprint: str = Field(..., description="Path to fingerprint JSON file")
    final_file: str = Field(..., description="Path to final file (good records only, excluding rejects)")


class ClassificationStatistics(BaseModel):
    """Statistics for classification."""
    total_rows: int = Field(..., description="Total rows processed")
    good_rows: int = Field(..., description="Number of good rows")
    bad_rows: int = Field(..., description="Number of bad rows")
    reject_rows: int = Field(..., description="Number of rejected rows")
    final_rows: int = Field(..., description="Number of rows in final file (good only, excluding rejects)")
    columns_processed: int = Field(..., description="Number of columns processed")
    total_good_values: int = Field(..., description="Total good values")
    total_bad_values: int = Field(..., description="Total bad values")


class ClassificationMetadata(BaseModel):
    """Metadata for classification."""
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Processing timestamp")
    job_id: str = Field(..., description="Job identifier")


class ClassificationResponse(BaseModel):
    """Response model for classification API."""
    status: str = Field(..., description="Status of the request")
    job_id: str = Field(..., description="Job identifier")
    files: FilePaths = Field(..., description="Generated file paths")
    statistics: ClassificationStatistics = Field(..., description="Processing statistics")
    metadata: ClassificationMetadata = Field(..., description="Processing metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "files": {
                    "good_data": "output/550e8400/good_data.csv",
                    "bad_data": "output/550e8400/bad_data.csv",
                    "reject_data": "output/550e8400/reject_data.csv",
                    "fingerprint": "output/550e8400/fingerprint.json",
                    "final_file": "output/550e8400/final_file.csv"
                },
                "statistics": {
                    "total_rows": 1000,
                    "good_rows": 950,
                    "bad_rows": 30,
                    "reject_rows": 20,
                    "final_rows": 950,
                    "columns_processed": 36,
                    "total_good_values": 34200,
                    "total_bad_values": 1080
                },
                "metadata": {
                    "processing_time": 12.5,
                    "timestamp": "2026-01-27T10:00:00Z",
                    "job_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }


class CorrectionFilePaths(FilePaths):
    """File paths including correction files."""
    corrected_data: str = Field(..., description="Path to corrected data file")
    correction_report: str = Field(..., description="Path to correction report JSON file")
    final_file: str = Field(..., description="Path to final file (good + corrected records, excluding rejects)")


class CorrectionStatistics(ClassificationStatistics):
    """Statistics including correction data."""
    corrected_rows: int = Field(..., description="Number of corrected rows")
    corrections_applied: int = Field(..., description="Total corrections applied")
    corrections_rejected: int = Field(..., description="Number of corrections rejected")


class ClassificationAndCorrectionResponse(BaseModel):
    """Response model for classification + correction API."""
    status: str = Field(..., description="Status of the request")
    job_id: str = Field(..., description="Job identifier")
    files: CorrectionFilePaths = Field(..., description="Generated file paths")
    statistics: CorrectionStatistics = Field(..., description="Processing statistics")
    metadata: ClassificationMetadata = Field(..., description="Processing metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "files": {
                    "good_data": "output/550e8400/good_data.csv",
                    "bad_data": "output/550e8400/bad_data.csv",
                    "corrected_data": "output/550e8400/corrected_data.csv",
                    "reject_data": "output/550e8400/reject_data.csv",
                    "fingerprint": "output/550e8400/fingerprint.json",
                    "correction_report": "output/550e8400/correction_report.json",
                    "final_file": "output/550e8400/final_file.csv"
                },
                "statistics": {
                    "total_rows": 1000,
                    "good_rows": 950,
                    "bad_rows": 30,
                    "corrected_rows": 25,
                    "reject_rows": 5,
                    "final_rows": 975,
                    "columns_processed": 36,
                    "total_good_values": 34200,
                    "total_bad_values": 1080,
                    "corrections_applied": 45,
                    "corrections_rejected": 5
                },
                "metadata": {
                    "processing_time": 18.3,
                    "timestamp": "2026-01-27T10:00:00Z",
                    "job_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field(default="error", description="Status")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
