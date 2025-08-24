"""
Main application entry point for the Research Assistant Agent.
Provides CLI interface and example usage.
"""

import asyncio
import argparse
import sys
from typing import Optional

from .graph import ResearchWorkflow, research_query
from .config import Config


async def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Research Assistant Agent with LangGraph & Gemini 2.0 Flash"
    )
    
    parser.add_argument(
        "query",
        help="Research query to investigate"
    )
    
    parser.add_argument(
        "--thread-id",
        help="Thread ID for checkpointing (optional)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint using thread-id"
    )
    
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show execution history for thread-id"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration"
    )
    
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save research report to markdown file (default: auto-save on completion)"
    )
    
    args = parser.parse_args()
    
    # Show configuration if requested
    if args.config:
        print("Current Configuration:")
        print("-" * 30)
        config = Config.get_safe_config()
        for key, value in config.items():
            print(f"{key}: {value}")
        print(f"config_valid: {Config.validate_config()}")
        return
    
    # Validate configuration
    if not Config.validate_config():
        print("ERROR: Configuration validation failed!")
        print("Please check your API keys in environment variables or .env file")
        sys.exit(1)
    
    # Create workflow
    workflow = ResearchWorkflow()
    
    try:
        if args.history and args.thread_id:
            # Show execution history
            print(f"Execution History for Thread: {args.thread_id}")
            print("-" * 50)
            
            history = await workflow.get_state_history(args.thread_id)
            
            if not history:
                print("No history found for this thread ID")
                return
            
            for i, checkpoint in enumerate(history):
                print(f"{i+1}. Step: {checkpoint['step']}")
                print(f"   Timestamp: {checkpoint['timestamp']}")
                print(f"   Errors: {checkpoint['errors']}")
                print(f"   Sources: {checkpoint['sources']}")
                print()
        
        elif args.resume and args.thread_id:
            # Resume from checkpoint
            print(f"Resuming execution for Thread: {args.thread_id}")
            result = await workflow.resume_from_checkpoint(args.thread_id)
            
        else:
            # Run new research
            result = await workflow.run_research(args.query, args.thread_id)
            
            # Manual save if requested (auto-save already happens in workflow)
            if args.save_report and result['current_step'] == 'completed' and result.get('draft'):
                print("\nManual save requested (note: auto-save already occurred)")
                workflow._save_report_to_file(result, args.thread_id)
            
            # Show final status
            if result['current_step'] == 'completed' and result['is_safe']:
                print("\nResearch completed successfully!")
            else:
                print(f"\nWARNING: Research ended with status: {result['current_step']}")
                if result.get('errors'):
                    print("Errors encountered:")
                    for error in result['errors']:
                        print(f"  - {error}")
    
    except KeyboardInterrupt:
        print("\nResearch interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"ERROR: Application error: {e}")
        sys.exit(1)


async def example_usage():
    """Example usage of the research agent."""
    print("Running Example Research Queries")
    print("=" * 50)
    
    # Example queries
    queries = [
        "What are the latest developments in quantum computing?",
        "How does climate change affect ocean currents?",
        "What are the benefits and risks of artificial intelligence in healthcare?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\nExample {i}: {query}")
        print("-" * 40)
        
        try:
            result = await research_query(query, thread_id=f"example_{i}")
            
            if result['current_step'] == 'completed':
                print("Research completed")
                print(f"Sources found: {len(result.get('sources', []))}")
                print(f"Safety status: {'Safe' if result['is_safe'] else 'Unsafe'}")
            else:
                print(f"WARNING: Research incomplete: {result['current_step']}")
        
        except Exception as e:
            print(f"ERROR: Example failed: {e}")
        
        print("\n" + "=" * 50)


if __name__ == "__main__":
    # Check if running examples
    if len(sys.argv) == 2 and sys.argv[1] == "--examples":
        asyncio.run(example_usage())
    else:
        asyncio.run(main())