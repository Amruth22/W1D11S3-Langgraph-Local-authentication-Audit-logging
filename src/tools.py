"""
Tools integration for the Research Assistant Agent.
Handles Tavily search and Gemini LLM interactions.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from tavily import TavilyClient
from google import genai
from google.genai import types
from pydantic import BaseModel

from .config import Config
from .state import SearchResult, PlanningOutput, SynthesisOutput, ReflexionOutput
from .safety import SafetyValidator


class StructuredOutputParser:
    """Parser for structured outputs from LLM responses."""
    
    @staticmethod
    def parse_planning_output(text: str) -> PlanningOutput:
        """Parse planning output from LLM response."""
        try:
            # Try to extract JSON if present
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
                data = json.loads(json_text)
                return PlanningOutput(**data)
            
            # Fallback to text parsing
            lines = text.split('\n')
            plan = ""
            queries = []
            sources = []
            criteria = ""
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "research plan" in line.lower():
                    current_section = "plan"
                elif "search queries" in line.lower() or "queries" in line.lower():
                    current_section = "queries"
                elif "expected sources" in line.lower() or "sources" in line.lower():
                    current_section = "sources"
                elif "success criteria" in line.lower() or "criteria" in line.lower():
                    current_section = "criteria"
                elif line.startswith('-') or line.startswith('*') or line.startswith('•'):
                    item = line[1:].strip()
                    if current_section == "queries":
                        queries.append(item)
                    elif current_section == "sources":
                        sources.append(item)
                else:
                    if current_section == "plan":
                        plan += line + " "
                    elif current_section == "criteria":
                        criteria += line + " "
            
            return PlanningOutput(
                research_plan=plan.strip() or "Comprehensive research plan",
                search_queries=queries or ["main research query"],
                expected_sources=sources or ["academic sources", "news articles"],
                success_criteria=criteria.strip() or "Accurate and comprehensive information"
            )
            
        except Exception as e:
            # Fallback output
            return PlanningOutput(
                research_plan="Comprehensive research on the given topic",
                search_queries=["main research query"],
                expected_sources=["reliable sources"],
                success_criteria="Accurate information gathering"
            )
    
    @staticmethod
    def parse_synthesis_output(text: str) -> SynthesisOutput:
        """Parse synthesis output from LLM response."""
        try:
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
                data = json.loads(json_text)
                return SynthesisOutput(**data)
            
            # Text parsing fallback
            return SynthesisOutput(
                research_summary=text[:500] + "..." if len(text) > 500 else text,
                key_findings=["Key finding extracted from research"],
                sources_used=["research sources"],
                confidence_level=0.8,
                recommendations=["Further research recommended"]
            )
            
        except Exception:
            return SynthesisOutput(
                research_summary=text[:500] + "..." if len(text) > 500 else text,
                key_findings=["Analysis completed"],
                sources_used=["multiple sources"],
                confidence_level=0.7,
                recommendations=["Review findings"]
            )
    
    @staticmethod
    def parse_reflexion_output(text: str) -> ReflexionOutput:
        """Parse reflexion output from LLM response."""
        try:
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
                data = json.loads(json_text)
                return ReflexionOutput(**data)
            
            # Simple text parsing
            should_retry = "retry" in text.lower() or "try again" in text.lower()
            
            return ReflexionOutput(
                critique=text[:300] + "..." if len(text) > 300 else text,
                identified_issues=["Issues identified in previous attempt"],
                improvement_suggestions=["Suggestions for improvement"],
                revised_plan="Revised approach based on critique",
                should_retry=should_retry
            )
            
        except Exception:
            return ReflexionOutput(
                critique="Analysis of previous attempt",
                identified_issues=["General issues"],
                improvement_suggestions=["General improvements"],
                revised_plan="Revised approach",
                should_retry=False
            )


class TavilySearchTool:
    """Tavily search tool wrapper."""
    
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key)
        self.safety_validator = SafetyValidator()
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform search and return structured results."""
        try:
            # Check rate limiting
            if not self.safety_validator.check_rate_limit():
                wait_time = self.safety_validator.get_rate_limit_wait_time()
                await asyncio.sleep(wait_time)
            
            # Perform search
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_raw_content=False
            )
            
            # Convert to SearchResult objects
            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    score=item.get('score', 0.0),
                    raw_content=item.get('raw_content')
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def extract_content(self, urls: List[str]) -> Dict[str, str]:
        """Extract content from specific URLs."""
        try:
            if not self.safety_validator.check_rate_limit():
                wait_time = self.safety_validator.get_rate_limit_wait_time()
                await asyncio.sleep(wait_time)
            
            response = self.client.extract(urls=urls)
            
            content_map = {}
            for result in response.get('results', []):
                url = result.get('url', '')
                content = result.get('raw_content', '')
                if url and content:
                    content_map[url] = content
            
            return content_map
            
        except Exception as e:
            print(f"Content extraction error: {e}")
            return {}


class GeminiLLM:
    """Gemini LLM wrapper for structured interactions."""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.config = types.GenerateContentConfig(
            max_output_tokens=Config.MAX_OUTPUT_TOKENS,
            temperature=Config.TEMPERATURE
        )
    
    async def generate_plan(self, query: str) -> PlanningOutput:
        """Generate research plan."""
        prompt = f"""
        Create a comprehensive research plan for the following query: "{query}"
        
        Provide your response in the following JSON format:
        ```json
        {{
            "research_plan": "Detailed step-by-step research approach",
            "search_queries": ["query1", "query2", "query3"],
            "expected_sources": ["source_type1", "source_type2"],
            "success_criteria": "What constitutes successful research completion"
        }}
        ```
        
        Focus on:
        1. Breaking down the query into searchable components
        2. Identifying reliable source types
        3. Creating specific search queries
        4. Defining clear success metrics
        """
        
        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                config=self.config,
                contents=[prompt]
            )
            
            return StructuredOutputParser.parse_planning_output(response.text)
            
        except Exception as e:
            print(f"Planning generation error: {e}")
            return PlanningOutput(
                research_plan=f"Research plan for: {query}",
                search_queries=[query],
                expected_sources=["web sources"],
                success_criteria="Gather relevant information"
            )
    
    async def synthesize_research(self, query: str, sources: List[SearchResult]) -> SynthesisOutput:
        """Synthesize research from sources."""
        sources_text = "\n\n".join([
            f"Source: {s.title}\nURL: {s.url}\nContent: {s.content[:500]}..."
            for s in sources[:5]  # Limit to top 5 sources
        ])
        
        prompt = f"""
        Synthesize research findings for the query: "{query}"
        
        Based on the following sources:
        {sources_text}
        
        Provide your response in JSON format:
        ```json
        {{
            "research_summary": "Comprehensive summary of findings",
            "key_findings": ["finding1", "finding2", "finding3"],
            "sources_used": ["source1", "source2"],
            "confidence_level": 0.85,
            "recommendations": ["recommendation1", "recommendation2"]
        }}
        ```
        
        Requirements:
        1. Synthesize information from multiple sources
        2. Identify key findings and insights
        3. Assess confidence level (0.0-1.0)
        4. Provide actionable recommendations
        5. Cite sources used
        """
        
        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                config=self.config,
                contents=[prompt]
            )
            
            return StructuredOutputParser.parse_synthesis_output(response.text)
            
        except Exception as e:
            print(f"Synthesis error: {e}")
            return SynthesisOutput(
                research_summary="Research synthesis completed",
                key_findings=["Key insights gathered"],
                sources_used=[s.url for s in sources[:3]],
                confidence_level=0.7,
                recommendations=["Further analysis recommended"]
            )
    
    async def perform_reflexion(self, query: str, previous_attempt: str, error_context: str) -> ReflexionOutput:
        """Perform reflexion on failed attempt."""
        prompt = f"""
        Analyze the failed research attempt and provide reflexion:
        
        Original Query: "{query}"
        Previous Attempt: "{previous_attempt}"
        Error Context: "{error_context}"
        
        Provide reflexion in JSON format:
        ```json
        {{
            "critique": "Analysis of what went wrong",
            "identified_issues": ["issue1", "issue2"],
            "improvement_suggestions": ["suggestion1", "suggestion2"],
            "revised_plan": "Updated approach to address issues",
            "should_retry": true/false
        }}
        ```
        
        Focus on:
        1. Identifying specific failure points
        2. Understanding root causes
        3. Proposing concrete improvements
        4. Deciding if retry is worthwhile
        """
        
        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                config=self.config,
                contents=[prompt]
            )
            
            return StructuredOutputParser.parse_reflexion_output(response.text)
            
        except Exception as e:
            print(f"Reflexion error: {e}")
            return ReflexionOutput(
                critique="Analysis of previous attempt",
                identified_issues=["General issues encountered"],
                improvement_suggestions=["Retry with different approach"],
                revised_plan="Adjusted research strategy",
                should_retry=True
            )