"""
Safety and validation components for the Research Assistant Agent.
Implements content moderation, URL validation, and rate limiting.
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re
from dataclasses import dataclass
from threading import Lock

from .config import Config
from .state import SafetyCheck, SearchResult


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if successful."""
        with self.lock:
            now = time.time()
            # Add tokens based on time passed
            tokens_to_add = (now - self.last_refill) * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time needed for tokens to be available."""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate


class URLValidator:
    """Validates URLs against whitelist and safety criteria."""
    
    def __init__(self, trusted_domains: set):
        self.trusted_domains = trusted_domains
    
    def is_trusted_domain(self, url: str) -> bool:
        """Check if URL belongs to a trusted domain."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check exact match or subdomain
            for trusted in self.trusted_domains:
                if domain == trusted or domain.endswith('.' + trusted):
                    return True
            
            return False
        except Exception:
            return False
    
    def validate_url(self, url: str) -> SafetyCheck:
        """Comprehensive URL validation."""
        try:
            parsed = urlparse(url)
            
            # Basic URL structure validation
            if not parsed.scheme or not parsed.netloc:
                return SafetyCheck(
                    is_safe=False,
                    reason="Invalid URL structure",
                    confidence=1.0,
                    flagged_content=[url]
                )
            
            # Protocol validation
            if parsed.scheme not in ['http', 'https']:
                return SafetyCheck(
                    is_safe=False,
                    reason="Unsupported protocol",
                    confidence=1.0,
                    flagged_content=[parsed.scheme]
                )
            
            # Domain trust validation
            is_trusted = self.is_trusted_domain(url)
            confidence = 0.9 if is_trusted else 0.3
            
            return SafetyCheck(
                is_safe=is_trusted,
                reason="Trusted domain" if is_trusted else "Untrusted domain",
                confidence=confidence,
                flagged_content=[] if is_trusted else [parsed.netloc]
            )
            
        except Exception as e:
            return SafetyCheck(
                is_safe=False,
                reason=f"URL validation error: {str(e)}",
                confidence=1.0,
                flagged_content=[url]
            )


class ContentModerationChain:
    """Content moderation using keyword filtering and pattern matching."""
    
    def __init__(self, blocked_keywords: List[str]):
        self.blocked_keywords = [kw.lower() for kw in blocked_keywords]
        self.suspicious_patterns = [
            r'\b(?:hack|crack|pirate|illegal)\b',
            r'\b(?:violence|violent|kill|murder)\b',
            r'\b(?:hate|racist|discrimination)\b',
            r'\b(?:explicit|adult|nsfw|porn)\b'
        ]
    
    def moderate_content(self, content: str) -> SafetyCheck:
        """Moderate content for safety violations."""
        if not content:
            return SafetyCheck(
                is_safe=True,
                reason="Empty content",
                confidence=1.0
            )
        
        content_lower = content.lower()
        flagged_content = []
        
        # Check blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in content_lower:
                flagged_content.append(keyword)
        
        # Check suspicious patterns
        for pattern in self.suspicious_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            flagged_content.extend(matches)
        
        is_safe = len(flagged_content) == 0
        confidence = 0.8 if is_safe else 0.9
        reason = "Content passed moderation" if is_safe else "Content flagged for review"
        
        return SafetyCheck(
            is_safe=is_safe,
            reason=reason,
            confidence=confidence,
            flagged_content=flagged_content
        )


class SafetyValidator:
    """Main safety validation orchestrator."""
    
    def __init__(self):
        self.url_validator = URLValidator(Config.TRUSTED_DOMAINS)
        self.content_moderator = ContentModerationChain(Config.BLOCKED_KEYWORDS)
        self.rate_limiter = TokenBucket(
            capacity=Config.RATE_LIMIT_REQUESTS_PER_MINUTE,
            refill_rate=Config.RATE_LIMIT_REQUESTS_PER_MINUTE / 60.0
        )
    
    def validate_search_results(self, results: List[SearchResult]) -> List[SafetyCheck]:
        """Validate a list of search results."""
        safety_checks = []
        
        for result in results:
            # URL validation
            url_check = self.url_validator.validate_url(result.url)
            safety_checks.append(url_check)
            
            # Content moderation
            content_check = self.content_moderator.moderate_content(result.content)
            safety_checks.append(content_check)
            
            # Title moderation
            title_check = self.content_moderator.moderate_content(result.title)
            safety_checks.append(title_check)
        
        return safety_checks
    
    def validate_final_output(self, content: str) -> SafetyCheck:
        """Validate final research output."""
        return self.content_moderator.moderate_content(content)
    
    def check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        return self.rate_limiter.consume()
    
    def get_rate_limit_wait_time(self) -> float:
        """Get wait time for rate limiting."""
        return self.rate_limiter.wait_time()
    
    def aggregate_safety_checks(self, checks: List[SafetyCheck]) -> SafetyCheck:
        """Aggregate multiple safety checks into a single result."""
        if not checks:
            return SafetyCheck(
                is_safe=True,
                reason="No checks performed",
                confidence=0.5
            )
        
        unsafe_checks = [check for check in checks if not check.is_safe]
        
        if not unsafe_checks:
            return SafetyCheck(
                is_safe=True,
                reason="All safety checks passed",
                confidence=min(check.confidence for check in checks)
            )
        
        # Aggregate flagged content
        all_flagged = []
        for check in unsafe_checks:
            all_flagged.extend(check.flagged_content)
        
        return SafetyCheck(
            is_safe=False,
            reason=f"Failed {len(unsafe_checks)} safety checks",
            confidence=max(check.confidence for check in unsafe_checks),
            flagged_content=list(set(all_flagged))  # Remove duplicates
        )