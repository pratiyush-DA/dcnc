"""
Health Check Endpoints
======================
Health and status endpoints
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status of the API and services
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "classification": "operational",
            "correction": "operational",
            "database": "operational"  # TODO: Check actual DB status
        }
    }


@router.get("/status")
async def status():
    """
    Detailed status endpoint.
    
    Returns:
        Detailed status information
    """
    # TODO: Add actual service status checks
    return {
        "status": "operational",
        "version": "1.0.0",
        "uptime": "N/A",  # TODO: Calculate uptime
        "services": {
            "classification": {
                "status": "operational",
                "last_check": datetime.utcnow().isoformat() + "Z"
            },
            "correction": {
                "status": "operational",
                "last_check": datetime.utcnow().isoformat() + "Z"
            }
        }
    }
