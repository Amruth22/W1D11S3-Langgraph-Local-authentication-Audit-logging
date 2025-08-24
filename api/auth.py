"""
Local authentication system for the Research Assistant API.
File-based user management with JWT tokens.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration (loaded from .env file)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "research-assistant-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
USERS_FILE = os.getenv("USERS_FILE", "data/users.json")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Validate JWT secret key
if SECRET_KEY == "research-assistant-secret-key-change-in-production":
    print("WARNING: Using default JWT secret key. Set JWT_SECRET_KEY in .env file for production.")


class User(BaseModel):
    """User model."""
    username: str
    email: str
    full_name: str
    disabled: bool = False


class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str
    created_at: str
    last_login: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: str
    full_name: str
    password: str


class UserLogin(BaseModel):
    """User login model."""
    username: str
    password: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int


class AuthManager:
    """Local authentication manager."""
    
    def __init__(self):
        self.users_file = Path(USERS_FILE)
        self.users_file.parent.mkdir(exist_ok=True)
        self._ensure_users_file()
    
    def _ensure_users_file(self):
        """Ensure users file exists."""
        if not self.users_file.exists():
            self.users_file.write_text(json.dumps({}))
    
    def _load_users(self) -> Dict[str, UserInDB]:
        """Load users from file."""
        try:
            with open(self.users_file, 'r') as f:
                users_data = json.load(f)
                return {
                    username: UserInDB(**user_data)
                    for username, user_data in users_data.items()
                }
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict[str, UserInDB]):
        """Save users to file."""
        users_data = {
            username: user.dict()
            for username, user in users.items()
        }
        with open(self.users_file, 'w') as f:
            json.dump(users_data, f, indent=2)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)
    
    def get_user(self, username: str) -> Optional[UserInDB]:
        """Get user by username."""
        users = self._load_users()
        return users.get(username)
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Authenticate user."""
        user = self.get_user(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        users = self._load_users()
        users[username].last_login = datetime.now().isoformat()
        self._save_users(users)
        
        return user
    
    def create_user(self, user_create: UserCreate) -> UserInDB:
        """Create new user."""
        users = self._load_users()
        
        # Check if user already exists
        if user_create.username in users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        for existing_user in users.values():
            if existing_user.email == user_create.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        hashed_password = self.get_password_hash(user_create.password)
        new_user = UserInDB(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            created_at=datetime.now().isoformat()
        )
        
        users[user_create.username] = new_user
        self._save_users(users)
        
        return new_user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return username."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        username = auth_manager.verify_token(credentials.credentials)
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = auth_manager.get_user(username)
    if user is None:
        raise credentials_exception
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return User(**user.dict())


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user