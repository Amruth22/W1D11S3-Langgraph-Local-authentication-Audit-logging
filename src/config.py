"""
Configuration management for the Research Assistant Agent.
Handles environment variables, API keys, and system settings.
"""

import os
from typing import List, Set
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Validate that .env file was loaded
if not os.getenv("GEMINI_API_KEY") and not os.getenv("TAVILY_API_KEY"):
    print("WARNING: No API keys found in environment variables.")
    print("Please ensure .env file exists with GEMINI_API_KEY and TAVILY_API_KEY")


class Config:
    """Configuration class for the research agent."""
    
    # API Keys (loaded from .env file)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # LLM Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "1000"))
    
    # Workflow Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    MAX_SEARCH_RESULTS: int = 10
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    
    # Safety Configuration
    TRUSTED_DOMAINS: Set[str] = {
        "wikipedia.org",
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "scholar.google.com",
        "ieee.org",
        "acm.org",
        "nature.com",
        "science.org",
        "reuters.com",
        "bbc.com",
        "cnn.com",
        "nytimes.com",
        "wsj.com",
        "bloomberg.com",
        "techcrunch.com",
        "wired.com",
        "mit.edu",
        "stanford.edu",
        "harvard.edu",
        "github.com",
        "stackoverflow.com",
        # Tech and Hardware Sources
        "nvidia.com",
        "amd.com",
        "intel.com",
        "microsoft.com",
        "apple.com",
        "google.com",
        "techpowerup.com",
        "anandtech.com",
        "tomshardware.com",
        "pcgamer.com",
        "ign.com",
        "gamespot.com",
        "polygon.com",
        "theverge.com",
        "engadget.com",
        "ars-technica.com",
        "zdnet.com",
        "cnet.com",
        "pcworld.com",
        "computerworld.com",
        "guru3d.com",
        "reddit.com",
        "notebookcheck.net",
        "digitaltrends.com",
        "tweaktown.com",
        "overclock3d.net",
        "hardwarecanucks.com",
        "techspot.com",
        "phoronix.com"
    }
    
    # Content Moderation
    BLOCKED_KEYWORDS: List[str] = [
        "violence", "hate", "harassment", "illegal", "harmful",
        "dangerous", "explicit", "adult", "nsfw"
    ]
    
    # Search Configuration
    SEARCH_TIMEOUT: int = 30
    MAX_CONTENT_LENGTH: int = 10000
    
    # Checkpointing
    CHECKPOINT_ENABLED: bool = True
    CHECKPOINT_PATH: str = "./checkpoints"
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required configuration is present."""
        # Check if API keys are present and valid
        if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY.startswith("your_"):
            print("ERROR: GEMINI_API_KEY not found or invalid")
            return False
        
        if not cls.TAVILY_API_KEY or cls.TAVILY_API_KEY.startswith("your_"):
            print("ERROR: TAVILY_API_KEY not found or invalid")
            return False
        
        # Validate Gemini API key format (should start with 'AIza')
        if not cls.GEMINI_API_KEY.startswith('AIza') or len(cls.GEMINI_API_KEY) < 30:
            print("ERROR: GEMINI_API_KEY appears to be invalid format")
            return False
        
        # Validate Tavily API key format (should start with 'tvly-')
        if not cls.TAVILY_API_KEY.startswith('tvly-') or len(cls.TAVILY_API_KEY) < 20:
            print("ERROR: TAVILY_API_KEY appears to be invalid format")
            return False
        
        return True
    
    @classmethod
    def get_safe_config(cls) -> dict:
        """Get configuration without sensitive information for logging."""
        return {
            "model": cls.GEMINI_MODEL,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_OUTPUT_TOKENS,
            "max_retries": cls.MAX_RETRIES,
            "rate_limit": cls.RATE_LIMIT_REQUESTS_PER_MINUTE,
            "trusted_domains_count": len(cls.TRUSTED_DOMAINS),
            "checkpoint_enabled": cls.CHECKPOINT_ENABLED
        }