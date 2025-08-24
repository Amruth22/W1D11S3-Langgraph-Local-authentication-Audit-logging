"""
Middleware for the Research Assistant API.
Handles audit logging, request tracking, and CORS.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .audit import audit_logger, AuditAction, AuditLevel


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get username from token if available
        username = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from .auth import auth_manager
                token = auth_header.split(" ")[1]
                username = auth_manager.verify_token(token)
        except Exception:
            pass
        
        # Start timing
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log API access
            audit_logger.log_api_access(
                username=username or "anonymous",
                method=request.method,
                endpoint=str(request.url.path),
                ip_address=client_ip,
                user_agent=user_agent,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            audit_logger.log(
                action=AuditAction.API_ERROR,
                level=AuditLevel.ERROR,
                username=username or "anonymous",
                ip_address=client_ip,
                user_agent=user_agent,
                duration_ms=duration_ms,
                request_id=request_id,
                details={
                    "method": request.method,
                    "endpoint": str(request.url.path),
                    "error": str(e)
                }
            )
            
            raise


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and statistics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.total_requests = 0
        self.active_requests = 0
        self.start_time = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Increment counters
        self.total_requests += 1
        self.active_requests += 1
        
        # Store stats in app state
        request.app.state.total_requests = self.total_requests
        request.app.state.active_requests = self.active_requests
        request.app.state.start_time = self.start_time
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Decrement active requests
            self.active_requests -= 1
            request.app.state.active_requests = self.active_requests


def setup_middleware(app):
    """Setup all middleware for the FastAPI app."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request tracking middleware
    app.add_middleware(RequestTrackingMiddleware)
    
    # Audit logging middleware
    app.add_middleware(AuditMiddleware)