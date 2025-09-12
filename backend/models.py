"""
Database models for Peer-to-Peer GPU Cloud Platform
Based on python_database integration blueprint adapted for FastAPI
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    HOST = "host"
    RENTER = "renter"
    ADMIN = "admin"

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class User(Base):
    """User accounts - can be hosts, renters, or admins"""
    __tablename__ = "users"
    
    id = Column(String(255), primary_key=True)  # Google user ID
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), nullable=False)  # Display name from Google
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    oauth_provider = Column(String(50), nullable=False, default="google")  # google, github, etc
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RENTER)
    stripe_customer_id = Column(String(255), nullable=True)  # For payments
    stripe_account_id = Column(String(255), nullable=True)  # For hosts (Connect)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    hosts = relationship("Host", back_populates="owner")
    jobs = relationship("Job", back_populates="renter")
    models = relationship("PublicModel", back_populates="author")

class Host(Base):
    """GPU host devices registered by users"""
    __tablename__ = "hosts"
    
    id = Column(Integer, primary_key=True)
    host_id = Column(String(100), unique=True, nullable=False)  # Unique device ID
    owner_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    
    # GPU specifications
    gpu_model = Column(String(100), nullable=False)  # RTX 4090, A100, etc
    gpu_memory = Column(String(20), nullable=False)  # 24GB, 80GB, etc
    gpu_count = Column(Integer, default=1)
    cpu_cores = Column(Integer, nullable=True)
    ram_gb = Column(Integer, nullable=True)
    storage_gb = Column(Integer, nullable=True)
    
    # Availability and pricing
    price_per_hour = Column(Float, nullable=False)
    is_online = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    
    # Location and tags
    location = Column(String(100), nullable=True)  # US-West, EU-Central, etc
    tags = Column(Text, nullable=True)  # JSON array of tags
    
    # Performance metrics
    uptime_percentage = Column(Float, default=0.0)
    total_jobs_completed = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    
    # Connection info
    last_heartbeat = Column(DateTime, nullable=True)
    public_key = Column(Text, nullable=True)  # For job verification
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="hosts")
    jobs = relationship("Job", back_populates="host")

class Job(Base):
    """GPU jobs submitted by renters"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True, nullable=False)
    renter_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    host_id = Column(Integer, ForeignKey("hosts.id"), nullable=True)
    
    # Job specification
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    command = Column(Text, nullable=False)
    docker_image = Column(String(255), nullable=True)
    code_archive_url = Column(String(500), nullable=True)  # S3 URL
    
    # Resource requirements
    gpu_count_required = Column(Integer, default=1)
    memory_gb_required = Column(Integer, nullable=True)
    max_runtime_hours = Column(Float, default=24.0)
    
    # Status and timing
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    exit_code = Column(Integer, nullable=True)
    log_url = Column(String(500), nullable=True)  # S3 URL for logs
    results_url = Column(String(500), nullable=True)  # S3 URL for outputs
    error_message = Column(Text, nullable=True)
    
    # Billing
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    # Publishing
    make_public = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    renter = relationship("User", back_populates="jobs")
    host = relationship("Host", back_populates="jobs")

class PublicModel(Base):
    """Public models shared by users"""
    __tablename__ = "public_models"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(String(100), unique=True, nullable=False)
    author_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)  # Source job
    
    # Model metadata
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    model_type = Column(String(100), nullable=True)  # PyTorch, TensorFlow, etc
    framework = Column(String(100), nullable=True)
    
    # Files and downloads
    model_files_url = Column(String(500), nullable=False)  # S3 URL
    readme_url = Column(String(500), nullable=True)
    example_code_url = Column(String(500), nullable=True)
    file_size_mb = Column(Float, nullable=True)
    
    # Usage stats
    download_count = Column(Integer, default=0)
    star_count = Column(Integer, default=0)
    fork_count = Column(Integer, default=0)
    
    # Citation info
    citation = Column(Text, nullable=True)
    license = Column(String(100), default="MIT")
    
    is_featured = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", back_populates="models")

# Note: Database setup is handled in database.py
# This file only contains the SQLAlchemy model definitions