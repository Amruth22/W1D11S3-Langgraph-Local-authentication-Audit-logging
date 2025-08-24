"""
State management for the Research Assistant Agent.
Defines the state structure using TypedDict for type safety.
"""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Individual search result structure."""
    url: str
    title: str
    content: str
    score: float
    raw_content: Optional[str] = None


class SafetyCheck(BaseModel):
    """Safety validation result."""
    is_safe: bool
    reason: str
    confidence: float
    flagged_content: List[str] = []


class ResearchState(TypedDict):
    """
    Main state structure for the research agent workflow.
    Maintains all necessary information throughout the graph execution.
    """
    # Core research data
    research_query: str
    plan: str
    sources: List[SearchResult]
    draft: str
    
    # Safety and validation
    safety_checks: List[SafetyCheck]
    is_safe: bool
    
    # Workflow control
    current_step: str
    retry_count: int
    max_retries: int
    
    # Reflexion and improvement
    critique: str
    improvements: List[str]
    
    # Metadata
    timestamp: str
    request_id: str
    
    # Error handling
    errors: List[str]
    warnings: List[str]


class PlanningOutput(BaseModel):
    """Structured output for planning node."""
    research_plan: str
    search_queries: List[str]
    expected_sources: List[str]
    success_criteria: str


class SynthesisOutput(BaseModel):
    """Structured output for synthesis node."""
    research_summary: str
    key_findings: List[str]
    sources_used: List[str]
    confidence_level: float
    recommendations: List[str]


class ReflexionOutput(BaseModel):
    """Structured output for reflexion node."""
    critique: str
    identified_issues: List[str]
    improvement_suggestions: List[str]
    revised_plan: str
    should_retry: bool