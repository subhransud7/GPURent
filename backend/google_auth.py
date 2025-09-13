"""
Google OAuth authentication for FastAPI
Based on Replit Auth integration principles adapted for FastAPI
"""

import os
import requests
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models import User, UserRole
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get the domain from environment 
REPLIT_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN")
if REPLIT_DOMAIN:
    REDIRECT_URI = f"https://{REPLIT_DOMAIN}/auth/google/callback"
else:
    # Development fallback
    REDIRECT_URI = "http://localhost:5000/auth/google/callback"

# JWT Configuration - Load from environment, fail if missing for production stability
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is required for secure operation. Check your .env file.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class GoogleOAuth:
    def __init__(self):
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            print("""
⚠️  Google OAuth Configuration Required:

To enable Google authentication:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add the following to Authorized redirect URIs:
   {redirect_uri}
4. Set the GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
            """.format(redirect_uri=REDIRECT_URI))
    
    def get_authorization_url(self) -> str:
        """Get the Google OAuth authorization URL"""
        import secrets
        import urllib.parse
        import hmac
        import hashlib
        import time
        
        # Generate a random nonce and timestamp for security
        nonce = secrets.token_urlsafe(16)
        timestamp = str(int(time.time()))
        
        # Create state by HMAC signing the nonce and timestamp
        state_data = f"{nonce}:{timestamp}"
        state_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            state_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        state = f"{state_data}:{state_signature}"
        
        # Build authorization URL manually
        auth_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': 'openid email profile',
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',
            'prompt': 'select_account'
        }
        
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
        return auth_url
    
    def get_user_info(self, authorization_code: str, state: str) -> dict:
        """Exchange authorization code for user information"""
        try:
            # Verify state parameter to prevent CSRF attacks
            if not state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing state parameter - potential CSRF attack"
                )
            
            self._verify_oauth_state(state)
            # Exchange authorization code for access token
            token_data = {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI
            }
            
            # Make token exchange request
            token_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {error_detail}"
                )
            
            token_json = token_response.json()
            access_token = token_json.get('access_token')
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Google"
                )
            
            # Get user info from Google
            user_response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user information from Google"
                )
            
            return user_response.json()
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth authentication failed: {str(e)}"
            )

    def _verify_oauth_state(self, state: str) -> None:
        """Verify OAuth state parameter to prevent CSRF attacks"""
        import hmac
        import hashlib
        import time
        
        try:
            # Parse state: nonce:timestamp:signature
            parts = state.split(':')
            if len(parts) != 3:
                raise ValueError("Invalid state format")
            
            nonce, timestamp_str, provided_signature = parts
            
            # Check timestamp (reject states older than 10 minutes)
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            if current_time - timestamp > 600:  # 10 minutes
                raise ValueError("State expired")
            
            # Verify signature
            state_data = f"{nonce}:{timestamp_str}"
            expected_signature = hmac.new(
                SECRET_KEY.encode('utf-8'),
                state_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(provided_signature, expected_signature):
                raise ValueError("Invalid state signature")
                
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OAuth state - potential CSRF attack: {str(e)}"
            )

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

def verify_token(token: str):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

def create_or_update_user(user_info: dict, db: Session, role: UserRole = UserRole.RENTER) -> User:
    """Create or update user from Google OAuth information"""
    google_id = user_info.get("id")
    email = user_info.get("email")
    
    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient user information from Google"
        )
    
    # Check if user already exists
    user = db.query(User).filter(User.google_id == google_id).first()
    
    if user:
        # Update existing user info
        user.email = email
        user.username = user_info.get("name", email.split("@")[0])
        user.first_name = user_info.get("given_name") or user.first_name
        user.last_name = user_info.get("family_name") or user.last_name
        user.profile_image_url = user_info.get("picture") or user.profile_image_url
        user.updated_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            username=user_info.get("name", email.split("@")[0]),
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            profile_image_url=user_info.get("picture"),
            oauth_provider="google",
            role=role
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    return user

# Initialize OAuth client
google_oauth = GoogleOAuth()