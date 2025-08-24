#!/usr/bin/env python3
"""
API testing examples for the Research Assistant API.
"""

import requests
import json
import time
from typing import Optional


class APIClient:
    """Simple API client for testing."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session = requests.Session()
    
    def _headers(self) -> dict:
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def register(self, username: str, email: str, full_name: str, password: str) -> dict:
        """Register a new user."""
        data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": password
        }
        
        response = self.session.post(
            f"{self.base_url}/auth/register",
            json=data,
            headers=self._headers()
        )
        
        if response.status_code == 200:
            print(f"User {username} registered successfully")
        else:
            print(f"Registration failed: {response.text}")
        
        return response.json()
    
    def login(self, username: str, password: str) -> dict:
        """Login and get access token."""
        data = {
            "username": username,
            "password": password
        }
        
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json=data,
            headers=self._headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            self.token = result["access_token"]
            print(f"Login successful. Token expires in {result['expires_in']} seconds")
            return result
        else:
            print(f"Login failed: {response.text}")
            return response.json()
    
    def health_check(self) -> dict:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def create_research(self, query: str, thread_id: Optional[str] = None, save_report: bool = True) -> dict:
        """Create a research request."""
        data = {
            "query": query,
            "thread_id": thread_id,
            "save_report": save_report
        }
        
        response = self.session.post(
            f"{self.base_url}/research",
            json=data,
            headers=self._headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Research request created: {result['request_id']}")
            return result
        else:
            print(f"Research creation failed: {response.text}")
            return response.json()
    
    def get_research(self, request_id: str) -> dict:
        """Get research request details."""
        response = self.session.get(
            f"{self.base_url}/research/{request_id}",
            headers=self._headers()
        )
        
        return response.json()
    
    def list_research(self, page: int = 1, per_page: int = 20) -> dict:
        """List research requests."""
        params = {"page": page, "per_page": per_page}
        
        response = self.session.get(
            f"{self.base_url}/research",
            params=params,
            headers=self._headers()
        )
        
        return response.json()
    
    def get_profile(self) -> dict:
        """Get user profile."""
        response = self.session.get(
            f"{self.base_url}/profile",
            headers=self._headers()
        )
        
        return response.json()
    
    def get_audit_logs(self, page: int = 1, per_page: int = 20, days: int = 7) -> dict:
        """Get audit logs."""
        params = {"page": page, "per_page": per_page, "days": days}
        
        response = self.session.get(
            f"{self.base_url}/audit",
            params=params,
            headers=self._headers()
        )
        
        return response.json()


def test_complete_workflow():
    """Test complete API workflow."""
    print("Testing Research Assistant API")
    print("=" * 50)
    
    client = APIClient()
    
    # Test health check
    print("\\n1. Health Check")
    health = client.health_check()
    print(f"API Status: {health['status']}")
    print(f"Version: {health['version']}")
    print(f"Total Users: {health['total_users']}")
    
    # Test user registration
    print("\\n2. User Registration")
    username = f"testuser_{int(time.time())}"
    email = f"{username}@example.com"
    
    try:
        client.register(
            username=username,
            email=email,
            full_name="Test User",
            password="testpassword123"
        )
    except Exception as e:
        print(f"Registration error: {e}")
    
    # Test login
    print("\\n3. User Login")
    try:
        client.login(username, "testpassword123")
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    # Test profile
    print("\\n4. User Profile")
    profile = client.get_profile()
    print(f"Username: {profile['username']}")
    print(f"Email: {profile['email']}")
    print(f"Total Requests: {profile['total_research_requests']}")
    
    # Test research creation
    print("\\n5. Create Research Request")
    research_query = "What are the latest developments in quantum computing?"
    research = client.create_research(research_query)
    request_id = research["request_id"]
    
    print(f"Request ID: {request_id}")
    print(f"Status: {research['status']}")
    print(f"Query: {research['query']}")
    
    # Wait and check research progress
    print("\\n6. Monitor Research Progress")
    for i in range(10):  # Check for up to 10 times
        time.sleep(5)  # Wait 5 seconds
        
        status = client.get_research(request_id)
        print(f"Check {i+1}: Status = {status['status']}")
        
        if status['status'] in ['completed', 'failed']:
            break
    
    # Get final results
    print("\\n7. Final Results")
    final_result = client.get_research(request_id)
    print(f"Final Status: {final_result['status']}")
    
    if final_result['status'] == 'completed':
        print(f"Sources Count: {final_result['sources_count']}")
        print(f"Confidence: {final_result['confidence']}")
        print(f"Report File: {final_result['report_file']}")
        print(f"Draft Preview: {final_result['draft'][:200]}...")
    elif final_result['status'] == 'failed':
        print(f"Error: {final_result['error_message']}")
    
    # Test research listing
    print("\\n8. List Research Requests")
    research_list = client.list_research()
    print(f"Total Requests: {research_list['total']}")
    for item in research_list['items'][:3]:  # Show first 3
        print(f"  - {item['request_id']}: {item['status']} - {item['query'][:50]}...")
    
    # Test audit logs
    print("\\n9. Audit Logs")
    audit_logs = client.get_audit_logs(per_page=5)
    print(f"Total Audit Entries: {audit_logs['total']}")
    for entry in audit_logs['entries'][:3]:  # Show first 3
        print(f"  - {entry['timestamp']}: {entry['action']} by {entry['username']}")
    
    print("\\n" + "=" * 50)
    print("API Testing Complete!")


def test_authentication_errors():
    """Test authentication error handling."""
    print("\\nTesting Authentication Errors")
    print("-" * 30)
    
    client = APIClient()
    
    # Test invalid login
    print("1. Invalid Login")
    result = client.login("nonexistent", "wrongpassword")
    print(f"Expected error: {result}")
    
    # Test accessing protected endpoint without token
    print("\\n2. Access Without Token")
    try:
        profile = client.get_profile()
        print(f"Unexpected success: {profile}")
    except Exception as e:
        print(f"Expected error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Research Assistant API")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--test-auth", action="store_true", help="Test authentication errors")
    
    args = parser.parse_args()
    
    if args.test_auth:
        test_authentication_errors()
    else:
        test_complete_workflow()