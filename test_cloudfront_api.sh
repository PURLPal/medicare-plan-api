#!/bin/bash
# Test CloudFront Medicare Plan API

# CloudFront API URL
API_URL="${1:-https://d11vrs9xl9u4t7.cloudfront.net/medicare}"

echo "================================"
echo "CloudFront Medicare Plan API Tests"
echo "================================"
echo "Using: $API_URL"
echo ""

# Test 1: List all states
echo "1. List All States"
echo "----------------"
curl -s "$API_URL/states.json" | jq '{
  total_states: .state_count,
  total_plans: .plan_count,
  states: .states | map({code: .state_code, name: .state_name, plans: .plan_count})
}' | head -20
echo ""

# Test 2: Get NH state info
echo "2. New Hampshire State Info"
echo "----------------"
curl -s "$API_URL/state/NH/info.json" | jq '{
  state: .state_name,
  plan_count: .plan_count,
  county_count: .county_count
}'
echo ""

# Test 3: Get plans by ZIP (showing category field)
echo "3. Plans by ZIP 03462 (Cheshire County, NH)"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  state: .primary_state,
  plan_count,
  plans: .plans | map({
    plan_id,
    category,
    plan_type,
    name: .plan_info.name,
    organization: .plan_info.organization,
    monthly_premium: .premiums["Total monthly premium"]
  })
}' | head -40
echo ""

# Test 4: Filter MAPD plans only
echo "4. MAPD Plans Only in ZIP 03462"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  mapd_count: (.plans | map(select(.category == "MAPD")) | length),
  mapd_plans: .plans | map(select(.category == "MAPD")) | map({
    plan_id,
    category,
    name: .plan_info.name,
    organization: .plan_info.organization,
    premium: .premiums["Total monthly premium"],
    drug_deductible: .deductibles["Drug deductible"]
  })
}'
echo ""

# Test 5: Filter MA plans only (no drug coverage)
echo "5. MA Plans Only in ZIP 03462"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  ma_count: (.plans | map(select(.category == "MA")) | length),
  ma_plans: .plans | map(select(.category == "MA")) | map({
    plan_id,
    category,
    name: .plan_info.name,
    organization: .plan_info.organization,
    premium: .premiums["Total monthly premium"]
  })
}'
echo ""

# Test 6: Filter PD plans only (Part D drug plans)
echo "6. Part D Drug Plans Only in ZIP 03462"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  pd_count: (.plans | map(select(.category == "PD")) | length),
  pd_plans: .plans | map(select(.category == "PD")) | map({
    plan_id,
    category,
    name: .plan_info.name,
    organization: .plan_info.organization,
    premium: .premiums["Total monthly premium"],
    drug_deductible: .deductibles["Drug deductible"]
  })
}'
echo ""

# Test 7: Count plans by category
echo "7. Plan Category Breakdown for ZIP 03462"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  total_plans: (.plans | length),
  mapd_plans: (.plans | map(select(.category == "MAPD")) | length),
  ma_plans: (.plans | map(select(.category == "MA")) | length),
  pd_plans: (.plans | map(select(.category == "PD")) | length)
}'
echo ""

# Test 8: Get specific plan details
echo "8. Specific Plan Details (H6851_001_0)"
echo "----------------"
curl -s "$API_URL/plan/H6851_001_0.json" | jq '{
  plan_id,
  category,
  plan_type,
  name: .plan_info.name,
  organization: .plan_info.organization,
  type: .plan_info.type,
  premiums,
  deductibles,
  maximum_out_of_pocket
}'
echo ""

# Test 9: Compare MAPD vs PD plans
echo "9. Compare MAPD vs PD Plans (Drug Coverage)"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  comparison: {
    mapd: {
      count: (.plans | map(select(.category == "MAPD")) | length),
      avg_premium: (.plans | map(select(.category == "MAPD")) | map(.premiums["Total monthly premium"] | gsub("[^0-9.]"; "") | tonumber) | add / length | floor),
      plans: (.plans | map(select(.category == "MAPD")) | map({
        name: .plan_info.name,
        premium: .premiums["Total monthly premium"]
      }))
    },
    pd: {
      count: (.plans | map(select(.category == "PD")) | length),
      avg_premium: (.plans | map(select(.category == "PD")) | map(.premiums["Total monthly premium"] | gsub("[^0-9.]"; "") | tonumber) | add / length | floor),
      plans: (.plans | map(select(.category == "PD")) | map({
        name: .plan_info.name,
        premium: .premiums["Total monthly premium"]
      }))
    }
  }
}'
echo ""

# Test 10: Multi-state ZIP check
echo "10. Check Multi-State ZIP (if available)"
echo "----------------"
curl -s "$API_URL/zip/03462.json" | jq '{
  zip_code,
  multi_state,
  multi_county,
  states,
  counties: .counties | map({
    name,
    state,
    fips
  })
}'
echo ""

echo "================================"
echo "Tests Complete!"
echo ""
echo "API Filtering Examples:"
echo "  - Filter MAPD: jq '.plans | map(select(.category == \"MAPD\"))'"
echo "  - Filter MA:   jq '.plans | map(select(.category == \"MA\"))'"
echo "  - Filter PD:   jq '.plans | map(select(.category == \"PD\"))'"
echo ""
echo "Custom Domain (when DNS propagates):"
echo "  https://medicare.purlpal-api.com/medicare/"
echo "================================"
