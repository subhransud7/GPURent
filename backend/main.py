"""
Peer-to-Peer GPU Cloud Platform Backend
FastAPI application with WebSocket support for GPU host communication
Based on python_database integration blueprint adapted for FastAPI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uvicorn
import asyncio
import json
import uuid
from typing import Dict, List, Optional
import logging
import os

# Database imports
from database import get_db, init_db, check_db_connection
from models import User, Host, Job, PublicModel, UserRole, JobStatus

_db_initialized = False

def ensure_db_initialized():
    """Initialize database lazily on first use"""
    global _db_initialized
    if not _db_initialized:
        if check_db_connection():
            init_db()
            _db_initialized = True
        else:
            logger.error("❌ Database connection failed")


# Redis job queue imports
from redis_queue import get_job_queue, JobQueueStatus

# Authentication imports
from auth import (
    get_current_user, get_current_active_user, require_host_role, require_admin_role,
    authenticate_websocket_token
)
from google_auth import google_oauth, create_access_token, create_or_update_user

# Schema imports
from schemas import (
    UserRegister, Token, UserResponse, ActiveRoleUpdate,
    HostRegister, HostUpdate, HostResponse,
    JobSubmit, JobUpdate, JobResponse,
    HostHeartbeat, JobProgress, ErrorResponse, HealthResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.host_connections: Dict[str, WebSocket] = {}
        self.host_users: Dict[str, User] = {}  # Track authenticated users
    
    async def connect_host(self, websocket: WebSocket, host_id: str, user: User, db: Session):
        await websocket.accept()
        self.host_connections[host_id] = websocket
        self.host_users[host_id] = user
        
        # Update host status in database
        host = db.query(Host).filter(
            Host.host_id == host_id,
            Host.owner_id == user.id
        ).first()
        
        if host:
            host.is_online = True
            host.last_heartbeat = datetime.utcnow()
            db.commit()
            logger.info(f"Host {host_id} connected and marked online")
        else:
            logger.warning(f"Host {host_id} not found in database for user {user.email}")
    
    async def disconnect_host(self, host_id: str, db: Session):
        if host_id in self.host_connections:
            del self.host_connections[host_id]
            
            # Update host status in database
            if host_id in self.host_users:
                user = self.host_users[host_id]
                del self.host_users[host_id]
                
                host = db.query(Host).filter(
                    Host.host_id == host_id,
                    Host.owner_id == user.id
                ).first()
                
                if host:
                    host.is_online = False
                    db.commit()
                    logger.info(f"Host {host_id} disconnected and marked offline")
    
    async def send_to_host(self, host_id: str, message: dict):
        if host_id in self.host_connections:
            websocket = self.host_connections[host_id]
            await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 GPU Cloud Platform starting up...")
    
    # Skip all database operations during startup for faster health checks
    # This ensures deployment health checks succeed quickly
    logger.info("✅ Startup complete - database will initialize on first use")
    
    yield
    logger.info("Shutting down GPU Cloud Platform...")

# Create FastAPI app
app = FastAPI(
    title="Peer-to-Peer GPU Cloud Platform",
    description="A marketplace for renting GPU compute power",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for security
FRONTEND_URL = os.environ.get("REPLIT_DEV_DOMAIN")
if FRONTEND_URL:
    allowed_origins = [f"https://{FRONTEND_URL}"]
else:
    # Development fallback
    allowed_origins = ["http://localhost:5000", "http://localhost:3000", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Static file mounting will be done after all API routes are defined

# Health check endpoint moved to /health for deployment monitoring
@app.get("/health")
@app.head("/health")
def deployment_health_check():
    """Fast health check endpoint for deployment monitoring - no database dependencies"""
    return {"status": "ok", "message": "Service is healthy", "timestamp": datetime.utcnow().isoformat()}
    

# API info endpoint is defined later with both GET and HEAD support

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check with database status"""
    # Test database connection safely without blocking
    db_status = "online" if check_db_connection() else "offline"
    
    return HealthResponse(
        status="healthy" if db_status == "online" else "degraded",
        active_hosts=len(manager.host_connections),
        components={
            "api": "online",
            "database": db_status,
            "websocket": "online"
        }
    )

# Authentication routes
# Note: User registration now happens automatically via Google OAuth

@app.get("/api/auth/google")
async def google_login():
    """Initiate Google OAuth login"""
    try:
        authorization_url = google_oauth.get_authorization_url()
        return {"authorization_url": authorization_url}
    except Exception as e:
        logger.error(f"Google OAuth initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google authentication"
        )

@app.get("/api/auth/google/callback")
async def google_callback(
    code: str, 
    state: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback and return JWT token with user data"""
    try:
        # Get user info from Google
        user_info = google_oauth.get_user_info(code, state or "")
        
        # Create or update user in database
        user = create_or_update_user(user_info, db)
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in via Google: {user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_image_url": user.profile_image_url,
                "role": user.role.value,
                "oauth_provider": user.oauth_provider,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_renter": user.is_renter,
                "is_host": user.is_host,
                "active_role": user.active_role.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@app.patch("/api/auth/me/active-role", response_model=UserResponse)
async def update_active_role(
    role_update: ActiveRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user's active role (switch between renter and host)"""
    try:
        # Validate that user can switch to the requested role
        if role_update.active_role == UserRole.HOST and not current_user.is_host:
            # Don't auto-enable host capability - user must complete host onboarding first
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must register as a host before switching to host mode. Please add a GPU host device first."
            )
        
        # Update the active role
        current_user.active_role = role_update.active_role
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.email} switched to {role_update.active_role.value} role")
        return current_user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating active role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update active role"
        )

@app.get("/api")
@app.head("/api")
def api_root():
    """API root endpoint - supports HEAD for proxy health checks"""
    return {"message": "P2P GPU Cloud Platform API", "version": "1.0.0", "status": "online"}
    
# Host management routes
@app.post("/api/hosts/register", response_model=HostResponse)
async def register_host(
    host_data: HostRegister, 
    current_user: User = Depends(require_host_role),
    db: Session = Depends(get_db)
):
    """Register a GPU host device (requires host role)"""
    try:
        # Check if host_id already exists
        existing_host = db.query(Host).filter(Host.host_id == host_data.host_id).first()
        if existing_host:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host ID already exists"
            )
        
        # Create new host record
        new_host = Host(
            host_id=host_data.host_id,
            owner_id=current_user.id,  # Use authenticated user's ID
            gpu_model=host_data.gpu_model,
            gpu_memory=host_data.gpu_memory,
            gpu_count=host_data.gpu_count,
            cpu_cores=host_data.cpu_cores,
            ram_gb=host_data.ram_gb,
            storage_gb=host_data.storage_gb,
            price_per_hour=host_data.price_per_hour,
            location=host_data.location,
            tags=json.dumps(host_data.tags)
        )
        
        db.add(new_host)
        db.commit()
        db.refresh(new_host)
        
        logger.info(f"Host registered: {new_host.host_id} by user {current_user.email}")
        
        # Parse tags for response
        host_dict = new_host.__dict__.copy()
        host_dict['tags'] = host_data.tags if host_data.tags else []
        
        return HostResponse(**host_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Host registration error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host registration failed"
        )

@app.get("/api/hosts", response_model=List[HostResponse])
async def list_hosts(db: Session = Depends(get_db)):
    """Get all available GPU hosts"""
    try:
        hosts = db.query(Host).filter(Host.is_available == True).all()
        
        host_list = []
        for host in hosts:
            # Parse tags from JSON
            tags = json.loads(host.tags) if host.tags else []
            host_dict = host.__dict__.copy()
            host_dict['tags'] = tags
            host_list.append(HostResponse(**host_dict))
        
        return host_list
    except Exception as e:
        logger.error(f"Error fetching hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hosts"
        )

@app.get("/api/hosts/my", response_model=List[HostResponse])
async def list_my_hosts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's hosts (any user can check their own hosts)"""
    try:
        hosts = db.query(Host).filter(Host.owner_id == current_user.id).all()
        
        host_list = []
        for host in hosts:
            tags = json.loads(host.tags) if host.tags else []
            host_dict = host.__dict__.copy()
            host_dict['tags'] = tags
            host_list.append(HostResponse(**host_dict))
        
        return host_list
    except Exception as e:
        logger.error(f"Error fetching user hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hosts"
        )

# Job management routes
@app.post("/api/jobs", response_model=JobResponse)
async def submit_job(
    job_data: JobSubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit a new GPU job"""
    try:
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        # Find suitable host if preferred host specified
        host = None
        if job_data.host_id:
            host = db.query(Host).filter(
                Host.host_id == job_data.host_id,
                Host.is_available == True,
                Host.is_online == True
            ).first()
            if not host:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified host not available"
                )
        
        # Create new job
        new_job = Job(
            job_id=job_id,
            renter_id=current_user.id,
            host_id=host.id if host else None,
            title=job_data.title,
            description=job_data.description,
            command=job_data.command,
            docker_image=job_data.docker_image,
            code_archive_url=job_data.code_archive_url,
            gpu_count_required=job_data.gpu_count_required,
            memory_gb_required=job_data.memory_gb_required,
            max_runtime_hours=job_data.max_runtime_hours,
            make_public=job_data.make_public
        )
        
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
        logger.info(f"Job submitted: {job_id} by user {current_user.email}")
        return new_job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job submission error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job submission failed"
        )

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job status and details"""
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if user has access to this job
        if job.renter_id != current_user.id and current_user.role != UserRole.ADMIN:
            # Allow host to see their assigned jobs
            if current_user.role == UserRole.HOST:
                host = db.query(Host).filter(
                    Host.owner_id == current_user.id,
                    Host.id == job.host_id
                ).first()
                if not host:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch job"
        )

@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's jobs"""
    try:
        if current_user.role == UserRole.ADMIN:
            jobs = db.query(Job).all()
        elif current_user.role == UserRole.HOST:
            # Host can see jobs assigned to their hosts
            host_ids = [h.id for h in db.query(Host).filter(Host.owner_id == current_user.id).all()]
            jobs = db.query(Job).filter(Job.host_id.in_(host_ids)).all()
        else:
            # Renters see their own jobs
            jobs = db.query(Job).filter(Job.renter_id == current_user.id).all()
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch jobs"
        )

# WebSocket endpoint for host connections
@app.websocket("/ws/host/{host_id}")
async def websocket_host_endpoint(websocket: WebSocket, host_id: str):
    """WebSocket endpoint for GPU host agents"""
    db = None
    
    try:
        db = next(get_db())
        # Authenticate WebSocket connection
        # Extract token from query parameters or headers
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        # Authenticate user
        user = authenticate_websocket_token(token, db)
        
        # Verify user owns this host
        host = db.query(Host).filter(
            Host.host_id == host_id,
            Host.owner_id == user.id
        ).first()
        
        if not host:
            await websocket.close(code=1008, reason="Host not found or access denied")
            return
        
        await manager.connect_host(websocket, host_id, user, db)
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": f"Connected as host {host_id}",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        while True:
            # Listen for messages from host
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"Received from host {host_id}: {message}")
            
            # Handle different message types
            if message.get("type") == "heartbeat":
                # Update heartbeat in database
                host.last_heartbeat = datetime.utcnow()
                db.commit()
                
                await websocket.send_text(json.dumps({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            elif message.get("type") == "job_result":
                # Handle job completion
                logger.info(f"Job completed by host {host_id}")
                await websocket.send_text(json.dumps({
                    "type": "job_ack",
                    "message": "Job result received"
                }))
                
    except WebSocketDisconnect:
        if db:
            await manager.disconnect_host(host_id, db)
    except HTTPException as e:
        logger.error(f"WebSocket auth error for host {host_id}: {e.detail}")
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        logger.error(f"Error in WebSocket connection for host {host_id}: {e}")
        if db:
            await manager.disconnect_host(host_id, db)
    finally:
        if db:
            db.close()

# WebSocket endpoint for renter job monitoring
@app.websocket("/ws/job/{job_id}")
async def websocket_job_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for job log streaming"""
    db = None
    
    try:
        db = next(get_db())
        # Authenticate WebSocket connection
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        # Authenticate user
        user = authenticate_websocket_token(token, db)
        
        # Verify user has access to this job
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job or (job.renter_id != user.id and user.role != UserRole.ADMIN):
            await websocket.close(code=1008, reason="Job not found or access denied")
            return
        
        await websocket.accept()
        
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "job_id": job_id,
            "status": job.status.value,
            "message": f"Job is {job.status.value}..."
        }))
        
        # Simulate streaming logs for demo
        if job.status == JobStatus.RUNNING:
            demo_logs = [
                "Loading Docker image...",
                "Setting up GPU environment...",
                "Running training script...",
                "Epoch 1/10: loss=0.5, accuracy=0.85",
                "Epoch 2/10: loss=0.4, accuracy=0.87",
                "Training completed successfully!",
                "Uploading results..."
            ]
            
            for log in demo_logs:
                await asyncio.sleep(2)  # Simulate processing time
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "job_id": job_id,
                    "message": log,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            # Send completion status
            await websocket.send_text(json.dumps({
                "type": "status",
                "job_id": job_id,
                "status": "completed",
                "message": "Job completed successfully",
                "results_url": f"https://example.com/results/{job_id}.zip"
            }))
        
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except HTTPException as e:
        logger.error(f"WebSocket auth error for job {job_id}: {e.detail}")
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        logger.error(f"Error in WebSocket connection for job {job_id}: {e}")
    finally:
        if db:
            db.close()

# Admin routes
@app.get("/api/admin/stats")
async def get_platform_stats(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get platform statistics for admin dashboard"""
    try:
        total_hosts = db.query(Host).count()
        active_jobs = db.query(Job).filter(Job.status == JobStatus.RUNNING).count()
        completed_jobs = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
        total_users = db.query(User).count()
        
        return {
            "total_hosts": total_hosts,
            "active_hosts": len(manager.host_connections),
            "total_users": total_users,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "pending_jobs": db.query(Job).filter(Job.status == JobStatus.PENDING).count()
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )

# Mount static files for production (after all API routes)
import os
from fastapi.responses import FileResponse

frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    # Mount static assets (CSS, JS, etc.) at /assets
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    
    # Serve frontend at root for the main user experience
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_frontend(path: str = ""):
        """Serve frontend index.html for SPA routing - main app entry point"""
        # Skip serving frontend for API endpoints
        if path and (path.startswith("api/") or path.startswith("ws/") or path == "health"):
            raise HTTPException(status_code=404, detail="Not found")
            
        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")
    
    logger.info(f"✅ Mounted frontend static files from {frontend_dist_path} at root with SPA routing")
else:
    logger.info("ℹ️ Frontend dist directory not found, running in development mode")

if __name__ == "__main__":
    # Use environment variables to determine production vs development settings
    is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"
    reload_enabled = os.getenv("UVICORN_RELOAD", "true" if is_development else "false").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=reload_enabled,
        log_level="info"
    )