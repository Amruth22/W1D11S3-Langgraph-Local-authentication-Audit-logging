# 🔧 Configuration Guide - Research Assistant API with Authentication

This guide explains how to configure the Research Assistant API with local authentication and audit logging.

## 📋 Environment Variables

The application uses environment variables for secure configuration management across all components.

### 🔑 Required Configuration

#### **API Keys (Required)**
```bash
# Gemini API Key for LLM functionality
GEMINI_API_KEY=AIzaSyCeQeHPZYUl2iZVMfNCs1hC3FeO23pkRag

# Tavily API Key for web search
TAVILY_API_KEY=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
```

#### **JWT Security (Critical for Production)**
```bash
# JWT Secret Key - MUST be changed for production
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**⚠️ Security Warning**: The default JWT secret is for development only. **Always change it for production!**

### 🌐 API Server Configuration

```bash
# Server binding
API_HOST=127.0.0.1          # Use 0.0.0.0 for external access
API_PORT=8000               # API server port
API_WORKERS=1               # Number of worker processes
API_LOG_LEVEL=info          # Logging level
```

### 📁 Storage Configuration

```bash
# File-based storage paths
USERS_FILE=data/users.json                    # User accounts
RESEARCH_STORAGE_DIR=data/research            # Research requests
AUDIT_LOG_DIR=data/audit                      # Audit logs
REPORTS_DIR=reports                           # Generated reports
CHECKPOINTS_DIR=checkpoints                   # LangGraph checkpoints
```

### 🧠 LLM Configuration

```bash
# Gemini 2.0 Flash settings
TEMPERATURE=0.1                               # Response randomness (0.0-1.0)
MAX_OUTPUT_TOKENS=1000                        # Maximum response length
MAX_RETRIES=3                                 # Retry attempts for failures

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60            # API rate limit
```

## 🚀 Setup Instructions

### 🔧 Development Setup

1. **Clone and install**:
   ```bash
   git clone [repository]
   cd W1D11S3-Langgraph-Local-authentication-Audit-logging
   pip install -r requirements.txt
   ```

2. **Configuration is ready**:
   ```bash
   # API keys are pre-configured in .env file
   # Start the API immediately
   python run_api.py --reload
   ```

3. **Access the API**:
   - **API Server**: http://127.0.0.1:8000
   - **Interactive Docs**: http://127.0.0.1:8000/docs
   - **Health Check**: http://127.0.0.1:8000/health

### 🏭 Production Setup

1. **Create production configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with production values**:
   ```bash
   # Critical: Change JWT secret key
   JWT_SECRET_KEY=your-production-jwt-secret-min-32-characters-long
   
   # Use your own API keys
   GEMINI_API_KEY=your-production-gemini-key
   TAVILY_API_KEY=your-production-tavily-key
   
   # Production server settings
   API_HOST=0.0.0.0
   API_PORT=8000
   API_WORKERS=4
   API_LOG_LEVEL=warning
   ```

3. **Start production server**:
   ```bash
   python run_api.py --host 0.0.0.0 --port 8000 --workers 4
   ```

## 🔒 Security Configuration

### 🔐 JWT Token Security

#### **Development (Current)**
```bash
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### **Production (Recommended)**
```bash
# Generate a strong secret key
JWT_SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=15  # Shorter expiry for production
```

### 🛡️ API Security

#### **CORS Configuration**
```python
# In api/middleware.py - configure for production
allow_origins=["https://yourdomain.com"]  # Specific domains only
allow_credentials=True
```

#### **Rate Limiting**
```bash
# Adjust based on your needs
RATE_LIMIT_REQUESTS_PER_MINUTE=30  # Lower for production
```

## 📊 Storage Configuration

### 📁 File-based Storage (Current)

```bash
# Directory structure created automatically
data/
├── users.json              # User accounts with hashed passwords
├── research/               # Research request data
│   ├── {request_id}.json
│   └── ...
└── audit/                  # Daily audit logs
    ├── audit_20240115.log
    └── ...

reports/                    # Generated markdown reports
checkpoints/               # LangGraph state persistence
```

### 🗄️ Database Migration (Future)

For production scale, consider migrating to:

```bash
# PostgreSQL configuration (future enhancement)
DATABASE_URL=postgresql://user:password@localhost:5432/research_db

# MongoDB configuration (alternative)
MONGODB_URL=mongodb://localhost:27017/research_db
```

## 🧪 Configuration Testing

### **Test Configuration Loading**
```bash
# Test that .env file is loaded correctly
python -c "
from src.config import Config
from api.auth import SECRET_KEY
print(f'Gemini API: {\"✅\" if Config.GEMINI_API_KEY else \"❌\"}')
print(f'Tavily API: {\"✅\" if Config.TAVILY_API_KEY else \"❌\"}')
print(f'JWT Secret: {\"✅\" if SECRET_KEY else \"❌\"}')
print(f'Config Valid: {\"✅\" if Config.validate_config() else \"❌\"}')
"
```

### **Test API Server**
```bash
# Start server
python run_api.py --reload

# Test health endpoint
curl http://127.0.0.1:8000/health

# Expected response should show healthy status
```

### **Test Authentication**
```bash
# Test user registration and login
python api_examples/test_api.py

# Or use curl examples
chmod +x api_examples/curl_examples.sh
./api_examples/curl_examples.sh
```

## 🚨 Troubleshooting

### **Common Configuration Issues**

#### **1. API Keys Not Loading**
```bash
# Check if .env file exists
ls -la .env

# Test environment loading
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Gemini: {bool(os.getenv(\"GEMINI_API_KEY\"))}')
print(f'Tavily: {bool(os.getenv(\"TAVILY_API_KEY\"))}')
"
```

#### **2. JWT Secret Key Warning**
```bash
WARNING: Using default JWT secret key. Set JWT_SECRET_KEY in .env file for production.
```

**Solution**: Update `.env` file:
```bash
JWT_SECRET_KEY=your-production-secret-key-min-32-characters
```

#### **3. Storage Permission Errors**
```bash
# Ensure directories are writable
mkdir -p data/users data/research data/audit reports checkpoints
chmod 755 data/ reports/ checkpoints/
```

#### **4. Port Already in Use**
```bash
# Change port in .env file
API_PORT=8001

# Or use command line
python run_api.py --port 8001
```

### **Configuration Validation**

#### **Startup Validation**
The application validates configuration on startup:

```python
# Validates API keys, JWT secret, and storage paths
if not Config.validate_config():
    print("ERROR: Configuration validation failed!")
    sys.exit(1)
```

#### **Health Check Validation**
```bash
curl http://127.0.0.1:8000/health
```

Expected response includes configuration status:
```json
{
  "status": "healthy",
  "config": {
    "model": "gemini-2.0-flash-exp",
    "temperature": 0.1,
    "max_tokens": 1000
  }
}
```

## 🔄 Configuration Updates

### **Runtime Configuration**
Some settings can be overridden at runtime:

```bash
# Override server settings
python run_api.py --host 0.0.0.0 --port 8080 --workers 2 --log-level debug

# Override via environment
API_HOST=0.0.0.0 API_PORT=8080 python run_api.py
```

### **Adding New Configuration**
1. Add to `.env` and `.env.example` files
2. Update relevant module to load the variable
3. Add validation if needed
4. Update documentation

## 🌐 Deployment Configurations

### **Docker Configuration**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Environment variables can be set via docker-compose
ENV GEMINI_API_KEY=""
ENV TAVILY_API_KEY=""
ENV JWT_SECRET_KEY=""

EXPOSE 8000
CMD ["python", "run_api.py", "--host", "0.0.0.0", "--port", "8000"]
```

### **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'
services:
  research-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - API_HOST=0.0.0.0
      - API_WORKERS=4
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./reports:/app/reports
```

### **Cloud Deployment**
```bash
# AWS/GCP/Azure - set environment variables in platform
export GEMINI_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export JWT_SECRET_KEY="your-secret"
export API_HOST="0.0.0.0"
export API_WORKERS="4"
```

## 📈 Production Best Practices

### **Security Checklist**
- ✅ Change JWT secret key from default
- ✅ Use strong, unique API keys for production
- ✅ Set appropriate token expiry times
- ✅ Configure CORS for specific domains
- ✅ Use HTTPS in production
- ✅ Implement rate limiting
- ✅ Monitor audit logs regularly

### **Performance Optimization**
- ✅ Increase API workers for high load
- ✅ Adjust rate limits based on API quotas
- ✅ Monitor and tune LLM parameters
- ✅ Implement caching for frequent requests
- ✅ Use database instead of file storage

### **Monitoring & Maintenance**
- ✅ Monitor health endpoint regularly
- ✅ Review audit logs for security issues
- ✅ Track API usage and performance
- ✅ Backup user data and research requests
- ✅ Rotate API keys periodically

---

## 🎯 Quick Reference

### **Immediate Use (Development)**
```bash
git clone [repository]
pip install -r requirements.txt
python run_api.py --reload
# Access: http://127.0.0.1:8000/docs
```

### **Production Deployment**
```bash
cp .env.example .env
# Edit .env with production values
python run_api.py --host 0.0.0.0 --workers 4
```

### **Configuration Validation**
```bash
python -c "from src.config import Config; print('✅ Valid' if Config.validate_config() else '❌ Invalid')"
```

**The Research Assistant API is now ready for secure, production-grade deployment!** 🚀