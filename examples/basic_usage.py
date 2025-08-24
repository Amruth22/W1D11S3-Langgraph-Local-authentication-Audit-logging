"""
Basic usage examples for the Research Assistant Agent.
Demonstrates different ways to use the research workflow.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graph import research_query, ResearchWorkflow
from src.config import Config


async def simple_research_example():
    """Simple research example using the convenience function."""
    print("Simple Research Example")
    print("=" * 40)
    
    query = "What are the latest breakthroughs in renewable energy?"
    
    try:
        result = await research_query(query)
        
        print(f"Query: {query}")
        print(f"Status: {result['current_step']}")
        print(f"Sources found: {len(result.get('sources', []))}")
        
        if result['current_step'] == 'completed' and result.get('draft'):
            print("\nResearch Results:")
            print("-" * 20)
            print(result['draft'][:500] + "..." if len(result['draft']) > 500 else result['draft'])
        
    except Exception as e:
        print(f"Error: {e}")


async def workflow_with_checkpointing():
    """Example using workflow with checkpointing."""
    print("\nWorkflow with Checkpointing Example")
    print("=" * 45)
    
    workflow = ResearchWorkflow()
    thread_id = "checkpoint_example_1"
    query = "How does machine learning impact cybersecurity?"
    
    try:
        # Run research with checkpointing
        result = await workflow.run_research(query, thread_id=thread_id)
        
        print(f"\nThread ID: {thread_id}")
        print(f"Final Status: {result['current_step']}")
        
        # Show execution history
        print("\nExecution History:")
        history = await workflow.get_state_history(thread_id)
        for i, checkpoint in enumerate(history[-5:], 1):  # Last 5 steps
            print(f"{i}. {checkpoint['step']} - {checkpoint['timestamp'][:19]}")
        
    except Exception as e:
        print(f"Error: {e}")


async def multiple_queries_example():
    """Example running multiple research queries."""
    print("\nMultiple Queries Example")
    print("=" * 35)
    
    queries = [
        "What is the current state of quantum computing?",
        "How do electric vehicles impact the environment?",
        "What are the latest developments in gene therapy?"
    ]
    
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}: {query[:50]}...")
        
        try:
            result = await research_query(query, thread_id=f"multi_query_{i}")
            results.append({
                'query': query,
                'status': result['current_step'],
                'sources': len(result.get('sources', [])),
                'safe': result.get('is_safe', False)
            })
            
            print(f"   Status: {result['current_step']}")
            print(f"   Sources: {len(result.get('sources', []))}")
            print(f"   Safe: {'Yes' if result.get('is_safe') else 'No'}")
            
        except Exception as e:
            print(f"   Error: {e}")
            results.append({
                'query': query,
                'status': 'error',
                'sources': 0,
                'safe': False
            })
    
    # Summary
    print("\n📊 Summary:")
    print("-" * 20)
    successful = sum(1 for r in results if r['status'] == 'completed')
    total_sources = sum(r['sources'] for r in results)
    
    print(f"Successful queries: {successful}/{len(queries)}")
    print(f"Total sources found: {total_sources}")
    print(f"All safe: {'Yes' if all(r['safe'] for r in results) else 'No'}")


async def error_handling_example():
    """Example demonstrating error handling and reflexion."""
    print("\nError Handling & Reflexion Example")
    print("=" * 42)
    
    # Use a potentially problematic query
    query = "xyz123 invalid query test error handling"
    
    try:
        result = await research_query(query, thread_id="error_example")
        
        print(f"Query: {query}")
        print(f"Final Status: {result['current_step']}")
        print(f"Retry Count: {result['retry_count']}/{result['max_retries']}")
        
        if result.get('errors'):
            print(f"\nErrors encountered ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result.get('critique'):
            print(f"\nReflexion Critique:")
            print(f"  {result['critique'][:200]}...")
        
        if result.get('improvements'):
            print(f"\nSuggested Improvements:")
            for improvement in result['improvements']:
                print(f"  - {improvement}")
        
    except Exception as e:
        print(f"Error: {e}")


async def configuration_example():
    """Example showing configuration usage."""
    print("\nConfiguration Example")
    print("=" * 30)
    
    print("Current Configuration:")
    config = Config.get_safe_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    print(f"\nConfiguration Valid: {Config.validate_config()}")
    print(f"Trusted Domains: {len(Config.TRUSTED_DOMAINS)} domains")
    print(f"Blocked Keywords: {len(Config.BLOCKED_KEYWORDS)} keywords")


async def main():
    """Run all examples."""
    print("Research Assistant Agent - Examples")
    print("=" * 50)
    
    # Check configuration first
    if not Config.validate_config():
        print("ERROR: Configuration validation failed!")
        print("Please set your API keys in environment variables or .env file")
        return
    
    try:
        # Run examples
        await configuration_example()
        await simple_research_example()
        await workflow_with_checkpointing()
        await multiple_queries_example()
        await error_handling_example()
        
        print("\nAll examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    
    except Exception as e:
        print(f"\nERROR: Examples failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())