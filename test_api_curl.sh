#!/bin/bash
# Test Medicare Plan API using curl
# Replace FUNCTION_URL with your actual Lambda Function URL after deployment

# FUNCTION_URL="https://your-function-url.lambda-url.us-east-1.on.aws"
FUNCTION_URL="${1:-http://localhost:5000}"  # Default to local for testing

echo "================================"
echo "Medicare Plan API - curl Tests"
echo "================================"
echo "Using: $FUNCTION_URL"
echo ""

# Test 1: Health check
echo "1. Health Check"
echo "----------------"
curl -s "${FUNCTION_URL}/health" | jq '.'
echo ""

# Test 2: List all states
echo "2. List States"
echo "----------------"
curl -s "${FUNCTION_URL}/states" | jq '.states[] | {key, name, zip_codes, counties}'
echo ""

# Test 3: NH single-county ZIP (summary only)
echo "3. NH ZIP 03462 (Cheshire) - Summary Only"
echo "----------------"
curl -s "${FUNCTION_URL}/nh/03462?details=0" | jq '{
  zip_code,
  state,
  multi_county,
  counties: (.counties | to_entries | map({
    county: .key,
    plan_count: .value.plan_count,
    with_details: .value.scraped_details_available
  }))
}'
echo ""

# Test 4: NH multi-county ZIP (summary only)
echo "4. NH ZIP 03602 (Cheshire/Sullivan) - Summary Only"
echo "----------------"
curl -s "${FUNCTION_URL}/nh/03602?details=0" | jq '{
  zip_code,
  state,
  multi_county,
  primary_county,
  counties: (.counties | to_entries | map({
    county: .key,
    percentage: .value.percentage,
    plan_count: .value.plan_count
  }))
}'
echo ""

# Test 5: VT ZIP
echo "5. VT ZIP 05401 - Summary Only"
echo "----------------"
curl -s "${FUNCTION_URL}/vt/05401?details=0" | jq '{
  zip_code,
  state,
  multi_county,
  plan_count: (.counties | to_entries[0].value.plan_count)
}'
echo ""

# Test 6: WY ZIP
echo "6. WY ZIP 82001 - Summary Only"
echo "----------------"
curl -s "${FUNCTION_URL}/wy/82001?details=0" | jq '{
  zip_code,
  state,
  multi_county,
  plan_count: (.counties | to_entries[0].value.plan_count)
}'
echo ""

# Test 7: Get specific plan with full details
echo "7. NH Plan Details (S4802_075_0)"
echo "----------------"
curl -s "${FUNCTION_URL}/nh/plan/S4802_075_0" | jq '{
  plan_id,
  state,
  county,
  name: .summary.plan_name,
  organization: .summary.organization,
  has_details: .has_scraped_details,
  address: .details.contact_info["Plan address"]
}'
echo ""

# Test 8: List NH counties
echo "8. List NH Counties"
echo "----------------"
curl -s "${FUNCTION_URL}/nh/counties" | jq '{
  state,
  county_count,
  counties: (.counties | map({name, plan_count, with_details: .scraped_details_available}))
}'
echo ""

# Test 9: Full details for a ZIP (larger response)
echo "9. NH ZIP 03462 - Full Details (sample)"
echo "----------------"
curl -s "${FUNCTION_URL}/nh/03462" | jq '{
  zip_code,
  state,
  plan_count: (.counties.Cheshire.plan_count),
  sample_plan: .counties.Cheshire.plans[0] | {
    name: .summary.plan_name,
    organization: .summary.organization,
    premium: .details.premiums,
    deductible: .details.deductibles,
    address: .details.contact_info["Plan address"]
  }
}'
echo ""

# Test 10: CORS preflight (Chrome Extension compatibility)
echo "10. CORS Preflight Check"
echo "----------------"
curl -i -X OPTIONS \
  -H "Origin: chrome-extension://abcdefghijklmnop" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  "${FUNCTION_URL}/nh/03462" 2>&1 | grep -i "access-control"
echo ""

echo "================================"
echo "Tests Complete!"
echo "================================"
