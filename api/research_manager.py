"""
Research request manager for the FastAPI application.
Handles research request lifecycle and storage.
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from .models import ResearchStatus, ResearchResponse, ResearchSummary
from .audit import audit_logger
from src.graph import ResearchWorkflow
from src.state import ResearchState

# Load environment variables
load_dotenv()


class ResearchManager:
    """Manages research requests and their lifecycle."""
    
    def __init__(self, storage_dir: str = None):
        # Use environment variable or default
        storage_dir = storage_dir or os.getenv("RESEARCH_STORAGE_DIR", "data/research")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for active requests
        self.active_requests: Dict[str, Dict] = {}
        
        # Thread pool for background research tasks
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Research workflow instance
        self.workflow = ResearchWorkflow()
    
    def _get_request_file(self, request_id: str) -> Path:
        """Get file path for request data."""
        return self.storage_dir / f"{request_id}.json"
    
    def _save_request(self, request_id: str, data: Dict):
        """Save request data to file."""
        request_file = self._get_request_file(request_id)
        with open(request_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_request(self, request_id: str) -> Optional[Dict]:
        """Load request data from file."""
        request_file = self._get_request_file(request_id)
        if not request_file.exists():
            return None
        
        try:
            with open(request_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def create_request(
        self,
        query: str,
        username: str,
        thread_id: Optional[str] = None,
        save_report: bool = True,
        ip_address: str = "unknown"
    ) -> str:
        """Create a new research request."""
        request_id = str(uuid.uuid4())
        
        request_data = {
            "request_id": request_id,
            "status": ResearchStatus.PENDING,
            "query": query,
            "thread_id": thread_id,
            "save_report": save_report,
            "username": username,
            "ip_address": ip_address,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "start_time": None,
            "end_time": None,
            "duration_ms": None,
            
            # Results
            "draft": None,
            "sources_count": None,
            "confidence": None,
            "retry_count": None,
            "is_safe": None,
            
            # Errors
            "error_message": None,
            "errors": [],
            "warnings": [],
            
            # File info
            "report_file": None
        }
        
        # Save to file and memory
        self._save_request(request_id, request_data)
        self.active_requests[request_id] = request_data
        
        # Log request creation
        audit_logger.log_research_start(
            username=username,
            query=query,
            request_id=request_id,
            ip_address=ip_address
        )
        
        return request_id
    
    def start_research(self, request_id: str) -> bool:
        """Start research execution in background."""
        request_data = self.get_request(request_id)
        if not request_data or request_data["status"] != ResearchStatus.PENDING:
            return False
        
        # Update status
        request_data["status"] = ResearchStatus.RUNNING
        request_data["start_time"] = time.time()
        request_data["updated_at"] = datetime.now().isoformat()
        
        self._save_request(request_id, request_data)
        self.active_requests[request_id] = request_data
        
        # Start background task
        asyncio.create_task(self._execute_research(request_id))
        
        return True
    
    async def _execute_research(self, request_id: str):
        """Execute research in background."""
        request_data = self.get_request(request_id)
        if not request_data:
            return
        
        try:
            # Run research workflow
            result = await self.workflow.run_research(
                query=request_data["query"],
                thread_id=request_data["thread_id"]
            )
            
            # Calculate duration
            duration_ms = int((time.time() - request_data["start_time"]) * 1000)
            
            # Update request with results
            request_data.update({
                "status": ResearchStatus.COMPLETED,
                "end_time": time.time(),
                "duration_ms": duration_ms,
                "updated_at": datetime.now().isoformat(),
                
                # Results from research state
                "draft": result.get("draft"),
                "sources_count": len(result.get("sources", [])),
                "confidence": self._extract_confidence(result.get("draft", "")),
                "retry_count": result.get("retry_count", 0),
                "is_safe": result.get("is_safe", False),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                
                # Report file info
                "report_file": self._get_report_filename(request_data)
            })
            
            # Log completion
            audit_logger.log_research_complete(
                username=request_data["username"],
                request_id=request_id,
                duration_ms=duration_ms,
                sources_count=request_data["sources_count"],
                confidence=request_data["confidence"] or 0.0
            )
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - request_data["start_time"]) * 1000)
            
            # Update request with error
            request_data.update({
                "status": ResearchStatus.FAILED,
                "end_time": time.time(),
                "duration_ms": duration_ms,
                "updated_at": datetime.now().isoformat(),
                "error_message": str(e),
                "errors": [str(e)]
            })
            
            # Log failure
            audit_logger.log_research_failure(
                username=request_data["username"],
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(e)
            )
        
        finally:
            # Save final state
            self._save_request(request_id, request_data)
            self.active_requests[request_id] = request_data
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get request data."""
        # Try memory first
        if request_id in self.active_requests:
            return self.active_requests[request_id]
        
        # Try file storage
        return self._load_request(request_id)
    
    def get_user_requests(
        self,
        username: str,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[List[Dict], int]:
        """Get user's research requests."""
        all_requests = []
        
        # Load all request files
        for request_file in self.storage_dir.glob("*.json"):
            try:
                with open(request_file, 'r') as f:
                    data = json.load(f)
                    if data.get("username") == username:
                        all_requests.append(data)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        # Sort by created_at (newest first)
        all_requests.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Pagination
        total = len(all_requests)
        start = (page - 1) * per_page
        end = start + per_page
        
        return all_requests[start:end], total
    
    def _extract_confidence(self, draft: str) -> float:
        """Extract confidence level from draft text."""
        if not draft:
            return 0.0
        
        # Look for confidence level in the draft
        lines = draft.split('\n')
        for line in lines:
            if 'confidence level' in line.lower():
                try:
                    # Extract number from line like "0.85 (out of 1.0)"
                    parts = line.split()
                    for part in parts:
                        if part.replace('.', '').isdigit():
                            confidence = float(part)
                            if 0.0 <= confidence <= 1.0:
                                return confidence
                except (ValueError, IndexError):
                    continue
        
        return 0.8  # Default confidence
    
    def _get_report_filename(self, request_data: Dict) -> Optional[str]:
        """Generate report filename."""
        if not request_data.get("save_report"):
            return None
        
        timestamp = datetime.fromisoformat(request_data["created_at"]).strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in request_data["query"][:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')
        
        if request_data.get("thread_id"):
            return f"{timestamp}_{request_data['thread_id']}_{query_safe}.md"
        else:
            return f"{timestamp}_{query_safe}.md"
    
    def to_response_model(self, request_data: Dict) -> ResearchResponse:
        """Convert request data to response model."""
        return ResearchResponse(**request_data)
    
    def to_summary_model(self, request_data: Dict) -> ResearchSummary:
        """Convert request data to summary model."""
        return ResearchSummary(
            request_id=request_data["request_id"],
            status=request_data["status"],
            query=request_data["query"],
            created_at=request_data["created_at"],
            username=request_data["username"],
            sources_count=request_data.get("sources_count"),
            confidence=request_data.get("confidence")
        )


# Global research manager instance
research_manager = ResearchManager()