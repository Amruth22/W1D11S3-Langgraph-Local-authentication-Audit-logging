# Research Assistant API Documentation

FastAPI-based REST API for the Research Assistant Agent with local authentication and audit logging.

## Features

- **FastAPI Integration**: Modern, fast web API with automatic OpenAPI documentation
- **Local Authentication**: File-based user management with JWT tokens
- **Audit Logging**: Comprehensive logging of all user actions and API calls
- **Background Research**: Asynchronous research execution with status tracking
- **Report Generation**: Automatic markdown report saving
- **Request Management**: Full lifecycle management of research requests

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The API keys are already configured in the `.env` file. For production, update the JWT secret:

```bash
# For production deployment
cp .env.example .env
# Edit .env with your API keys and a strong JWT secret
```

**Important**: Change the `JWT_SECRET_KEY` for production use!

### 3. Start the API Server

```bash
# Development server with auto-reload
python run_api.py --reload

# Production server
python run_api.py --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Access API Documentation

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### Authentication

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Research

#### Create Research Request
```http
POST /research
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What are the latest developments in quantum computing?",
  "thread_id": "optional_thread_id",
  "save_report": true
}
```

**Response:**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "query": "What are the latest developments in quantum computing?",
  "created_at": "2024-01-15T10:30:00",
  "username": "johndoe"
}
```

#### Get Research Status
```http
GET /research/{request_id}
Authorization: Bearer <token>
```

**Response (Completed):**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "query": "What are the latest developments in quantum computing?",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:32:15",
  "username": "johndoe",
  "draft": "# Research Summary: Quantum Computing...",
  "sources_count": 8,
  "confidence": 0.92,
  "retry_count": 0,
  "is_safe": true,
  "report_file": "20240115_103000_quantum_computing.md"
}
```

#### List Research Requests
```http
GET /research?page=1&per_page=20
Authorization: Bearer <token>
```

### User Profile

#### Get Profile
```http
GET /profile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2024-01-15T09:00:00",
  "last_login": "2024-01-15T10:25:00",
  "total_research_requests": 15,
  "successful_requests": 12,
  "failed_requests": 3
}
```

### System

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "active_requests": 2,
  "total_requests": 150,
  "total_users": 5,
  "config": {
    "model": "gemini-2.0-flash-exp",
    "temperature": 0.1,
    "max_tokens": 1000
  }
}
```

#### Audit Logs
```http
GET /audit?page=1&per_page=20&days=7
Authorization: Bearer <token>
```

## Research Status Flow

```
pending → running → completed
                 ↘ failed
```

- **pending**: Request created, waiting to start
- **running**: Research in progress
- **completed**: Research finished successfully
- **failed**: Research failed with errors

## Authentication Flow

1. **Register**: Create new user account
2. **Login**: Get JWT access token (30-minute expiry)
3. **Use Token**: Include in Authorization header for protected endpoints
4. **Token Refresh**: Login again when token expires

## File Structure

```
data/
├── users.json          # User accounts
├── research/           # Research request data
│   ├── {request_id}.json
│   └── ...
└── audit/              # Audit logs
    ├── audit_20240115.log
    └── ...

reports/                # Generated markdown reports
├── 20240115_103000_quantum_computing.md
└── ...
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "error": "Authentication Error",
  "detail": "Could not validate credentials",
  "timestamp": "2024-01-15T10:30:00",
  "request_id": "req_123456"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## Security Features

### Local Authentication
- File-based user storage (`data/users.json`)
- Bcrypt password hashing
- JWT tokens with expiration
- Protected route middleware

### Audit Logging
- All API calls logged with user context
- Authentication events tracked
- Research lifecycle events recorded
- Structured JSON log format
- Daily log file rotation

### Request Tracking
- Unique request IDs for tracing
- Request duration monitoring
- Active request counting
- Rate limiting ready

## Testing

### Python Client
```bash
python api_examples/test_api.py
```

### Curl Examples
```bash
chmod +x api_examples/curl_examples.sh
./api_examples/curl_examples.sh
```

### Manual Testing
1. Start API server: `python run_api.py --reload`
2. Open browser: http://127.0.0.1:8000/docs
3. Use Swagger UI for interactive testing

## Configuration

### Environment Variables
```bash
# API Keys (required)
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key

# Authentication & Security (important for production)
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_WORKERS=1
API_LOG_LEVEL=info

# Storage Configuration
USERS_FILE=data/users.json
RESEARCH_STORAGE_DIR=data/research
AUDIT_LOG_DIR=data/audit

# LLM Configuration
TEMPERATURE=0.1
MAX_OUTPUT_TOKENS=1000
MAX_RETRIES=3
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### Server Options
```bash
python run_api.py --help

Options:
  --host TEXT          Host to bind to (default: 127.0.0.1)
  --port INTEGER       Port to bind to (default: 8000)
  --reload             Enable auto-reload for development
  --workers INTEGER    Number of worker processes (default: 1)
  --log-level TEXT     Log level (default: info)
```

## Production Deployment

### Using Uvicorn
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Gunicorn
```bash
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Monitoring

### Health Endpoint
Monitor API health at `/health` endpoint:
- Server status
- Uptime tracking
- Request statistics
- Configuration info

### Audit Logs
Monitor user activity via audit logs:
- Authentication events
- Research requests
- API access patterns
- Error tracking

### Log Files
```bash
# View recent audit logs
tail -f data/audit/audit_$(date +%Y%m%d).log

# Parse JSON logs
cat data/audit/audit_$(date +%Y%m%d).log | jq '.action' | sort | uniq -c
```

## Troubleshooting

### Common Issues

1. **Configuration Errors**
   ```bash
   python run_api.py  # Check config validation
   ```

2. **Authentication Issues**
   ```bash
   # Check users file
   cat data/users.json | jq '.'
   ```

3. **Research Failures**
   ```bash
   # Check research request files
   ls data/research/
   cat data/research/{request_id}.json | jq '.'
   ```

4. **Permission Errors**
   ```bash
   # Ensure data directory is writable
   mkdir -p data/users data/research data/audit
   chmod 755 data/
   ```

### Debug Mode
```bash
python run_api.py --reload --log-level debug
```

## API Client Libraries

### Python
```python
import requests

class ResearchAPIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        response = requests.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        self.token = response.json()["access_token"]
    
    def create_research(self, query):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(f"{self.base_url}/research", 
                               json={"query": query}, headers=headers)
        return response.json()
```

### JavaScript/Node.js
```javascript
class ResearchAPIClient {
    constructor(baseUrl = 'http://127.0.0.1:8000') {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await response.json();
        this.token = data.access_token;
    }
    
    async createResearch(query) {
        const response = await fetch(`${this.baseUrl}/research`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({query})
        });
        return response.json();
    }
}
```

---

**API Version**: 1.0.0  
**Built with FastAPI, JWT Authentication, and File-based Storage**