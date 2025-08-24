"""
Audit logging system for the Research Assistant API.
File-based audit logging with structured format.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel


class AuditAction(str, Enum):
    """Audit action types."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    
    # Research
    RESEARCH_START = "research_start"
    RESEARCH_COMPLETE = "research_complete"
    RESEARCH_FAILED = "research_failed"
    RESEARCH_VIEW = "research_view"
    
    # API
    API_ACCESS = "api_access"
    API_ERROR = "api_error"


class AuditLevel(str, Enum):
    """Audit log levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEntry(BaseModel):
    """Audit log entry model."""
    timestamp: str
    level: AuditLevel
    action: AuditAction
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None
    duration_ms: Optional[int] = None


class AuditLogger:
    """File-based audit logger."""
    
    def __init__(self, log_dir: str = "data/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self, date: datetime = None) -> Path:
        """Get log file path for date."""
        if date is None:
            date = datetime.now()
        
        filename = f"audit_{date.strftime('%Y%m%d')}.log"
        return self.log_dir / filename
    
    def _write_entry(self, entry: AuditEntry):
        """Write audit entry to file."""
        log_file = self._get_log_file()
        
        # Convert to JSON string
        log_line = entry.json() + "\n"
        
        # Append to file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
    
    def log(
        self,
        action: AuditAction,
        level: AuditLevel = AuditLevel.INFO,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Log audit entry."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            action=action,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            request_id=request_id,
            duration_ms=duration_ms
        )
        
        self._write_entry(entry)
    
    def log_auth_success(self, username: str, ip_address: str, user_agent: str):
        """Log successful authentication."""
        self.log(
            action=AuditAction.LOGIN,
            level=AuditLevel.INFO,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"status": "success"}
        )
    
    def log_auth_failure(self, username: str, ip_address: str, user_agent: str, reason: str):
        """Log failed authentication."""
        self.log(
            action=AuditAction.LOGIN_FAILED,
            level=AuditLevel.WARNING,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"status": "failed", "reason": reason}
        )
    
    def log_user_registration(self, username: str, email: str, ip_address: str):
        """Log user registration."""
        self.log(
            action=AuditAction.REGISTER,
            level=AuditLevel.INFO,
            username=username,
            ip_address=ip_address,
            details={"email": email, "status": "success"}
        )
    
    def log_research_start(
        self,
        username: str,
        query: str,
        request_id: str,
        ip_address: str
    ):
        """Log research start."""
        self.log(
            action=AuditAction.RESEARCH_START,
            level=AuditLevel.INFO,
            username=username,
            ip_address=ip_address,
            request_id=request_id,
            details={"query": query[:100]}  # Truncate long queries
        )
    
    def log_research_complete(
        self,
        username: str,
        request_id: str,
        duration_ms: int,
        sources_count: int,
        confidence: float
    ):
        """Log research completion."""
        self.log(
            action=AuditAction.RESEARCH_COMPLETE,
            level=AuditLevel.INFO,
            username=username,
            request_id=request_id,
            duration_ms=duration_ms,
            details={
                "sources_count": sources_count,
                "confidence": confidence,
                "status": "success"
            }
        )
    
    def log_research_failure(
        self,
        username: str,
        request_id: str,
        duration_ms: int,
        error: str
    ):
        """Log research failure."""
        self.log(
            action=AuditAction.RESEARCH_FAILED,
            level=AuditLevel.ERROR,
            username=username,
            request_id=request_id,
            duration_ms=duration_ms,
            details={"error": error, "status": "failed"}
        )
    
    def log_api_access(
        self,
        username: str,
        method: str,
        endpoint: str,
        ip_address: str,
        user_agent: str,
        status_code: int,
        duration_ms: int
    ):
        """Log API access."""
        level = AuditLevel.INFO if status_code < 400 else AuditLevel.WARNING
        
        self.log(
            action=AuditAction.API_ACCESS,
            level=level,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            details={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code
            }
        )
    
    def get_recent_logs(self, days: int = 7, username: Optional[str] = None) -> list:
        """Get recent audit logs."""
        logs = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = self._get_log_file(date)
            
            if not log_file.exists():
                continue
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if username is None or entry.get('username') == username:
                            logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs


# Global audit logger instance
audit_logger = AuditLogger()