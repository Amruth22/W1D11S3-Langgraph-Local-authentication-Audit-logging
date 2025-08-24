#!/bin/bash
# Curl examples for testing the Research Assistant API

API_URL="http://127.0.0.1:8000"
USERNAME="testuser_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="testpassword123"

echo "Research Assistant API - Curl Examples"
echo "======================================"

# 1. Health Check
echo -e "\n1. Health Check"
echo "curl -X GET $API_URL/health"
curl -X GET "$API_URL/health" | jq '.'

# 2. User Registration
echo -e "\n2. User Registration"
echo "curl -X POST $API_URL/auth/register"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"email\": \"$EMAIL\",
    \"full_name\": \"Test User\",
    \"password\": \"$PASSWORD\"
  }")

echo "$REGISTER_RESPONSE" | jq '.'

# 3. User Login
echo -e "\n3. User Login"
echo "curl -X POST $API_URL/auth/login"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"password\": \"$PASSWORD\"
  }")

echo "$LOGIN_RESPONSE" | jq '.'

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to get access token"
    exit 1
fi

echo "Access Token: $TOKEN"

# 4. Get User Profile
echo -e "\n4. Get User Profile"
echo "curl -X GET $API_URL/profile -H \"Authorization: Bearer \$TOKEN\""
curl -s -X GET "$API_URL/profile" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 5. Create Research Request
echo -e "\n5. Create Research Request"
echo "curl -X POST $API_URL/research -H \"Authorization: Bearer \$TOKEN\""
RESEARCH_RESPONSE=$(curl -s -X POST "$API_URL/research" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "What are the latest developments in artificial intelligence?",
    "save_report": true
  }')

echo "$RESEARCH_RESPONSE" | jq '.'

# Extract request ID
REQUEST_ID=$(echo "$RESEARCH_RESPONSE" | jq -r '.request_id')

if [ "$REQUEST_ID" = "null" ] || [ -z "$REQUEST_ID" ]; then
    echo "ERROR: Failed to get request ID"
    exit 1
fi

echo "Request ID: $REQUEST_ID"

# 6. Check Research Status
echo -e "\n6. Check Research Status"
echo "curl -X GET $API_URL/research/$REQUEST_ID -H \"Authorization: Bearer \$TOKEN\""

# Check status multiple times
for i in {1..5}; do
    echo -e "\nCheck $i:"
    STATUS_RESPONSE=$(curl -s -X GET "$API_URL/research/$REQUEST_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
    echo "Status: $STATUS"
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        echo "Final result:"
        echo "$STATUS_RESPONSE" | jq '.'
        break
    fi
    
    echo "Waiting 10 seconds..."
    sleep 10
done

# 7. List Research Requests
echo -e "\n7. List Research Requests"
echo "curl -X GET $API_URL/research -H \"Authorization: Bearer \$TOKEN\""
curl -s -X GET "$API_URL/research?page=1&per_page=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 8. Get Audit Logs
echo -e "\n8. Get Audit Logs"
echo "curl -X GET $API_URL/audit -H \"Authorization: Bearer \$TOKEN\""
curl -s -X GET "$API_URL/audit?page=1&per_page=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 9. Test Authentication Error
echo -e "\n9. Test Authentication Error"
echo "curl -X GET $API_URL/profile (without token)"
curl -s -X GET "$API_URL/profile" | jq '.'

# 10. Test Invalid Token
echo -e "\n10. Test Invalid Token"
echo "curl -X GET $API_URL/profile -H \"Authorization: Bearer invalid_token\""
curl -s -X GET "$API_URL/profile" \
  -H "Authorization: Bearer invalid_token" | jq '.'

echo -e "\n======================================"
echo "Curl examples completed!"
echo "Username: $USERNAME"
echo "Token: $TOKEN"
echo "Request ID: $REQUEST_ID"