#!/usr/bin/env python3
"""
Run DCNC API Server
===================
Production-ready API server for data classification and correction
"""

import os
import uvicorn

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required, but helpful for .env files

from DCNC.api.config import API_HOST, API_PORT, API_WORKERS

if __name__ == "__main__":
    # Default to 1 worker for dev (avoids multiprocessing issues); set API_WORKERS=4 for production
    workers = int(os.getenv("API_WORKERS", "1"))
    use_workers = workers if workers > 1 else None
    uvicorn.run(
        "DCNC.api.app:app",
        host=API_HOST,
        port=API_PORT,
        workers=use_workers,
        log_level="info",
        reload=False
    )
