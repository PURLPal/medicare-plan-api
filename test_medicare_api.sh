#!/bin/bash
# Medicare Plan API - Easy Testing Script
# This script tests the production Medicare API with real examples
# Perfect for beginners - just run: ./test_medicare_api.sh

# Production API URL - DO NOT CHANGE
API_URL="https://medicare.purlpal-api.com/medicare"

echo "╔════════════════════════════════════════════════════════╗"
echo "║        Medicare Plan API - Production Tests           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📍 API URL: $API_URL"
echo ""
echo "⏳ Running tests... (this may take 10-20 seconds)"
echo ""

# Test 1: Get all states
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: List All States"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/states.json" | jq '{
  "Total States": .state_count,
  "Total Plans": .plan_count,
  "Generated": .generated_at,
  "Sample States": .states[0:3] | map({
    code: .state_code,
    name: .state_name,
    plans: .plan_count
  })
}'
echo ""
echo "✅ Test 1 Complete"
echo ""

# Test 2: New Hampshire ZIP 03462 (Cheshire County)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Plans for ZIP 03462 (Keene, NH)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/zip/03462.json" | jq '{
  "ZIP Code": .zip_code,
  "Location": .counties[0].name,
  "State": .primary_state,
  "Total Plans": (.plans | length),
  "Plan Breakdown": {
    "MAPD (Medicare Advantage + Drugs)": (.plans | map(select(.category == "MAPD")) | length),
    "MA (Medicare Advantage Only)": (.plans | map(select(.category == "MA")) | length),
    "PD (Part D Drug Plans)": (.plans | map(select(.category == "PD")) | length)
  }
}'
echo ""
echo "✅ Test 2 Complete"
echo ""

# Test 3: Filter MAPD plans only for ZIP 03462
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Filter MAPD Plans (Medicare Advantage + Drugs)"
echo "ZIP: 03462 (Keene, NH)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/zip/03462.json" | jq '
  .plans |
  map(select(.category == "MAPD")) |
  map({
    "Plan Name": .plan_info.name,
    "Provider": .plan_info.organization,
    "Monthly Premium": .premiums["Total monthly premium"],
    "Drug Deductible": .deductibles["Drug deductible"]
  })
'
echo ""
echo "✅ Test 3 Complete"
echo ""

# Test 4: Alaska ZIP 99801 (Juneau)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Plans for ZIP 99801 (Juneau, AK)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/zip/99801.json" | jq '{
  "ZIP Code": .zip_code,
  "State": .primary_state,
  "Total Plans": (.plans | length),
  "Sample Plans": .plans[0:3] | map({
    name: .plan_info.name,
    category,
    premium: .premiums["Total monthly premium"]
  })
}'
echo ""
echo "✅ Test 4 Complete"
echo ""

# Test 5: Vermont ZIP 05401 (Burlington)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: Plans for ZIP 05401 (Burlington, VT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/zip/05401.json" | jq '{
  "ZIP Code": .zip_code,
  "Total Plans": (.plans | length),
  "Zero Premium Plans": (.plans | map(select(.premiums["Total monthly premium"] == "$0.00")) | length),
  "Providers": (.plans | map(.plan_info.organization) | unique)
}'
echo ""
echo "✅ Test 5 Complete"
echo ""

# Test 6: Wyoming ZIP 82001 (Cheyenne)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Plans for ZIP 82001 (Cheyenne, WY)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/zip/82001.json" | jq '{
  "ZIP Code": .zip_code,
  "State": .primary_state,
  "Total Plans": (.plans | length),
  "Plan Types": (.plans | map(.plan_type) | unique)
}'
echo ""
echo "✅ Test 6 Complete"
echo ""

# Test 7: Get specific plan details
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Detailed Plan Information"
echo "Plan: S4802_075_0 (HealthSpring PDP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$API_URL/plan/S4802_075_0.json" | jq '{
  "Plan ID": .plan_id,
  "Category": .category,
  "Plan Name": .plan_info.name,
  "Organization": .plan_info.organization,
  "Monthly Premium": .premiums["Total monthly premium"],
  "Drug Deductible": .deductibles["Drug deductible"],
  "Plan Address": .contact_info["Plan address"]
}'
echo ""
echo "✅ Test 7 Complete"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════╗"
echo "║                  ALL TESTS COMPLETE!                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Sample ZIP Codes to Try:"
echo "   • 03462 - Keene, NH (14 plans)"
echo "   • 99801 - Juneau, AK (42 plans)"
echo "   • 05401 - Burlington, VT"
echo "   • 82001 - Cheyenne, WY"
echo "   • 59801 - Missoula, MT"
echo "   • 03820 - Dover, NH"
echo ""
echo "🔍 Filter Examples:"
echo "   MAPD Plans: curl '$API_URL/zip/03462.json' | jq '.plans | map(select(.category == \"MAPD\"))'"
echo "   MA Plans:   curl '$API_URL/zip/03462.json' | jq '.plans | map(select(.category == \"MA\"))'"
echo "   PD Plans:   curl '$API_URL/zip/03462.json' | jq '.plans | map(select(.category == \"PD\"))'"
echo ""
echo "📖 Full Documentation:"
echo "   • API_REFERENCE.md - Complete API guide"
echo "   • API_DEPLOYMENT.md - Deployment and update guide"
echo ""
echo "✨ API Features:"
echo "   ✅ CORS enabled for Chrome extensions"
echo "   ✅ Custom domain: medicare.purlpal-api.com"
echo "   ✅ Global CDN with ~50ms latency"
echo "   ✅ Filter by plan category (MAPD, MA, PD)"
echo "   ✅ Filter by premium, provider, plan type"
echo ""
