"""
Authentication utilities for JWT token handling and password hashing
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
# Removed passlib import - using Google OAuth only
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole

# Password hashing - REMOVED for Google OAuth only authentication

# JWT configuration - use the same key as google_auth for consistency  
from google_auth import SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()

# Password functions REMOVED - using Google OAuth only

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    payload = verify_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token - missing user ID"
        )
    user_id: int = int(user_id_str)  # Integer primary key from database
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (alias for clarity)"""
    return current_user

def require_role(required_role: UserRole):
    """Create a dependency that requires a specific user role"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return current_user
    return role_checker

def require_host_role(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a host"""
    if current_user.role not in [UserRole.HOST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Host role required."
        )
    return current_user

def require_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    return current_user

# WebSocket authentication
def authenticate_websocket_token(token: str, db: Session) -> User:
    """Authenticate a WebSocket connection using JWT token"""
    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        
        # Convert string user ID from JWT to integer for database lookup
        user_id = int(user_id_str)
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user
    except HTTPException:
        raise
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=401, detail="Invalid user ID format")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token authentication failed")