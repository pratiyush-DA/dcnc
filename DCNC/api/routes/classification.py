"""
Classification Routes
=====================
API routes for data classification
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ..models.request import ClassificationRequest
from ..models.response import ClassificationResponse, ErrorResponse
from ..services.classification_service import ClassificationService
from ..utils.job_queue import get_job_queue
from ..config import MAX_FILE_SIZE
from backend.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_classification_service(
    current_user: dict = None
) -> ClassificationService:
    """Get classification service with client context"""
    client_id = current_user.get("client_id") if current_user else None
    return ClassificationService(client_id=client_id)


@router.post("/classify")
async def classify_data(
    request: ClassificationRequest,
    background_tasks: BackgroundTasks,
    use_background: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Classify data file into good/bad/reject.
    
    Accepts either:
    - file_path: Path to file on server
    - file_content: Base64 encoded file content
    
    For large files, set use_background=true to process asynchronously.
    
    Returns:
    - good_data.csv: Rows where ALL columns are good
    - bad_data.csv: Column-wise bad data details
    - reject_data.csv: Rows where ANY column has bad data
    - fingerprint.json: All column fingerprints
    """
    try:
        logger.info(f"Classification request received (background={use_background})")
        
        # Check file size for background processing
        file_size = 0
        if request.file_path:
            from pathlib import Path
            file_size = Path(request.file_path).stat().st_size if Path(request.file_path).exists() else 0
        elif request.file_content:
            file_size = len(request.file_content.encode('utf-8'))
        
        # Use background job for large files (>50MB) or if explicitly requested
        use_background = use_background or (file_size > 50 * 1024 * 1024)
        
        # Prepare options
        options = {}
        if request.options:
            options = {
                "enable_validation": request.options.enable_validation,
                "enable_ml_clustering": request.options.enable_ml_clustering,
                "enable_ensemble_detection": request.options.enable_ensemble_detection,
                "enable_llm_verification": request.options.enable_llm_verification,
                "strict_mode": request.options.strict_mode,
            }
        
        # Get classification service with client context
        classification_service = get_classification_service(current_user)
        
        if use_background:
            # Submit as background job
            job_queue = get_job_queue()
            job_id = await job_queue.submit_job(
                classification_service.classify,
                file_path=request.file_path,
                file_content=request.file_content,
                has_header=request.has_header,
                options=options
            )
            
            return JSONResponse(
                status_code=202,
                content={
                    "status": "processing",
                    "job_id": job_id,
                    "message": "Classification started in background. Use /classify/status/{job_id} to check status."
                }
            )
        else:
            # Run synchronously
            result = await classification_service.classify(
                file_path=request.file_path,
                file_content=request.file_content,
                has_header=request.has_header,
                options=options
            )
            
            return ClassificationResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/classify/upload")
async def classify_upload(
    file: UploadFile = File(...),
    has_header: bool = True,
    enable_validation: bool = True,
    enable_ml_clustering: bool = True,
    enable_ensemble_detection: bool = True,
    enable_llm_verification: bool = False,
    strict_mode: bool = False,
    use_background: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Classify uploaded file into good/bad/reject.
    
    Upload a file directly via multipart/form-data.
    
    Returns:
    - good_data.csv: Rows where ALL columns are good
    - bad_data.csv: Column-wise bad data details
    - reject_data.csv: Rows where ANY column has bad data
    - fingerprint.json: All column fingerprints
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
        
        # Decode content (assuming UTF-8 for CSV)
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
        options = {
            "enable_validation": enable_validation,
            "enable_ml_clustering": enable_ml_clustering,
            "enable_ensemble_detection": enable_ensemble_detection,
            "enable_llm_verification": enable_llm_verification,
            "strict_mode": strict_mode,
        }
        
        # Get classification service with client context
        classification_service = get_classification_service(current_user)
        
        if use_background:
            # Submit as background job
            job_queue = get_job_queue()
            job_id = await job_queue.submit_job(
                classification_service.classify,
                file_path=None,
                file_content=file_content,
                has_header=has_header,
                options=options
            )
            
            return JSONResponse(
                status_code=202,
                content={
                    "status": "processing",
                    "job_id": job_id,
                    "message": "Classification started in background. Use /classify/status/{job_id} to check status."
                }
            )
        else:
            # Run synchronously
            result = await classification_service.classify(
                file_path=None,
                file_content=file_content,
                has_header=has_header,
                options=options
            )
            
            return ClassificationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.get("/classify/status/{job_id}")
async def get_classification_status(job_id: str):
    """
    Get status of a classification job.
    
    Returns job status, progress, and result if completed.
    """
    job_queue = get_job_queue()
    job = await job_queue.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    response = {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at.isoformat() + "Z",
        "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
        "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
    }
    
    if job.status.value == "completed" and job.result:
        response["result"] = job.result
    elif job.status.value == "failed" and job.error:
        response["error"] = job.error
    
    return response
