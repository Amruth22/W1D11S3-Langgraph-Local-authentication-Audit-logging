"""
Basic tests for the Research Assistant Agent.
Tests core functionality, state management, and safety features.
"""

import pytest
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.state import ResearchState, SearchResult, SafetyCheck
from src.config import Config
from src.safety import URLValidator, ContentModerationChain, SafetyValidator
from src.nodes import create_initial_state
from src.tools import StructuredOutputParser


class TestStateManagement:
    """Test state management functionality."""
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        query = "Test research query"
        state = create_initial_state(query)
        
        assert state['research_query'] == query
        assert state['plan'] == ""
        assert state['sources'] == []
        assert state['draft'] == ""
        assert state['is_safe'] == True
        assert state['current_step'] == "initialized"
        assert state['retry_count'] == 0
        assert state['max_retries'] == Config.MAX_RETRIES
        assert isinstance(state['errors'], list)
        assert isinstance(state['warnings'], list)
    
    def test_search_result_creation(self):
        """Test SearchResult model."""
        result = SearchResult(
            url="https://example.com",
            title="Test Title",
            content="Test content",
            score=0.85
        )
        
        assert result.url == "https://example.com"
        assert result.title == "Test Title"
        assert result.content == "Test content"
        assert result.score == 0.85
        assert result.raw_content is None
    
    def test_safety_check_creation(self):
        """Test SafetyCheck model."""
        check = SafetyCheck(
            is_safe=True,
            reason="Content passed validation",
            confidence=0.9,
            flagged_content=[]
        )
        
        assert check.is_safe == True
        assert check.reason == "Content passed validation"
        assert check.confidence == 0.9
        assert check.flagged_content == []


class TestSafetyValidation:
    """Test safety validation components."""
    
    def test_url_validator_trusted_domains(self):
        """Test URL validation for trusted domains."""
        validator = URLValidator({"example.com", "test.org"})
        
        # Test trusted domain
        assert validator.is_trusted_domain("https://example.com/page") == True
        assert validator.is_trusted_domain("https://www.example.com/page") == True
        assert validator.is_trusted_domain("https://sub.example.com/page") == True
        
        # Test untrusted domain
        assert validator.is_trusted_domain("https://malicious.com/page") == False
        assert validator.is_trusted_domain("https://example.net/page") == False
    
    def test_url_validator_validation(self):
        """Test comprehensive URL validation."""
        validator = URLValidator({"trusted.com"})
        
        # Valid trusted URL
        check = validator.validate_url("https://trusted.com/page")
        assert check.is_safe == True
        assert check.confidence > 0.8
        
        # Valid untrusted URL
        check = validator.validate_url("https://untrusted.com/page")
        assert check.is_safe == False
        assert check.confidence < 0.5
        
        # Invalid URL
        check = validator.validate_url("not-a-url")
        assert check.is_safe == False
        assert check.confidence == 1.0
    
    def test_content_moderation(self):
        """Test content moderation."""
        moderator = ContentModerationChain(["violence", "hate", "illegal"])
        
        # Safe content
        check = moderator.moderate_content("This is safe educational content about science.")
        assert check.is_safe == True
        assert len(check.flagged_content) == 0
        
        # Unsafe content
        check = moderator.moderate_content("This content contains violence and hate speech.")
        assert check.is_safe == False
        assert len(check.flagged_content) > 0
        assert "violence" in check.flagged_content
        assert "hate" in check.flagged_content
    
    def test_safety_validator_aggregation(self):
        """Test safety check aggregation."""
        validator = SafetyValidator()
        
        # All safe checks
        safe_checks = [
            SafetyCheck(is_safe=True, reason="Safe", confidence=0.9),
            SafetyCheck(is_safe=True, reason="Safe", confidence=0.8)
        ]
        
        result = validator.aggregate_safety_checks(safe_checks)
        assert result.is_safe == True
        assert result.confidence == 0.8  # Minimum confidence
        
        # Mixed checks
        mixed_checks = [
            SafetyCheck(is_safe=True, reason="Safe", confidence=0.9),
            SafetyCheck(is_safe=False, reason="Unsafe", confidence=0.95, flagged_content=["bad"])
        ]
        
        result = validator.aggregate_safety_checks(mixed_checks)
        assert result.is_safe == False
        assert result.confidence == 0.95  # Maximum unsafe confidence
        assert "bad" in result.flagged_content


class TestStructuredOutputParser:
    """Test structured output parsing."""
    
    def test_planning_output_json_parsing(self):
        """Test parsing planning output from JSON."""
        json_text = '''
        Here's the plan:
        ```json
        {
            "research_plan": "Comprehensive research approach",
            "search_queries": ["query1", "query2"],
            "expected_sources": ["source1", "source2"],
            "success_criteria": "Complete information gathering"
        }
        ```
        '''
        
        result = StructuredOutputParser.parse_planning_output(json_text)
        assert result.research_plan == "Comprehensive research approach"
        assert result.search_queries == ["query1", "query2"]
        assert result.expected_sources == ["source1", "source2"]
        assert result.success_criteria == "Complete information gathering"
    
    def test_planning_output_text_parsing(self):
        """Test parsing planning output from text."""
        text = '''
        Research Plan: This is the research plan
        
        Search Queries:
        - First query
        - Second query
        
        Expected Sources:
        - Academic papers
        - News articles
        
        Success Criteria: Accurate information
        '''
        
        result = StructuredOutputParser.parse_planning_output(text)
        assert "research plan" in result.research_plan.lower()
        assert len(result.search_queries) >= 2
        assert len(result.expected_sources) >= 2
        assert "accurate" in result.success_criteria.lower()
    
    def test_synthesis_output_parsing(self):
        """Test synthesis output parsing."""
        text = "This is a comprehensive research summary with key findings."
        
        result = StructuredOutputParser.parse_synthesis_output(text)
        assert result.research_summary == text
        assert isinstance(result.key_findings, list)
        assert isinstance(result.sources_used, list)
        assert 0.0 <= result.confidence_level <= 1.0
        assert isinstance(result.recommendations, list)
    
    def test_reflexion_output_parsing(self):
        """Test reflexion output parsing."""
        text = "The previous attempt failed. We should retry with a different approach."
        
        result = StructuredOutputParser.parse_reflexion_output(text)
        assert "attempt" in result.critique.lower()
        assert result.should_retry == True  # Contains "retry"
        assert isinstance(result.identified_issues, list)
        assert isinstance(result.improvement_suggestions, list)


class TestConfiguration:
    """Test configuration management."""
    
    def test_config_validation(self):
        """Test configuration validation."""
        # This test depends on actual API keys being set
        # In a real test environment, you'd mock this
        is_valid = Config.validate_config()
        assert isinstance(is_valid, bool)
    
    def test_safe_config(self):
        """Test safe configuration retrieval."""
        safe_config = Config.get_safe_config()
        
        # Should not contain sensitive information
        assert "api_key" not in str(safe_config).lower()
        assert "secret" not in str(safe_config).lower()
        
        # Should contain expected configuration
        assert "model" in safe_config
        assert "temperature" in safe_config
        assert "max_tokens" in safe_config
    
    def test_trusted_domains(self):
        """Test trusted domains configuration."""
        assert isinstance(Config.TRUSTED_DOMAINS, set)
        assert len(Config.TRUSTED_DOMAINS) > 0
        assert "wikipedia.org" in Config.TRUSTED_DOMAINS
        assert "github.com" in Config.TRUSTED_DOMAINS
    
    def test_blocked_keywords(self):
        """Test blocked keywords configuration."""
        assert isinstance(Config.BLOCKED_KEYWORDS, list)
        assert len(Config.BLOCKED_KEYWORDS) > 0
        assert "violence" in Config.BLOCKED_KEYWORDS
        assert "hate" in Config.BLOCKED_KEYWORDS


# Async test runner
def run_async_test(coro):
    """Helper to run async tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


if __name__ == "__main__":
    # Run tests manually if pytest is not available
    print("Running Basic Tests")
    print("=" * 30)
    
    test_classes = [
        TestStateManagement,
        TestSafetyValidation,
        TestStructuredOutputParser,
        TestConfiguration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 20)
        
        instance = test_class()
        methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"PASS: {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"FAIL: {method_name}: {e}")
    
    print(f"\nTest Results: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("All tests passed!")
    else:
        print(f"WARNING: {total_tests - passed_tests} tests failed")