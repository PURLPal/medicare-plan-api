# CORS Configuration for Chrome Extensions - The Right Way

## TL;DR

**✅ DO:** Configure CORS at the AWS Lambda Function URL level
**❌ DON'T:** Add CORS headers in your Lambda code (causes duplicate headers)

## How We Configured CORS

### 1. Lambda Function URL CORS Config (AWS Level)

Our `deploy_lambda.sh` creates a CORS config file and applies it:

```bash
# CORS configuration file
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["*"],
  "AllowHeaders": ["Content-Type", "Authorization", "X-Requested-With"],
  "MaxAge": 300
}

# Applied when creating Function URL
aws lambda create-function-url-config \
  --function-name medicare-plan-api \
  --auth-type NONE \
  --cors file://cors-config.json
```

**Key settings:**
- `AllowOrigins: ["*"]` - Allows **ALL origins** including `chrome-extension://`
- `AllowMethods: ["*"]` - Allows GET, POST, OPTIONS, etc.
- `AllowHeaders: [...]` - Headers Chrome Extensions need
- `MaxAge: 300` - Caches preflight for 5 minutes

### 2. Lambda Code (NO Manual CORS Headers!)

Our `lambda_function.py` **ONLY** sets `Content-Type`:

```python
# ✅ CORRECT - Only Content-Type, no CORS headers
headers = {
    'Content-Type': 'application/json'
}

# Handle OPTIONS for CORS preflight
if http_method == 'OPTIONS':
    return {
        'statusCode': 200,
        'headers': headers,  # Just Content-Type
        'body': ''
    }

# All other responses
response['headers'] = headers  # Just Content-Type
return response
```

AWS Lambda Function URL **automatically adds** these headers:
- `Access-Control-Allow-Origin: *` (or matching origin)
- `Access-Control-Allow-Methods: *`
- `Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With`
- `Vary: Origin`

## Why This Matters for Chrome Extensions

### The Problem with Manual CORS Headers

If you add CORS headers in your Lambda code:

```python
# ❌ WRONG - Don't do this!
headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}
```

You'll get **duplicate headers**:
1. One from your code: `Access-Control-Allow-Origin: *`
2. One from Lambda Function URL: `Access-Control-Allow-Origin: *`

Browsers **reject** responses with duplicate CORS headers, causing:
```
Access to fetch at 'https://...' from origin 'chrome-extension://...'
has been blocked by CORS policy: The 'Access-Control-Allow-Origin'
header contains multiple values '*, *', but only one is allowed.
```

### The Correct Way (What We Do)

1. **Lambda Function URL adds CORS headers automatically**
2. **Your code only sets Content-Type**
3. **No duplicates, Chrome Extensions work perfectly**

## Testing CORS

### Test 1: Preflight Request (OPTIONS)

```bash
curl -X OPTIONS https://your-url.lambda-url.us-east-1.on.aws/nh/03462 \
  -H "Origin: chrome-extension://abcdefghijklmnop" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i
```

**Should see:**
```
HTTP/2 200
access-control-allow-origin: chrome-extension://abcdefghijklmnop
access-control-allow-methods: *
access-control-allow-headers: Content-Type, Authorization, X-Requested-With
access-control-max-age: 300
vary: Origin
content-type: application/json
```

### Test 2: Actual Request (GET)

```bash
curl -X GET https://your-url.lambda-url.us-east-1.on.aws/nh/03462 \
  -H "Origin: chrome-extension://abcdefghijklmnop" \
  -H "Content-Type: application/json" \
  -i
```

**Should see:**
```
HTTP/2 200
access-control-allow-origin: chrome-extension://abcdefghijklmnop
vary: Origin
content-type: application/json
```

**Should NOT see duplicate headers!**

## Chrome Extension Code

No special headers needed - just normal fetch:

```javascript
const API_URL = 'https://your-url.lambda-url.us-east-1.on.aws';

async function getPlans(state, zipCode) {
  const response = await fetch(`${API_URL}/${state}/${zipCode}?details=0`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
      // No CORS headers needed - browser handles it automatically
    }
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return await response.json();
}

// Usage
const data = await getPlans('nh', '03462');
console.log(data);
```

## How CORS Works with Lambda Function URLs

### Request Flow

1. **Browser makes preflight (OPTIONS) request**
   - Browser: `Origin: chrome-extension://abc123`
   - Browser: `Access-Control-Request-Method: GET`

2. **Lambda Function URL intercepts**
   - Checks CORS config
   - Adds CORS headers automatically
   - Returns 200 (or passes to Lambda handler)

3. **Your Lambda handler**
   - Returns `{'statusCode': 200, 'headers': {'Content-Type': '...'}}`
   - NO CORS headers

4. **Lambda Function URL adds CORS headers**
   - `Access-Control-Allow-Origin: chrome-extension://abc123`
   - `Vary: Origin`
   - Other CORS headers from config

5. **Browser receives response**
   - Sees matching origin
   - Allows the request
   - Chrome Extension can fetch data

### Why `AllowOrigins: ["*"]` Works

Chrome extensions have origins like:
- `chrome-extension://abcdefghijklmnop`
- `moz-extension://12345678-90ab-cdef`

The wildcard `*` matches **any** origin, including these extension origins.

**Security note:** This API serves public Medicare data, so `*` is fine. If you had auth/sensitive data, you'd use specific origins:

```json
{
  "AllowOrigins": [
    "https://yourdomain.com",
    "chrome-extension://your-specific-extension-id"
  ]
}
```

## Updating CORS Configuration

If you need to update CORS after deployment:

```bash
# 1. Update the CORS config
cat > /tmp/cors-config.json << 'EOF'
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["*"],
  "AllowHeaders": ["Content-Type", "Authorization", "X-Requested-With", "X-Custom-Header"],
  "MaxAge": 600
}
EOF

# 2. Delete old Function URL config
aws lambda delete-function-url-config \
  --function-name medicare-plan-api \
  --region us-east-1

# 3. Create new one with updated CORS
aws lambda create-function-url-config \
  --function-name medicare-plan-api \
  --auth-type NONE \
  --cors file:///tmp/cors-config.json \
  --region us-east-1

# 4. Get the new URL (should be the same)
aws lambda get-function-url-config \
  --function-name medicare-plan-api \
  --region us-east-1 \
  --query 'FunctionUrl' \
  --output text
```

## Common Mistakes

### ❌ Mistake 1: Adding CORS headers in code
```python
# DON'T DO THIS
headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'  # ❌ Causes duplicates
}
```

### ❌ Mistake 2: Not handling OPTIONS
```python
# Your handler must handle OPTIONS
if event['requestContext']['http']['method'] == 'OPTIONS':
    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}}
```

### ❌ Mistake 3: Restrictive AllowHeaders
```json
{
  "AllowHeaders": ["Content-Type"]  // ❌ Chrome might send Authorization
}
```

Should be:
```json
{
  "AllowHeaders": ["Content-Type", "Authorization", "X-Requested-With"]
}
```

## Summary

**Our Implementation:**
✅ CORS configured at Lambda Function URL level (AWS)
✅ Lambda code only sets `Content-Type`
✅ No manual CORS headers in code
✅ Works perfectly with Chrome Extensions
✅ No duplicate header errors

**Key Principle:**
> Let AWS Lambda Function URL handle CORS automatically.
> Your code should ONLY set Content-Type.

This is the clean, correct way to support Chrome Extensions with Lambda Function URLs!
