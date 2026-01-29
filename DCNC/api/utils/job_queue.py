"""
Job Queue
=========
Simple in-memory job queue for background processing
Can be upgraded to Redis/Celery for production
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job representation"""
    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobQueue:
    """Simple in-memory job queue"""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def submit_job(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        Submit a job for background processing.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, status=JobStatus.PENDING)
        
        async with self._lock:
            self._jobs[job_id] = job
        
        # Start job in background
        task = asyncio.create_task(self._run_job(job_id, func, *args, **kwargs))
        self._running_tasks[job_id] = task
        
        logger.info(f"Job {job_id} submitted")
        return job_id
    
    async def _run_job(
        self,
        job_id: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """Run a job in the background"""
        try:
            async with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow()
            
            logger.info(f"Job {job_id} started")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            async with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    job.result = result
                    job.progress = 1.0
            
            logger.info(f"Job {job_id} completed")
            
        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")
            async with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    job.error = str(e)
        finally:
            async with self._lock:
                if job_id in self._running_tasks:
                    del self._running_tasks[job_id]
    
    async def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status"""
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result if completed"""
        job = await self.get_job_status(job_id)
        if job and job.status == JobStatus.COMPLETED:
            return job.result
        return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELLED
                return True
            elif job.status == JobStatus.RUNNING:
                # Try to cancel the task
                task = self._running_tasks.get(job_id)
                if task:
                    task.cancel()
                job.status = JobStatus.CANCELLED
                return True
        
        return False
    
    async def cleanup_old_jobs(self, retention_hours: int = 24):
        """Clean up old completed/failed jobs"""
        cutoff = datetime.utcnow() - timedelta(hours=retention_hours)
        
        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.completed_at and job.completed_at < cutoff:
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del self._jobs[job_id]
                if job_id in self._running_tasks:
                    del self._running_tasks[job_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")


# Global job queue instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get global job queue instance"""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue
