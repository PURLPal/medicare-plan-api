# CORS AllowOrigins: ["*"] - Is It Safe?

## TL;DR

**For this Medicare API: Yes, it's fine.**

## Why `AllowOrigins: ["*"]` Is OK Here

### 1. Public Data
All Medicare plan data is **public information**:
- Available on Medicare.gov
- No authentication needed
- No personal user data
- No proprietary information

**Analogy**: It's like a weather API - the data is public, so anyone can access it.

### 2. Read-Only API
All endpoints are **GET requests only**:
- No data modification
- No user accounts
- No state changes
- No sensitive operations

### 3. No Authentication
There's no auth token or API key:
- Can't be stolen via CORS
- No session cookies
- No user-specific data

### 4. Chrome Extension Use Case
Chrome extensions have random origins like:
- `chrome-extension://abcdefghijklmnop1234567890`
- `chrome-extension://xyz987654321fedcba`

You'd need to whitelist **every** extension that wants to use your API. With `*`, any extension can use it.

## When You SHOULD Restrict Origins

Use specific origins when:

### ❌ 1. Authentication/Authorization
```json
// BAD with AllowOrigins: ["*"]
POST /api/login
Authorization: Bearer secret-token

// User data could be exposed via CORS
```

### ❌ 2. User-Specific Data
```json
// BAD with AllowOrigins: ["*"]
GET /api/user/profile
// Returns personal info based on session cookie
```

### ❌ 3. Mutations
```json
// BAD with AllowOrigins: ["*"]
POST /api/plans/delete
DELETE /api/data/123
```

### ❌ 4. API Keys/Rate Limiting
```json
// BAD with AllowOrigins: ["*"]
GET /api/data
X-API-Key: secret-key-123
// Anyone can call and use up your quota
```

## Alternative: Restricted Origins

If you want to lock it down later:

### Option 1: Specific Domains
```json
{
  "AllowOrigins": [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://staging.yourdomain.com"
  ]
}
```

**Pros:**
- More secure
- Know who's using your API

**Cons:**
- Doesn't work with Chrome Extensions (unknown extension IDs)
- Need to update list for every new user

### Option 2: Specific Extension ID
```json
{
  "AllowOrigins": [
    "chrome-extension://abcdefghijklmnop1234567890"
  ]
}
```

**Pros:**
- Only your specific extension can access

**Cons:**
- Need to know extension ID in advance
- Different in dev vs production
- Firefox uses different format (`moz-extension://`)
- Can't share API with other extensions

### Option 3: Pattern Matching (NOT SUPPORTED by AWS Lambda)
AWS Lambda Function URLs **don't support** wildcard patterns like:
```json
// ❌ NOT SUPPORTED
{
  "AllowOrigins": [
    "https://*.yourdomain.com",
    "chrome-extension://*"
  ]
}
```

It's either:
- Specific origins: `["https://example.com"]`
- All origins: `["*"]`

## Our Recommendation

### For Medicare Plan API:

**Keep `AllowOrigins: ["*"]`** because:
1. ✅ Public data (Medicare plans)
2. ✅ Read-only (GET requests)
3. ✅ No auth tokens
4. ✅ Need to support unknown Chrome Extensions
5. ✅ No rate limiting/quotas to protect

### If You Add These Features:

**Switch to specific origins** if you add:
- User accounts / authentication
- Personal data / user-specific responses
- Write operations (POST/PUT/DELETE)
- API keys / rate limiting
- Paid tiers / usage quotas

## Alternative Security Measures

If you're worried but still need `*`, you can add:

### 1. Rate Limiting (API Gateway)
```bash
# Add API Gateway in front of Lambda
# Set rate limit: 100 requests/minute per IP
```

### 2. IP Allowlist (if known users)
```python
# In Lambda function
ALLOWED_IPS = ['1.2.3.4', '5.6.7.8']

def lambda_handler(event, context):
    client_ip = event['requestContext']['http']['sourceIp']
    if client_ip not in ALLOWED_IPS:
        return {'statusCode': 403, 'body': 'Forbidden'}
```

### 3. Simple API Key (optional)
```python
# Check for API key in query param or header
def lambda_handler(event, context):
    api_key = event.get('queryStringParameters', {}).get('api_key')
    if api_key != 'your-simple-key':
        return {'statusCode': 403, 'body': 'Invalid API key'}
```

**Note**: This doesn't protect against CORS, but prevents automated scraping.

## Current CORS Config

File: `cors-config.json`

```json
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["*"],
  "AllowHeaders": ["Content-Type", "Authorization", "X-Requested-With"],
  "MaxAge": 300
}
```

**To change to specific origins:**

1. Edit `cors-config.json`:
   ```json
   {
     "AllowOrigins": [
       "https://yourdomain.com",
       "chrome-extension://your-extension-id"
     ],
     "AllowMethods": ["GET", "OPTIONS"],
     "AllowHeaders": ["Content-Type"],
     "MaxAge": 300
   }
   ```

2. Redeploy:
   ```bash
   ./deploy_lambda.sh
   ```

## Summary

**For public, read-only Medicare data API:**
- ✅ `AllowOrigins: ["*"]` is **safe and appropriate**
- ✅ Enables any Chrome Extension to use it
- ✅ No security risks (public data, no auth, read-only)

**For APIs with auth, user data, or mutations:**
- ❌ `AllowOrigins: ["*"]` is **dangerous**
- ✅ Use specific origins
- ✅ Add authentication
- ✅ Implement rate limiting

---

**Current status:** Safe to use `*` for this project. Change it if requirements evolve!
