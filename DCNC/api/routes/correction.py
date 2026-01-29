"""
Correction Routes
================
API routes for data classification + correction
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from ..models.request import ClassificationAndCorrectionRequest
from ..models.response import ClassificationAndCorrectionResponse, ErrorResponse
from ..services.correction_service import CorrectionService
from ..utils.job_queue import get_job_queue, JobStatus
from backend.middleware.auth_middleware import get_current_user
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter()


def get_correction_service(
    current_user: dict = None
) -> CorrectionService:
    """Get correction service with client context"""
    client_id = current_user.get("client_id") if current_user else None
    return CorrectionService(client_id=client_id)


@router.post("/classify-and-correct")
async def classify_and_correct(
    request: ClassificationAndCorrectionRequest,
    background_tasks: BackgroundTasks,
    use_background: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Classify data and apply corrections.
    
    This endpoint:
    1. Runs classification (good/bad/reject split)
    2. Applies corrections to bad data using fingerprints
    3. Generates corrected_data.csv
    4. Updates reject_data.csv with uncorrectable data
    5. Generates correction_report.json
    
    Returns:
    - good_data.csv: Rows where ALL columns are good
    - bad_data.csv: Column-wise bad data details
    - reject_data.csv: Rows with uncorrectable data
    - corrected_data.csv: Original data with corrections applied
    - fingerprint.json: All column fingerprints
    - correction_report.json: Detailed correction report
    """
    try:
        logger.info(f"Classification + correction request received")
        
        # Prepare classification options
        classification_options = {}
        if request.options:
            classification_options = {
                "enable_validation": request.options.enable_validation,
                "enable_ml_clustering": request.options.enable_ml_clustering,
                "enable_ensemble_detection": request.options.enable_ensemble_detection,
                "enable_llm_verification": request.options.enable_llm_verification,
                "strict_mode": request.options.strict_mode,
            }
        
        # Check file size for background processing
        file_size = 0
        if request.file_path:
            from pathlib import Path
            file_size = Path(request.file_path).stat().st_size if Path(request.file_path).exists() else 0
        elif request.file_content:
            file_size = len(request.file_content.encode('utf-8'))
        
        # Use background job for large files (>50MB) or if explicitly requested
        use_background = use_background or (file_size > 50 * 1024 * 1024)
        
        # Prepare correction options
        correction_options = {
            "similarity_threshold": request.correction_threshold,
            "max_corrections_per_column": request.max_corrections_per_column,
        }
        
        # Get correction service with client context
        correction_service = get_correction_service(current_user)
        
        if use_background:
            # Submit as background job
            job_queue = get_job_queue()
            job_id = await job_queue.submit_job(
                correction_service.classify_and_correct,
                file_path=request.file_path,
                file_content=request.file_content,
                has_header=request.has_header,
                classification_options=classification_options,
                correction_options=correction_options
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={
                    "status": "processing",
                    "job_id": job_id,
                    "message": "Classification + correction started in background. Use /classify-and-correct/status/{job_id} to check status."
                }
            )
        else:
            # Run synchronously
            result = await correction_service.classify_and_correct(
                file_path=request.file_path,
                file_content=request.file_content,
                has_header=request.has_header,
                classification_options=classification_options,
                correction_options=correction_options
            )
            
            return ClassificationAndCorrectionResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Classification + correction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/classify-and-correct/upload", response_model=ClassificationAndCorrectionResponse)
async def classify_and_correct_upload(
    file: UploadFile = File(...),
    has_header: bool = True,
    enable_validation: bool = True,
    enable_ml_clustering: bool = True,
    enable_ensemble_detection: bool = True,
    enable_llm_verification: bool = False,
    strict_mode: bool = False,
    correction_threshold: float = 0.7,
    max_corrections_per_column: int = 1000,
    use_background: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Classify and correct uploaded file.
    
    Upload a file directly via multipart/form-data.
    """
    try:
        logger.info(f"File upload received: {file.filename}")
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        from ..config import MAX_FILE_SIZE
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content)} bytes (max: {MAX_FILE_SIZE})"
            )
        
        # Validate file extension
        from ..config import ALLOWED_EXTENSIONS
        file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {ALLOWED_EXTENSIONS}"
            )
        
        # Decode content
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File encoding not supported. Please use UTF-8 encoded CSV."
            )
        
        # Check file size for background processing
        file_size = len(content)
        
        # Use background job for large files (>50MB) or if explicitly requested
        use_background = use_background or (file_size > 50 * 1024 * 1024)
        
        # Prepare options
        classification_options = {
            "enable_validation": enable_validation,
            "enable_ml_clustering": enable_ml_clustering,
            "enable_ensemble_detection": enable_ensemble_detection,
            "enable_llm_verification": enable_llm_verification,
            "strict_mode": strict_mode,
        }
        
        correction_options = {
            "similarity_threshold": correction_threshold,
            "max_corrections_per_column": max_corrections_per_column,
        }
        
        # Get correction service with client context
        correction_service = get_correction_service(current_user)
        
        if use_background:
            # Submit as background job
            job_queue = get_job_queue()
            job_id = await job_queue.submit_job(
                correction_service.classify_and_correct,
                file_path=None,
                file_content=file_content,
                has_header=has_header,
                classification_options=classification_options,
                correction_options=correction_options
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={
                    "status": "processing",
                    "job_id": job_id,
                    "message": "Classification + correction started in background. Use /classify-and-correct/status/{job_id} to check status."
                }
            )
        else:
            # Run synchronously
            result = await correction_service.classify_and_correct(
                file_path=None,
                file_content=file_content,
                has_header=has_header,
                classification_options=classification_options,
                correction_options=correction_options
            )
            
            return ClassificationAndCorrectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Classification + correction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/classify-and-correct/status/{job_id}")
async def get_correction_status(job_id: str):
    """
    Get status of a classification + correction job.
    
    For future use with background jobs.
    """
    job_queue = get_job_queue()
    job = await job_queue.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at.isoformat() + "Z",
        "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
        "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
        "error": job.error
    }
