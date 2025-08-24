"""
Main FastAPI application for the Research Assistant API.
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse

from .auth import (
    auth_manager, get_current_active_user, User, UserCreate, UserLogin, Token
)
from .audit import audit_logger, AuditAction, AuditLevel
from .middleware import setup_middleware
from .models import (
    ResearchRequest, ResearchResponse, ResearchListResponse, ResearchSummary,
    HealthResponse, ErrorResponse, MessageResponse, AuditLogResponse, UserProfile
)
from .research_manager import research_manager
from src.config import Config

# Create FastAPI app
app = FastAPI(
    title="Research Assistant API",
    description="AI-powered research assistant with LangGraph & Gemini 2.0 Flash",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup middleware
setup_middleware(app)

# Security
security = HTTPBearer()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


# Authentication endpoints
@app.post("/auth/register", response_model=MessageResponse)
async def register(user_create: UserCreate, request: Request):
    """Register a new user."""
    try:
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        
        # Create user
        new_user = auth_manager.create_user(user_create)
        
        # Log registration
        audit_logger.log_user_registration(
            username=new_user.username,
            email=new_user.email,
            ip_address=client_ip
        )
        
        return MessageResponse(
            message=f"User {new_user.username} registered successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin, request: Request):
    """Authenticate user and return access token."""
    try:
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Authenticate user
        user = auth_manager.authenticate_user(user_login.username, user_login.password)
        
        if not user:
            # Log failed attempt
            audit_logger.log_auth_failure(
                username=user_login.username,
                ip_address=client_ip,
                user_agent=user_agent,
                reason="Invalid credentials"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = auth_manager.create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        
        # Log successful login
        audit_logger.log_auth_success(
            username=user.username,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=1800  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


# Research endpoints
@app.post("/research", response_model=ResearchResponse)
async def create_research(
    research_request: ResearchRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new research request."""
    try:
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        
        # Create research request
        request_id = research_manager.create_request(
            query=research_request.query,
            username=current_user.username,
            thread_id=research_request.thread_id,
            save_report=research_request.save_report,
            ip_address=client_ip
        )
        
        # Start research execution
        research_manager.start_research(request_id)
        
        # Get and return request data
        request_data = research_manager.get_request(request_id)
        return research_manager.to_response_model(request_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create research request: {str(e)}"
        )


@app.get("/research/{request_id}", response_model=ResearchResponse)
async def get_research(
    request_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get research request details."""
    request_data = research_manager.get_request(request_id)
    
    if not request_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research request not found"
        )
    
    # Check if user owns this request
    if request_data["username"] != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return research_manager.to_response_model(request_data)


@app.get("/research", response_model=ResearchListResponse)
async def list_research(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_active_user)
):
    """List user's research requests."""
    if per_page > 100:
        per_page = 100
    
    requests, total = research_manager.get_user_requests(
        username=current_user.username,
        page=page,
        per_page=per_page
    )
    
    items = [research_manager.to_summary_model(req) for req in requests]
    
    return ResearchListResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=items
    )


# User profile endpoints
@app.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get user profile."""
    user_db = auth_manager.get_user(current_user.username)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user statistics
    requests, total = research_manager.get_user_requests(current_user.username, per_page=1000)
    successful = sum(1 for req in requests if req["status"] == "completed")
    failed = sum(1 for req in requests if req["status"] == "failed")
    
    return UserProfile(
        username=user_db.username,
        email=user_db.email,
        full_name=user_db.full_name,
        created_at=user_db.created_at,
        last_login=user_db.last_login,
        total_research_requests=total,
        successful_requests=successful,
        failed_requests=failed
    )


# System endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint."""
    uptime = time.time() - getattr(request.app.state, 'start_time', time.time())
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime_seconds=uptime,
        active_requests=getattr(request.app.state, 'active_requests', 0),
        total_requests=getattr(request.app.state, 'total_requests', 0),
        total_users=len(auth_manager._load_users()),
        config=Config.get_safe_config()
    )


@app.get("/audit", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = 1,
    per_page: int = 50,
    days: int = 7,
    current_user: User = Depends(get_current_active_user)
):
    """Get audit logs (user can only see their own logs)."""
    if per_page > 100:
        per_page = 100
    
    # Get user's audit logs
    logs = audit_logger.get_recent_logs(days=days, username=current_user.username)
    
    # Pagination
    total = len(logs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_logs = logs[start:end]
    
    return AuditLogResponse(
        total=total,
        page=page,
        per_page=per_page,
        entries=paginated_logs
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)