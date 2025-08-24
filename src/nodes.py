"""
LangGraph nodes implementation for the Research Assistant Agent.
Implements the ReAct pattern with planning, searching, validation, synthesis, and reflexion.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
import uuid

from .state import ResearchState, SearchResult, SafetyCheck
from .tools import TavilySearchTool, GeminiLLM
from .safety import SafetyValidator
from .config import Config


class ResearchNodes:
    """Collection of nodes for the research workflow."""
    
    def __init__(self):
        self.search_tool = TavilySearchTool(Config.TAVILY_API_KEY)
        self.llm = GeminiLLM(Config.GEMINI_API_KEY)
        self.safety_validator = SafetyValidator()
    
    async def plan_node(self, state: ResearchState) -> ResearchState:
        """
        Planning node: Creates research plan and search strategy.
        First step in the ReAct workflow.
        """
        print(f"Planning research for: {state['research_query']}")
        
        try:
            # Generate research plan using LLM
            planning_output = await self.llm.generate_plan(state['research_query'])
            
            # Update state
            state['plan'] = planning_output.research_plan
            state['current_step'] = 'planning_complete'
            state['timestamp'] = datetime.now().isoformat()
            
            # Store search queries for next step
            state['search_queries'] = planning_output.search_queries
            
            print(f"Plan created: {planning_output.research_plan[:100]}...")
            
        except Exception as e:
            error_msg = f"Planning failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'planning_failed'
            print(f"ERROR: {error_msg}")
        
        return state
    
    async def search_node(self, state: ResearchState) -> ResearchState:
        """
        Search node: Executes search queries and gathers sources.
        Acting component of ReAct pattern.
        """
        print(f"Searching for information...")
        
        try:
            all_results = []
            search_queries = state.get('search_queries', [state['research_query']])
            
            # Execute multiple search queries
            for query in search_queries[:3]:  # Limit to 3 queries
                print(f"  Searching: {query}")
                results = await self.search_tool.search(
                    query=query, 
                    max_results=Config.MAX_SEARCH_RESULTS // len(search_queries)
                )
                all_results.extend(results)
            
            # Remove duplicates based on URL
            unique_results = []
            seen_urls = set()
            for result in all_results:
                if result.url not in seen_urls:
                    unique_results.append(result)
                    seen_urls.add(result.url)
            
            # Sort by score and take top results
            unique_results.sort(key=lambda x: x.score, reverse=True)
            state['sources'] = unique_results[:Config.MAX_SEARCH_RESULTS]
            
            state['current_step'] = 'search_complete'
            print(f"Found {len(state['sources'])} sources")
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'search_failed'
            print(f"ERROR: {error_msg}")
        
        return state
    
    async def validate_node(self, state: ResearchState) -> ResearchState:
        """
        Validation node: Validates sources for safety and reliability.
        Safety layer in the workflow.
        """
        print(f"Validating {len(state['sources'])} sources...")
        
        try:
            # Validate all search results
            safety_checks = self.safety_validator.validate_search_results(state['sources'])
            
            # Filter safe sources
            safe_sources = []
            for i, source in enumerate(state['sources']):
                # Get safety checks for this source (URL + content + title)
                source_checks = safety_checks[i*3:(i+1)*3]  # 3 checks per source
                aggregated_check = self.safety_validator.aggregate_safety_checks(source_checks)
                
                if aggregated_check.is_safe:
                    safe_sources.append(source)
                else:
                    print(f"  WARNING: Filtered unsafe source: {source.url}")
            
            state['sources'] = safe_sources
            state['safety_checks'] = safety_checks
            state['current_step'] = 'validation_complete'
            
            print(f"Validated sources: {len(safe_sources)} safe sources")
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'validation_failed'
            print(f"ERROR: {error_msg}")
        
        return state
    
    async def synthesize_node(self, state: ResearchState) -> ResearchState:
        """
        Synthesis node: Synthesizes research findings into coherent output.
        Reasoning component of ReAct pattern.
        """
        print(f"Synthesizing research from {len(state['sources'])} sources...")
        
        try:
            if not state['sources']:
                raise ValueError("No sources available for synthesis")
            
            # Synthesize research using LLM
            synthesis_output = await self.llm.synthesize_research(
                state['research_query'], 
                state['sources']
            )
            
            # Create comprehensive draft
            draft = f"""# Research Summary: {state['research_query']}

## Overview
{synthesis_output.research_summary}

## Key Findings
{chr(10).join(f"• {finding}" for finding in synthesis_output.key_findings)}

## Sources
{chr(10).join(f"• {source}" for source in synthesis_output.sources_used)}

## Confidence Level
{synthesis_output.confidence_level:.2f} (out of 1.0)

## Recommendations
{chr(10).join(f"• {rec}" for rec in synthesis_output.recommendations)}

---
*Research completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            state['draft'] = draft
            state['current_step'] = 'synthesis_complete'
            
            print(f"Research synthesized (confidence: {synthesis_output.confidence_level:.2f})")
            
        except Exception as e:
            error_msg = f"Synthesis failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'synthesis_failed'
            print(f"ERROR: {error_msg}")
        
        return state
    
    async def safety_node(self, state: ResearchState) -> ResearchState:
        """
        Safety node: Final safety validation of the complete output.
        Final safety check before completion.
        """
        print(f"Final safety validation...")
        
        try:
            # Validate final output
            final_check = self.safety_validator.validate_final_output(state['draft'])
            
            state['is_safe'] = final_check.is_safe
            state['safety_checks'].append(final_check)
            
            if final_check.is_safe:
                state['current_step'] = 'completed'
                print(f"Research completed safely")
            else:
                state['current_step'] = 'safety_failed'
                print(f"WARNING: Safety validation failed: {final_check.reason}")
                
                # Add flagged content to warnings
                if final_check.flagged_content:
                    state['warnings'].extend(final_check.flagged_content)
            
        except Exception as e:
            error_msg = f"Safety validation failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'safety_validation_failed'
            state['is_safe'] = False
            print(f"ERROR: {error_msg}")
        
        return state
    
    async def reflexion_node(self, state: ResearchState) -> ResearchState:
        """
        Reflexion node: Analyzes failures and suggests improvements.
        Self-improvement component for failed attempts.
        """
        print(f"Performing reflexion on failed attempt...")
        
        try:
            # Prepare context for reflexion
            error_context = "; ".join(state['errors'][-3:])  # Last 3 errors
            previous_attempt = state.get('draft', 'No draft generated')
            
            # Perform reflexion using LLM
            reflexion_output = await self.llm.perform_reflexion(
                state['research_query'],
                previous_attempt,
                error_context
            )
            
            # Update state with reflexion insights
            state['critique'] = reflexion_output.critique
            state['improvements'] = reflexion_output.improvement_suggestions
            
            # Update plan if suggested
            if reflexion_output.revised_plan:
                state['plan'] = reflexion_output.revised_plan
            
            # Determine next action
            if reflexion_output.should_retry and state['retry_count'] < state['max_retries']:
                state['retry_count'] += 1
                state['current_step'] = 'retry_planning'
                print(f"Retry {state['retry_count']}/{state['max_retries']} - {reflexion_output.critique[:100]}...")
            else:
                state['current_step'] = 'max_retries_reached'
                print(f"Max retries reached or retry not recommended")
            
        except Exception as e:
            error_msg = f"Reflexion failed: {str(e)}"
            state['errors'].append(error_msg)
            state['current_step'] = 'reflexion_failed'
            print(f"ERROR: {error_msg}")
        
        return state


def create_initial_state(research_query: str) -> ResearchState:
    """Create initial state for the research workflow."""
    return ResearchState(
        research_query=research_query,
        plan="",
        sources=[],
        draft="",
        safety_checks=[],
        is_safe=True,
        current_step="initialized",
        retry_count=0,
        max_retries=Config.MAX_RETRIES,
        critique="",
        improvements=[],
        timestamp=datetime.now().isoformat(),
        request_id=str(uuid.uuid4()),
        errors=[],
        warnings=[],
        search_queries=[]
    )