"""
Redis-based job queue system for the peer-to-peer GPU cloud platform
Handles job queuing, scheduling, and status updates
"""

import redis
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

class JobQueueStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned" 
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RedisJobQueue:
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection for job queue management"""
        if redis_url is None:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            # Fall back to local Redis if available
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Connected to local Redis server")
            except Exception as local_e:
                logger.error(f"❌ Local Redis connection also failed: {local_e}")
                self.redis_client = None

        # Queue keys
        self.pending_jobs_key = "gpu_jobs:pending"
        self.running_jobs_key = "gpu_jobs:running"
        self.completed_jobs_key = "gpu_jobs:completed"
        self.host_status_key = "gpu_hosts:status"
        
    def is_connected(self) -> bool:
        """Check if Redis is available"""
        return self.redis_client is not None

    def enqueue_job(self, job_data: Dict) -> bool:
        """Add a new job to the pending queue"""
        if not self.is_connected():
            logger.error("Redis not available - cannot enqueue job")
            return False
            
        try:
            job_data['queued_at'] = datetime.utcnow().isoformat()
            job_data['status'] = JobQueueStatus.PENDING
            
            # Add to pending jobs queue (FIFO)
            self.redis_client.lpush(self.pending_jobs_key, json.dumps(job_data))
            
            # Store job details with expiration (24 hours)
            job_key = f"job:{job_data['job_id']}"
            self.redis_client.setex(job_key, 86400, json.dumps(job_data))
            
            logger.info(f"Job {job_data['job_id']} enqueued successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_data.get('job_id')}: {e}")
            return False

    def get_next_job(self) -> Optional[Dict]:
        """Get the next pending job from the queue"""
        if not self.is_connected():
            return None
            
        try:
            # Get job from pending queue (FIFO)
            job_json = self.redis_client.rpop(self.pending_jobs_key)
            if job_json:
                job_data = json.loads(job_json)
                # Move to assigned status
                job_data['status'] = JobQueueStatus.ASSIGNED
                job_data['assigned_at'] = datetime.utcnow().isoformat()
                
                # Update job status
                job_key = f"job:{job_data['job_id']}"
                self.redis_client.setex(job_key, 86400, json.dumps(job_data))
                
                return job_data
                
        except Exception as e:
            logger.error(f"Failed to get next job: {e}")
            
        return None

    def start_job(self, job_id: str, host_id: str) -> bool:
        """Mark job as running on a specific host"""
        if not self.is_connected():
            return False
            
        try:
            job_key = f"job:{job_id}"
            job_json = self.redis_client.get(job_key)
            
            if job_json:
                job_data = json.loads(job_json)
                job_data['status'] = JobQueueStatus.RUNNING
                job_data['host_id'] = host_id
                job_data['started_at'] = datetime.utcnow().isoformat()
                
                # Update job status
                self.redis_client.setex(job_key, 86400, json.dumps(job_data))
                
                # Add to running jobs set
                self.redis_client.sadd(self.running_jobs_key, job_id)
                
                logger.info(f"Job {job_id} started on host {host_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            
        return False

    def complete_job(self, job_id: str, result_data: Dict) -> bool:
        """Mark job as completed with results"""
        if not self.is_connected():
            return False
            
        try:
            job_key = f"job:{job_id}"
            job_json = self.redis_client.get(job_key)
            
            if job_json:
                job_data = json.loads(job_json)
                job_data['status'] = JobQueueStatus.COMPLETED
                job_data['completed_at'] = datetime.utcnow().isoformat()
                job_data['result'] = result_data
                
                # Update job status
                self.redis_client.setex(job_key, 86400, json.dumps(job_data))
                
                # Remove from running and add to completed
                self.redis_client.srem(self.running_jobs_key, job_id)
                self.redis_client.sadd(self.completed_jobs_key, job_id)
                
                logger.info(f"Job {job_id} completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            
        return False

    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed with error details"""
        if not self.is_connected():
            return False
            
        try:
            job_key = f"job:{job_id}"
            job_json = self.redis_client.get(job_key)
            
            if job_json:
                job_data = json.loads(job_json)
                job_data['status'] = JobQueueStatus.FAILED
                job_data['failed_at'] = datetime.utcnow().isoformat()
                job_data['error_message'] = error_message
                
                # Update job status
                self.redis_client.setex(job_key, 86400, json.dumps(job_data))
                
                # Remove from running
                self.redis_client.srem(self.running_jobs_key, job_id)
                
                logger.info(f"Job {job_id} marked as failed: {error_message}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as failed: {e}")
            
        return False

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status and details"""
        if not self.is_connected():
            return None
            
        try:
            job_key = f"job:{job_id}"
            job_json = self.redis_client.get(job_key)
            
            if job_json:
                return json.loads(job_json)
                
        except Exception as e:
            logger.error(f"Failed to get status for job {job_id}: {e}")
            
        return None

    def update_host_status(self, host_id: str, status_data: Dict) -> bool:
        """Update host availability and status"""
        if not self.is_connected():
            return False
            
        try:
            status_data['last_updated'] = datetime.utcnow().isoformat()
            host_key = f"host:{host_id}"
            
            # Store host status with 5 minute expiration
            self.redis_client.setex(host_key, 300, json.dumps(status_data))
            
            # Add to active hosts set if online
            if status_data.get('is_online'):
                self.redis_client.sadd("active_hosts", host_id)
            else:
                self.redis_client.srem("active_hosts", host_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to update host {host_id} status: {e}")
            return False

    def get_available_hosts(self) -> List[str]:
        """Get list of currently available hosts"""
        if not self.is_connected():
            return []
            
        try:
            return list(self.redis_client.smembers("active_hosts"))
        except Exception as e:
            logger.error(f"Failed to get available hosts: {e}")
            return []

    def get_queue_stats(self) -> Dict:
        """Get statistics about the job queue"""
        if not self.is_connected():
            return {"error": "Redis not available"}
            
        try:
            stats = {
                "pending_jobs": self.redis_client.llen(self.pending_jobs_key),
                "running_jobs": self.redis_client.scard(self.running_jobs_key),
                "completed_jobs": self.redis_client.scard(self.completed_jobs_key),
                "active_hosts": self.redis_client.scard("active_hosts"),
                "redis_connected": True
            }
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e), "redis_connected": False}

    def cleanup_expired_jobs(self) -> int:
        """Clean up old job data and expired hosts"""
        if not self.is_connected():
            return 0
            
        cleaned_count = 0
        try:
            # Clean up expired host statuses (older than 5 minutes)
            active_hosts = list(self.redis_client.smembers("active_hosts"))
            for host_id in active_hosts:
                host_key = f"host:{host_id}"
                if not self.redis_client.exists(host_key):
                    self.redis_client.srem("active_hosts", host_id)
                    cleaned_count += 1
                    logger.info(f"Removed expired host {host_id} from active set")
                    
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired jobs: {e}")
            return 0

# Global job queue instance
job_queue = RedisJobQueue()

def get_job_queue() -> RedisJobQueue:
    """Get the global job queue instance"""
    return job_queue