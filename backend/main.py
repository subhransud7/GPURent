"""
Peer-to-Peer GPU Cloud Platform Backend
FastAPI application with WebSocket support for GPU host communication
Based on python_database integration blueprint adapted for FastAPI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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

# Redis job queue imports
from redis_queue import get_job_queue, JobQueueStatus

# Authentication imports
from auth import (
    get_current_user, get_current_active_user, require_host_role, require_admin_role,
    create_access_token, get_password_hash, verify_password, authenticate_websocket_token
)

# Schema imports
from schemas import (
    UserRegister, UserLogin, Token, UserResponse,
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
    
    # Initialize database
    if not check_db_connection():
        logger.error("❌ Database connection failed during startup")
    else:
        init_db()
    
    yield
    logger.info("Shutting down GPU Cloud Platform...")

# Create FastAPI app
app = FastAPI(
    title="Peer-to-Peer GPU Cloud Platform",
    description="A marketplace for renting GPU compute power",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Welcome to the P2P GPU Cloud Platform",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "online"
    except Exception:
        db_status = "offline"
    
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
@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (host or renter)"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create new user
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            role=user_data.role
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.email} ({new_user.role.value})")
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/api/auth/login")
async def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token with user data"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@app.get("/api")
@app.head("/api")
async def api_root():
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
    current_user: User = Depends(require_host_role),
    db: Session = Depends(get_db)
):
    """Get current user's hosts"""
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
    db = next(get_db())
    
    try:
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
        await manager.disconnect_host(host_id, db)
    except HTTPException as e:
        logger.error(f"WebSocket auth error for host {host_id}: {e.detail}")
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        logger.error(f"Error in WebSocket connection for host {host_id}: {e}")
        await manager.disconnect_host(host_id, db)
    finally:
        db.close()

# WebSocket endpoint for renter job monitoring
@app.websocket("/ws/job/{job_id}")
async def websocket_job_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for job log streaming"""
    db = next(get_db())
    
    try:
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )