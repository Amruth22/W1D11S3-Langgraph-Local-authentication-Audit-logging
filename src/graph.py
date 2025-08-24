"""
LangGraph workflow orchestration for the Research Assistant Agent.
Defines the graph structure, conditional edges, and execution flow.
"""

import os
from datetime import datetime
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ResearchState
from .nodes import ResearchNodes, create_initial_state
from .config import Config


class ResearchWorkflow:
    """Main workflow orchestrator using LangGraph."""
    
    def __init__(self):
        self.nodes = ResearchNodes()
        self.checkpointer = MemorySaver() if Config.CHECKPOINT_ENABLED else None
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(ResearchState)
        
        # Add nodes
        workflow.add_node("plan", self.nodes.plan_node)
        workflow.add_node("search", self.nodes.search_node)
        workflow.add_node("validate", self.nodes.validate_node)
        workflow.add_node("synthesize", self.nodes.synthesize_node)
        workflow.add_node("safety", self.nodes.safety_node)
        workflow.add_node("reflexion", self.nodes.reflexion_node)
        
        # Set entry point
        workflow.set_entry_point("plan")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "plan",
            self._route_after_planning,
            {
                "search": "search",
                "reflexion": "reflexion",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "search",
            self._route_after_search,
            {
                "validate": "validate",
                "reflexion": "reflexion",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {
                "synthesize": "synthesize",
                "reflexion": "reflexion",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "synthesize",
            self._route_after_synthesis,
            {
                "safety": "safety",
                "reflexion": "reflexion",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "safety",
            self._route_after_safety,
            {
                "end": END,
                "reflexion": "reflexion"
            }
        )
        
        workflow.add_conditional_edges(
            "reflexion",
            self._route_after_reflexion,
            {
                "plan": "plan",
                "end": END
            }
        )
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _route_after_planning(self, state: ResearchState) -> Literal["search", "reflexion", "end"]:
        """Route after planning step."""
        current_step = state.get('current_step', '')
        
        if current_step == 'planning_complete':
            return "search"
        elif current_step == 'planning_failed':
            if state['retry_count'] < state['max_retries']:
                return "reflexion"
            else:
                return "end"
        else:
            return "end"
    
    def _route_after_search(self, state: ResearchState) -> Literal["validate", "reflexion", "end"]:
        """Route after search step."""
        current_step = state.get('current_step', '')
        
        if current_step == 'search_complete':
            if state.get('sources', []):
                return "validate"
            else:
                # No sources found, try reflexion
                if state['retry_count'] < state['max_retries']:
                    return "reflexion"
                else:
                    return "end"
        elif current_step == 'search_failed':
            if state['retry_count'] < state['max_retries']:
                return "reflexion"
            else:
                return "end"
        else:
            return "end"
    
    def _route_after_validation(self, state: ResearchState) -> Literal["synthesize", "reflexion", "end"]:
        """Route after validation step."""
        current_step = state.get('current_step', '')
        
        if current_step == 'validation_complete':
            if state.get('sources', []):
                return "synthesize"
            else:
                # All sources filtered out
                if state['retry_count'] < state['max_retries']:
                    return "reflexion"
                else:
                    return "end"
        elif current_step == 'validation_failed':
            if state['retry_count'] < state['max_retries']:
                return "reflexion"
            else:
                return "end"
        else:
            return "end"
    
    def _route_after_synthesis(self, state: ResearchState) -> Literal["safety", "reflexion", "end"]:
        """Route after synthesis step."""
        current_step = state.get('current_step', '')
        
        if current_step == 'synthesis_complete':
            return "safety"
        elif current_step == 'synthesis_failed':
            if state['retry_count'] < state['max_retries']:
                return "reflexion"
            else:
                return "end"
        else:
            return "end"
    
    def _route_after_safety(self, state: ResearchState) -> Literal["end", "reflexion"]:
        """Route after safety validation."""
        current_step = state.get('current_step', '')
        is_safe = state.get('is_safe', False)
        
        if current_step == 'completed' and is_safe:
            return "end"
        elif current_step in ['safety_failed', 'safety_validation_failed'] or not is_safe:
            if state['retry_count'] < state['max_retries']:
                return "reflexion"
            else:
                return "end"
        else:
            return "end"
    
    def _route_after_reflexion(self, state: ResearchState) -> Literal["plan", "end"]:
        """Route after reflexion step."""
        current_step = state.get('current_step', '')
        
        if current_step == 'retry_planning':
            return "plan"
        else:
            return "end"
    
    async def run_research(self, query: str, thread_id: str = None) -> ResearchState:
        """
        Run the complete research workflow.
        
        Args:
            query: Research query to investigate
            thread_id: Optional thread ID for checkpointing
            
        Returns:
            Final research state
        """
        print(f"Starting research workflow for: '{query}'")
        print("=" * 60)
        
        # Create initial state
        initial_state = create_initial_state(query)
        
        # Configure execution
        config = {"configurable": {"thread_id": thread_id or "default"}} if self.checkpointer else {}
        
        try:
            # Execute the workflow
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Print final results
            self._print_results(final_state)
            
            # Save report to markdown file if completed successfully
            if final_state['current_step'] == 'completed' and final_state.get('draft'):
                self._save_report_to_file(final_state, thread_id)
            
            return final_state
            
        except Exception as e:
            print(f"ERROR: Workflow execution failed: {e}")
            initial_state['errors'].append(f"Workflow execution failed: {str(e)}")
            initial_state['current_step'] = 'workflow_failed'
            return initial_state
    
    def _print_results(self, state: ResearchState):
        """Print workflow results."""
        print("\n" + "=" * 60)
        print("RESEARCH WORKFLOW RESULTS")
        print("=" * 60)
        
        print(f"Query: {state['research_query']}")
        print(f"Status: {state['current_step']}")
        print(f"Retries: {state['retry_count']}/{state['max_retries']}")
        print(f"Safety: {'Safe' if state['is_safe'] else 'Unsafe'}")
        print(f"Sources: {len(state.get('sources', []))}")
        
        if state.get('errors'):
            print(f"Errors: {len(state['errors'])}")
            for error in state['errors'][-3:]:  # Show last 3 errors
                print(f"   - {error}")
        
        if state.get('warnings'):
            print(f"Warnings: {len(state['warnings'])}")
            for warning in state['warnings'][-3:]:  # Show last 3 warnings
                print(f"   - {warning}")
        
        if state.get('draft') and state['current_step'] == 'completed':
            print("\nRESEARCH RESULTS:")
            print("-" * 40)
            print(state['draft'])
        
        print("\n" + "=" * 60)
    
    def _save_report_to_file(self, state: ResearchState, thread_id: str = None):
        """Save the research report to a markdown file."""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_safe = "".join(c for c in state['research_query'][:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            query_safe = query_safe.replace(' ', '_')
            
            if thread_id:
                filename = f"{timestamp}_{thread_id}_{query_safe}.md"
            else:
                filename = f"{timestamp}_{query_safe}.md"
            
            filepath = os.path.join(reports_dir, filename)
            
            # Write the report to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(state['draft'])
            
            print(f"\nReport saved to: {filepath}")
            
        except Exception as e:
            print(f"WARNING: Failed to save report to file: {e}")
    
    async def get_state_history(self, thread_id: str) -> list:
        """Get execution history for a thread."""
        if not self.checkpointer:
            return []
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            history = []
            
            async for checkpoint in self.graph.aget_state_history(config):
                history.append({
                    "step": checkpoint.values.get('current_step', 'unknown'),
                    "timestamp": checkpoint.values.get('timestamp', ''),
                    "errors": len(checkpoint.values.get('errors', [])),
                    "sources": len(checkpoint.values.get('sources', []))
                })
            
            return history
            
        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []
    
    async def resume_from_checkpoint(self, thread_id: str) -> ResearchState:
        """Resume execution from a checkpoint."""
        if not self.checkpointer:
            raise ValueError("Checkpointing not enabled")
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get current state
            current_state = await self.graph.aget_state(config)
            
            if not current_state.values:
                raise ValueError(f"No checkpoint found for thread {thread_id}")
            
            print(f"Resuming from step: {current_state.values.get('current_step', 'unknown')}")
            
            # Resume execution
            final_state = await self.graph.ainvoke(None, config=config)
            
            self._print_results(final_state)
            return final_state
            
        except Exception as e:
            print(f"ERROR: Resume failed: {e}")
            raise


# Convenience function for direct usage
async def research_query(query: str, thread_id: str = None) -> ResearchState:
    """
    Convenience function to run research on a query.
    
    Args:
        query: Research question to investigate
        thread_id: Optional thread ID for checkpointing
        
    Returns:
        Research results state
    """
    workflow = ResearchWorkflow()
    return await workflow.run_research(query, thread_id)