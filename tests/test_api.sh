#!/bin/bash
# Test Medicare Plan API - Simple version
# Usage: ./test_api.sh [FUNCTION_URL]

# Default to deployed Lambda URL
FUNCTION_URL="${1:-https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws}"

echo "================================"
echo "Medicare Plan API Tests"
echo "================================"
echo "Testing: $FUNCTION_URL"
echo ""

# Test 1: Health check
echo "1. Health Check"
curl -s "${FUNCTION_URL}/health" | jq '.'
echo ""

# Test 2: List states
echo "2. List States"
curl -s "${FUNCTION_URL}/states" | jq '.states'
echo ""

# Test 3: NH single-county ZIP
echo "3. NH ZIP 03462 (summary)"
curl -s "${FUNCTION_URL}/nh/03462?details=0" | jq '.'
echo ""

# Test 4: NH multi-county ZIP
echo "4. NH ZIP 03602 (multi-county)"
curl -s "${FUNCTION_URL}/nh/03602?details=0" | jq '.'
echo ""

# Test 5: VT ZIP
echo "5. VT ZIP 05401"
curl -s "${FUNCTION_URL}/vt/05401?details=0" | jq '.'
echo ""

# Test 6: WY ZIP
echo "6. WY ZIP 82001"
curl -s "${FUNCTION_URL}/wy/82001?details=0" | jq '.'
echo ""

# Test 7: AK ZIP
echo "7. AK ZIP 99501"
curl -s "${FUNCTION_URL}/ak/99501?details=0" | jq '.'
echo ""

# Test 8: Specific plan details
echo "8. Plan Details (S4802_075_0)"
curl -s "${FUNCTION_URL}/nh/plan/S4802_075_0" | jq '.'
echo ""

# Test 9: List counties
echo "9. List NH Counties"
curl -s "${FUNCTION_URL}/nh/counties" | jq '.'
echo ""

# Test 10: CORS preflight
echo "10. CORS Preflight (Chrome Extension)"
curl -i -X OPTIONS \
  -H "Origin: chrome-extension://test" \
  -H "Access-Control-Request-Method: GET" \
  "${FUNCTION_URL}/nh/03462" 2>&1 | grep -i "access-control"
echo ""

echo "================================"
echo "All tests complete!"
echo "================================"
