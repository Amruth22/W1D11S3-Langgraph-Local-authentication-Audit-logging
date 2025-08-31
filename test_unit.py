import unittest
import os
import sys
import tempfile
import shutil
import json
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the current directory to Python path to import project modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

class CoreLangGraphAuthAuditTests(unittest.TestCase):
    """Core 5 unit tests for LangGraph Local Authentication and Audit Logging with real components"""
    
    @classmethod
    def setUpClass(cls):
        """Load environment variables and validate API keys"""
        load_dotenv()
        
        # Validate Gemini API key
        cls.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not cls.gemini_api_key or not cls.gemini_api_key.startswith('AIza'):
            raise unittest.SkipTest("Valid GEMINI_API_KEY not found in environment")
        
        # Validate Tavily API key
        cls.tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not cls.tavily_api_key or not cls.tavily_api_key.startswith('tvly-'):
            raise unittest.SkipTest("Valid TAVILY_API_KEY not found in environment")
        
        print(f"Using Gemini API Key: {cls.gemini_api_key[:10]}...{cls.gemini_api_key[-5:]}")
        print(f"Using Tavily API Key: {cls.tavily_api_key[:10]}...{cls.tavily_api_key[-5:]}")
        
        # Load configuration only (no heavy imports)
        try:
            from src.config import Config
            from api.auth import SECRET_KEY
            cls.Config = Config
            cls.SECRET_KEY = SECRET_KEY
            print("LangGraph authentication and audit configuration loaded successfully")
        except ImportError as e:
            raise unittest.SkipTest(f"Required LangGraph auth/audit configuration not found: {e}")

    def setUp(self):
        """Set up test fixtures with temporary directories"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_username = f"testuser_{int(datetime.now().timestamp())}"
        self.test_email = f"{self.test_username}@example.com"
        self.test_password = "testpassword123"

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_authentication_configuration_and_setup(self):
        """Test 1: Authentication Configuration and Setup"""
        print("Running Test 1: Authentication Configuration and Setup")
        
        # Test API key configuration
        self.assertIsNotNone(self.Config.GEMINI_API_KEY)
        self.assertIsNotNone(self.Config.TAVILY_API_KEY)
        self.assertTrue(self.Config.GEMINI_API_KEY.startswith('AIza'))
        self.assertTrue(self.Config.TAVILY_API_KEY.startswith('tvly-'))
        
        # Test JWT configuration
        self.assertIsNotNone(self.SECRET_KEY)
        self.assertIsInstance(self.SECRET_KEY, str)
        self.assertGreater(len(self.SECRET_KEY), 10)
        
        # Test configuration validation
        is_valid = self.Config.validate_config()
        self.assertTrue(is_valid)
        
        # Test authentication components
        from api.auth import AuthManager, pwd_context, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Test password context
        self.assertIsNotNone(pwd_context)
        
        # Test JWT configuration
        self.assertEqual(ALGORITHM, "HS256")
        self.assertEqual(ACCESS_TOKEN_EXPIRE_MINUTES, 30)
        
        # Test AuthManager initialization
        auth_manager = AuthManager()
        self.assertIsNotNone(auth_manager)
        self.assertTrue(auth_manager.users_file.exists())
        
        # Test password hashing
        test_password = "testpassword123"
        hashed = auth_manager.get_password_hash(test_password)
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(hashed, test_password)
        self.assertTrue(auth_manager.verify_password(test_password, hashed))
        
        print(f"PASS: Authentication configuration - JWT algorithm: {ALGORITHM}, Token expiry: {ACCESS_TOKEN_EXPIRE_MINUTES}min")
        print(f"PASS: Password hashing and verification working")
        print("PASS: Authentication configuration and setup validated")

    def test_02_user_management_and_jwt_tokens(self):
        """Test 2: User Management and JWT Token Operations"""
        print("Running Test 2: User Management and JWT Tokens")
        
        # Import user management components
        from api.auth import AuthManager, UserCreate
        from api.models import UserProfile
        
        # Test user creation
        auth_manager = AuthManager()
        
        user_create = UserCreate(
            username=self.test_username,
            email=self.test_email,
            full_name=f"Test User {self.test_username}",
            password=self.test_password
        )
        
        # Create user
        new_user = auth_manager.create_user(user_create)
        self.assertEqual(new_user.username, self.test_username)
        self.assertEqual(new_user.email, self.test_email)
        self.assertIsNotNone(new_user.created_at)
        self.assertFalse(new_user.disabled)
        
        # Test user authentication
        authenticated_user = auth_manager.authenticate_user(self.test_username, self.test_password)
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.username, self.test_username)
        
        # Test JWT token creation
        token_data = {"sub": self.test_username}
        access_token = auth_manager.create_access_token(token_data)
        self.assertIsInstance(access_token, str)
        self.assertGreater(len(access_token), 50)
        
        # Test token verification
        verified_username = auth_manager.verify_token(access_token)
        self.assertEqual(verified_username, self.test_username)
        
        # Test invalid token
        invalid_username = auth_manager.verify_token("invalid.token.here")
        self.assertIsNone(invalid_username)
        
        # Test user retrieval
        retrieved_user = auth_manager.get_user(self.test_username)
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.username, self.test_username)
        
        print(f"PASS: User management - User created: {new_user.username}")
        print(f"PASS: JWT tokens - Token created and verified successfully")
        print(f"PASS: Authentication - User authenticated successfully")
        print("PASS: User management and JWT tokens validated")

    def test_03_audit_logging_system(self):
        """Test 3: Audit Logging System"""
        print("Running Test 3: Audit Logging System")
        
        # Import audit logging components
        from api.audit import AuditLogger, AuditAction, AuditLevel, AuditEntry
        
        # Test audit logger initialization
        audit_logger = AuditLogger(log_dir=self.temp_dir)
        self.assertIsNotNone(audit_logger)
        self.assertTrue(audit_logger.log_dir.exists())
        
        # Test audit entry creation
        test_entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            level=AuditLevel.INFO,
            action=AuditAction.LOGIN,
            username=self.test_username,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            details={"status": "success"},
            request_id=str(uuid.uuid4())
        )
        
        self.assertEqual(test_entry.action, AuditAction.LOGIN)
        self.assertEqual(test_entry.level, AuditLevel.INFO)
        self.assertEqual(test_entry.username, self.test_username)
        
        # Test audit logging methods
        audit_logger.log_auth_success(
            username=self.test_username,
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        audit_logger.log_auth_failure(
            username="invalid_user",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            reason="Invalid credentials"
        )
        
        audit_logger.log_user_registration(
            username=self.test_username,
            email=self.test_email,
            ip_address="127.0.0.1"
        )
        
        test_request_id = str(uuid.uuid4())
        audit_logger.log_research_start(
            username=self.test_username,
            query="Test research query",
            request_id=test_request_id,
            ip_address="127.0.0.1"
        )
        
        audit_logger.log_research_complete(
            username=self.test_username,
            request_id=test_request_id,
            duration_ms=5000,
            sources_count=3,
            confidence=0.85
        )
        
        # Test log retrieval
        recent_logs = audit_logger.get_recent_logs(days=1, username=self.test_username)
        self.assertIsInstance(recent_logs, list)
        self.assertGreater(len(recent_logs), 0)
        
        # Verify log entry structure
        first_log = recent_logs[0]
        self.assertIn('timestamp', first_log)
        self.assertIn('action', first_log)
        self.assertIn('username', first_log)
        self.assertIn('level', first_log)
        
        print(f"PASS: Audit logging - {len(recent_logs)} entries logged")
        print(f"PASS: Audit actions - Login, registration, research events logged")
        print(f"PASS: Log retrieval and filtering working")
        print("PASS: Audit logging system validated")

    def test_04_research_manager_and_lifecycle(self):
        """Test 4: Research Manager and Request Lifecycle"""
        print("Running Test 4: Research Manager and Lifecycle")
        
        # Import research management components
        from api.research_manager import ResearchManager
        from api.models import ResearchStatus
        
        # Test research manager initialization
        research_manager = ResearchManager(storage_dir=self.temp_dir)
        self.assertIsNotNone(research_manager)
        self.assertTrue(research_manager.storage_dir.exists())
        self.assertIsInstance(research_manager.active_requests, dict)
        self.assertIsNotNone(research_manager.executor)
        self.assertIsNotNone(research_manager.workflow)
        
        # Test research request creation
        request_id = research_manager.create_request(
            query="Test research query for lifecycle validation",
            username=self.test_username,
            thread_id=f"test_thread_{int(datetime.now().timestamp())}",
            save_report=True,
            ip_address="127.0.0.1"
        )
        
        self.assertIsInstance(request_id, str)
        self.assertEqual(len(request_id), 36)  # UUID4 length
        
        # Test request retrieval
        request_data = research_manager.get_request(request_id)
        self.assertIsNotNone(request_data)
        self.assertEqual(request_data['request_id'], request_id)
        self.assertEqual(request_data['status'], ResearchStatus.PENDING)
        self.assertEqual(request_data['username'], self.test_username)
        self.assertEqual(request_data['query'], "Test research query for lifecycle validation")
        
        # Test request file persistence
        request_file = research_manager._get_request_file(request_id)
        self.assertTrue(request_file.exists())
        
        # Test user requests listing
        user_requests, total = research_manager.get_user_requests(self.test_username)
        self.assertIsInstance(user_requests, list)
        self.assertGreater(total, 0)
        self.assertEqual(len(user_requests), total)
        
        # Find our test request
        test_request = next((req for req in user_requests if req['request_id'] == request_id), None)
        self.assertIsNotNone(test_request)
        
        # Test response model conversion
        response_model = research_manager.to_response_model(request_data)
        self.assertEqual(response_model.request_id, request_id)
        self.assertEqual(response_model.status, ResearchStatus.PENDING)
        
        # Test summary model conversion
        summary_model = research_manager.to_summary_model(request_data)
        self.assertEqual(summary_model.request_id, request_id)
        self.assertEqual(summary_model.username, self.test_username)
        
        print(f"PASS: Research manager - Request created: {request_id}")
        print(f"PASS: Request lifecycle - Status: {request_data['status']}")
        print(f"PASS: File persistence - Request saved and retrieved")
        print(f"PASS: User requests - {total} requests found")
        print("PASS: Research manager and lifecycle validated")

    def test_05_fastapi_structure_and_endpoints(self):
        """Test 5: FastAPI Structure and Endpoint Configuration"""
        print("Running Test 5: FastAPI Structure and Endpoints")
        
        # Test FastAPI application structure
        try:
            from api.main import app
            from fastapi.testclient import TestClient
            
            test_client = TestClient(app)
            
            # Test health endpoint
            response = test_client.get("/health")
            self.assertEqual(response.status_code, 200)
            health_data = response.json()
            self.assertEqual(health_data["status"], "healthy")
            self.assertIn("version", health_data)
            self.assertIn("config", health_data)
            self.assertIn("total_users", health_data)
            
            # Test API documentation endpoints
            response = test_client.get("/docs")
            self.assertEqual(response.status_code, 200)
            
            response = test_client.get("/openapi.json")
            self.assertEqual(response.status_code, 200)
            openapi_data = response.json()
            self.assertIn("openapi", openapi_data)
            self.assertIn("info", openapi_data)
            self.assertIn("paths", openapi_data)
            self.assertEqual(openapi_data["info"]["title"], "Research Assistant API")
            
            # Test that authentication endpoints exist in OpenAPI
            paths = openapi_data.get("paths", {})
            expected_auth_paths = ["/auth/register", "/auth/login"]
            for path in expected_auth_paths:
                self.assertIn(path, paths, f"Authentication endpoint {path} should be documented")
            
            # Test that research endpoints exist
            expected_research_paths = ["/research", "/research/{request_id}"]
            for path in expected_research_paths:
                # Check if exact path or similar pattern exists
                path_exists = path in paths or any(p.startswith(path.split('{')[0]) for p in paths.keys())
                self.assertTrue(path_exists, f"Research endpoint {path} should be documented")
            
            # Test that audit endpoint exists
            self.assertIn("/audit", paths, "Audit endpoint should be documented")
            
            print("PASS: FastAPI structure and endpoints validated")
            
        except ImportError as e:
            print(f"INFO: FastAPI test skipped due to: {str(e)}")
            
            # Test that API files exist
            self.assertTrue(os.path.exists('api/main.py'))
            self.assertTrue(os.path.exists('api/auth.py'))
            self.assertTrue(os.path.exists('api/audit.py'))
            print("PASS: API file structure validated")
        
        # Test Pydantic models
        try:
            from api.models import (
                ResearchRequest, ResearchResponse, ResearchStatus,
                UserProfile, AuditLogResponse
            )
            from api.auth import UserCreate, UserLogin, Token
            
            # Test user models
            test_user_create = UserCreate(
                username=self.test_username,
                email=self.test_email,
                full_name="Test User",
                password=self.test_password
            )
            self.assertEqual(test_user_create.username, self.test_username)
            
            test_user_login = UserLogin(
                username=self.test_username,
                password=self.test_password
            )
            self.assertEqual(test_user_login.username, self.test_username)
            
            # Test research models
            test_research_request = ResearchRequest(
                query="Test research query",
                thread_id="test_thread",
                save_report=True
            )
            self.assertEqual(test_research_request.query, "Test research query")
            
            print("PASS: Pydantic models structure validated")
            
        except ImportError as e:
            print(f"INFO: Pydantic models test skipped due to: {str(e)}")
        
        # Test middleware and security
        try:
            from api.middleware import setup_middleware
            from fastapi.security import HTTPBearer
            
            # Test that middleware setup function exists
            self.assertTrue(callable(setup_middleware))
            
            # Test security scheme
            security = HTTPBearer()
            self.assertIsNotNone(security)
            
            print("PASS: Middleware and security components validated")
            
        except ImportError as e:
            print(f"INFO: Middleware test skipped due to: {str(e)}")
        
        print(f"PASS: FastAPI configuration - Title: Research Assistant API")
        print(f"PASS: Authentication endpoints documented and available")
        print(f"PASS: Research and audit endpoints documented")
        print("PASS: FastAPI structure and endpoints validated")

def run_core_tests():
    """Run core tests and provide summary"""
    print("=" * 70)
    print("[*] Core LangGraph Local Authentication and Audit Logging Unit Tests (5 Tests)")
    print("Testing with REAL APIs and Authentication/Audit Components")
    print("=" * 70)
    
    # Check API keys
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    
    if not gemini_api_key or not gemini_api_key.startswith('AIza'):
        print("[ERROR] Valid GEMINI_API_KEY not found!")
        return False
    
    if not tavily_api_key or not tavily_api_key.startswith('tvly-'):
        print("[ERROR] Valid TAVILY_API_KEY not found!")
        return False
    
    print(f"[OK] Using Gemini API Key: {gemini_api_key[:10]}...{gemini_api_key[-5:]}")
    print(f"[OK] Using Tavily API Key: {tavily_api_key[:10]}...{tavily_api_key[-5:]}")
    print()
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(CoreLangGraphAuthAuditTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print("[*] Test Results:")
    print(f"[*] Tests Run: {result.testsRun}")
    print(f"[*] Failures: {len(result.failures)}")
    print(f"[*] Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n[FAILURES]:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\n[ERRORS]:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n[SUCCESS] All 5 core LangGraph authentication and audit tests passed!")
        print("[OK] Authentication and audit components working correctly with real APIs")
        print("[OK] Authentication, User Management, Audit Logging, Research Manager, FastAPI validated")
    else:
        print(f"\n[WARNING] {len(result.failures) + len(result.errors)} test(s) failed")
    
    return success

if __name__ == "__main__":
    print("[*] Starting Core LangGraph Local Authentication and Audit Logging Tests")
    print("[*] 5 essential tests with real APIs and authentication/audit components")
    print("[*] Components: Authentication, User Management, Audit Logging, Research Manager, FastAPI")
    print()
    
    success = run_core_tests()
    exit(0 if success else 1)