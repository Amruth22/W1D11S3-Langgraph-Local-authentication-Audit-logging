"""
API request and response models for the Research Assistant API.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ResearchStatus(str, Enum):
    """Research request status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchRequest(BaseModel):
    """Research request model."""
    query: str = Field(..., min_length=1, max_length=500, description="Research query")
    thread_id: Optional[str] = Field(None, description="Optional thread ID for checkpointing")
    save_report: bool = Field(True, description="Save report to markdown file")


class ResearchResponse(BaseModel):
    """Research response model."""
    request_id: str
    status: ResearchStatus
    query: str
    thread_id: Optional[str] = None
    created_at: str
    updated_at: str
    username: str
    
    # Results (only when completed)
    draft: Optional[str] = None
    sources_count: Optional[int] = None
    confidence: Optional[float] = None
    retry_count: Optional[int] = None
    is_safe: Optional[bool] = None
    
    # Error information (only when failed)
    error_message: Optional[str] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    # File information
    report_file: Optional[str] = None


class ResearchSummary(BaseModel):
    """Research summary for listing."""
    request_id: str
    status: ResearchStatus
    query: str
    created_at: str
    username: str
    sources_count: Optional[int] = None
    confidence: Optional[float] = None


class ResearchListResponse(BaseModel):
    """Research list response."""
    total: int
    page: int
    per_page: int
    items: List[ResearchSummary]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    
    # System info
    active_requests: int
    total_requests: int
    total_users: int
    
    # Configuration
    config: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    timestamp: str
    request_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    timestamp: str


class AuditLogEntry(BaseModel):
    """Audit log entry for API responses."""
    timestamp: str
    level: str
    action: str
    username: Optional[str] = None
    ip_address: Optional[str] = None
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None
    duration_ms: Optional[int] = None


class AuditLogResponse(BaseModel):
    """Audit log response."""
    total: int
    page: int
    per_page: int
    entries: List[AuditLogEntry]


class UserProfile(BaseModel):
    """User profile response."""
    username: str
    email: str
    full_name: str
    created_at: str
    last_login: Optional[str] = None
    
    # Statistics
    total_research_requests: int
    successful_requests: int
    failed_requests: int