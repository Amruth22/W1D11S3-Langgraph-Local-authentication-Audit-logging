#!/usr/bin/env python3
"""
API server runner for the Research Assistant API.
"""

import uvicorn
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.main import app
from src.config import Config


def main():
    """Run the FastAPI server."""
    parser = argparse.ArgumentParser(description="Research Assistant API Server")
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("API_WORKERS", "1")),
        help="Number of worker processes (default from .env or 1)"
    )
    
    parser.add_argument(
        "--log-level",
        default=os.getenv("API_LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default from .env or info)"
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    if not Config.validate_config():
        print("ERROR: Configuration validation failed!")
        print("Please check your API keys in environment variables or .env file")
        sys.exit(1)
    
    print("Starting Research Assistant API Server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print(f"Workers: {args.workers}")
    print(f"Log Level: {args.log_level}")
    print("-" * 50)
    
    # Run server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,  # Workers don't work with reload
        log_level=args.log_level,
        access_log=True
    )


if __name__ == "__main__":
    main()
