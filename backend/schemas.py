"""
Pydantic schemas for request and response validation
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, JobStatus

# Authentication schemas
class UserRegister(BaseModel):
    role: UserRole = UserRole.RENTER

class GoogleAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: UserRole

# UserCreate removed - using Google OAuth only

class ActiveRoleUpdate(BaseModel):
    active_role: UserRole
    
    @validator('active_role')
    def validate_active_role(cls, v):
        if v == UserRole.ADMIN:
            raise ValueError('Cannot switch to admin role')
        return v

class UserResponse(UserBase):
    id: str  # String ID for Google OAuth compatibility
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    oauth_provider: str = "google"
    is_active: bool
    created_at: datetime
    
    # Role switching fields
    is_renter: bool = True
    is_host: bool = False
    active_role: UserRole = UserRole.RENTER
    
    class Config:
        from_attributes = True

# Host schemas
class HostRegister(BaseModel):
    host_id: str = Field(..., min_length=3, max_length=100)
    gpu_model: str = Field(..., min_length=1, max_length=100)
    gpu_memory: str = Field(..., min_length=1, max_length=20)
    gpu_count: int = Field(default=1, ge=1, le=8)
    cpu_cores: Optional[int] = Field(None, ge=1, le=128)
    ram_gb: Optional[int] = Field(None, ge=1, le=1024)
    storage_gb: Optional[int] = Field(None, ge=1, le=10000)
    price_per_hour: float = Field(..., gt=0, le=1000)
    location: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list)

class HostUpdate(BaseModel):
    gpu_model: Optional[str] = Field(None, min_length=1, max_length=100)
    gpu_memory: Optional[str] = Field(None, min_length=1, max_length=20)
    gpu_count: Optional[int] = Field(None, ge=1, le=8)
    cpu_cores: Optional[int] = Field(None, ge=1, le=128)
    ram_gb: Optional[int] = Field(None, ge=1, le=1024)
    storage_gb: Optional[int] = Field(None, ge=1, le=10000)
    price_per_hour: Optional[float] = Field(None, gt=0, le=1000)
    location: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    is_available: Optional[bool] = None

class HostResponse(BaseModel):
    id: int
    host_id: str
    owner_id: int
    gpu_model: str
    gpu_memory: str
    gpu_count: int
    cpu_cores: Optional[int]
    ram_gb: Optional[int]
    storage_gb: Optional[int]
    price_per_hour: float
    is_online: bool
    is_available: bool
    location: Optional[str]
    tags: List[str]
    uptime_percentage: float
    total_jobs_completed: int
    total_earnings: float
    last_heartbeat: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Job schemas
class JobSubmit(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    command: str = Field(..., min_length=1, max_length=5000)
    docker_image: Optional[str] = Field(None, max_length=255)
    code_archive_url: Optional[str] = Field(None, max_length=500)
    gpu_count_required: int = Field(default=1, ge=1, le=8)
    memory_gb_required: Optional[int] = Field(None, ge=1, le=1024)
    max_runtime_hours: float = Field(default=24.0, gt=0, le=168)  # Max 1 week
    make_public: bool = Field(default=False)
    host_id: Optional[str] = Field(None, min_length=1, max_length=100)  # Preferred host

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = Field(None, max_length=5000)
    log_url: Optional[str] = Field(None, max_length=500)
    results_url: Optional[str] = Field(None, max_length=500)

class JobResponse(BaseModel):
    id: int
    job_id: str
    renter_id: int
    host_id: Optional[int]
    title: str
    description: Optional[str]
    status: JobStatus
    submitted_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    gpu_count_required: int
    memory_gb_required: Optional[int]
    max_runtime_hours: float
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    make_public: bool
    
    class Config:
        from_attributes = True

# WebSocket schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Optional[dict] = None
    timestamp: Optional[datetime] = None

class HostHeartbeat(BaseModel):
    host_id: str
    status: str = "online"
    gpu_utilization: Optional[float] = Field(None, ge=0, le=100)
    memory_utilization: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=0, le=200)

class JobProgress(BaseModel):
    job_id: str
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    current_epoch: Optional[int] = Field(None, ge=0)
    total_epochs: Optional[int] = Field(None, ge=1)
    loss: Optional[float] = None
    metrics: Optional[dict] = None

# Model schemas
class ModelPublish(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(default_factory=list)
    model_type: Optional[str] = Field(None, max_length=100)
    framework: Optional[str] = Field(None, max_length=100)
    model_files_url: str = Field(..., max_length=500)
    readme_url: Optional[str] = Field(None, max_length=500)
    example_code_url: Optional[str] = Field(None, max_length=500)
    citation: Optional[str] = Field(None, max_length=2000)
    license: str = Field(default="MIT", max_length=100)

class ModelResponse(BaseModel):
    id: int
    model_id: str
    author_id: int
    name: str
    description: Optional[str]
    tags: List[str]
    model_type: Optional[str]
    framework: Optional[str]
    download_count: int
    star_count: int
    fork_count: int
    file_size_mb: Optional[float]
    citation: Optional[str]
    license: str
    is_featured: bool
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Error schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Health check schemas
class HealthResponse(BaseModel):
    status: str
    active_hosts: int
    components: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)