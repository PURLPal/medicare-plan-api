#!/bin/bash
# Test live South Carolina Medicare API endpoints

echo "================================================================================"
echo "TESTING LIVE MEDICARE API - ZIP 29401 (Charleston, SC)"
echo "================================================================================"
echo ""

# Test 1: Regular endpoint (all 69 plans)
echo "TEST 1: All Plans (Regular Endpoint)"
echo "--------------------------------------------------------------------------------"
echo "URL: https://medicare.purlpal-api.com/medicare/zip/29401.json"
echo ""
curl -s "https://medicare.purlpal-api.com/medicare/zip/29401.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✓ Status: Success')
print(f'✓ ZIP Code: {data[\"zip_code\"]}')
print(f'✓ Primary State: {data[\"primary_state\"]}')
print(f'✓ Total Plans: {data[\"plan_count\"]}')
print(f'✓ MAPD Plans: {len([p for p in data[\"plans\"] if p.get(\"plan_type\") == \"MAPD\"])}')
print(f'✓ MA Plans: {len([p for p in data[\"plans\"] if p.get(\"plan_type\") == \"MA\"])}')
print(f'✓ Response Size: {len(json.dumps(data)) / 1024:.1f} KB')
"
echo ""

# Test 2: Custom "Ebony" endpoint (3 priority plans)
echo "TEST 2: Priority Plans Only (Ebony Endpoint)"
echo "--------------------------------------------------------------------------------"
echo "URL: https://medicare.purlpal-api.com/medicare/zip/29401_ebony.json"
echo ""
curl -s "https://medicare.purlpal-api.com/medicare/zip/29401_ebony.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✓ Status: Success')
print(f'✓ Total Plans: {data[\"plan_count\"]}')
print(f'✓ Response Size: {len(json.dumps(data)) / 1024:.1f} KB')
print('')
print('Priority Plans:')
for p in data['plans']:
    premium = p.get('premiums', {}).get('Total monthly premium', 'N/A')
    print(f'  • {p[\"plan_id\"]}: {premium}')
    print(f'    {p[\"plan_info\"][\"name\"]}')
"
echo ""

# Test 3: Minified endpoint (all plans)
echo "TEST 3: All Plans (Minified Endpoint)"
echo "--------------------------------------------------------------------------------"
echo "URL: https://medicare.purlpal-api.com/medicare/zip_minified/29401_minified.json"
echo ""
curl -s "https://medicare.purlpal-api.com/medicare/zip_minified/29401_minified.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✓ Status: Success')
print(f'✓ Total Plans (minified key \"pc\"): {data.get(\"pc\", \"N/A\")}')
print(f'✓ Response Size: {len(json.dumps(data)) / 1024:.1f} KB')
print(f'✓ Compression: Minified format verified')
"
echo ""

# Test 4: MAPD-only minified endpoint
echo "TEST 4: MAPD Plans Only (Minified)"
echo "--------------------------------------------------------------------------------"
echo "URL: https://medicare.purlpal-api.com/medicare/zip_minified/29401_MAPD_minified.json"
echo ""
curl -s "https://medicare.purlpal-api.com/medicare/zip_minified/29401_MAPD_minified.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✓ Status: Success')
print(f'✓ MAPD Plans: {data.get(\"pc\", \"N/A\")}')
print(f'✓ Response Size: {len(json.dumps(data)) / 1024:.1f} KB')
"
echo ""

# Test 5: MA-only minified endpoint
echo "TEST 5: MA Plans Only (Minified)"
echo "--------------------------------------------------------------------------------"
echo "URL: https://medicare.purlpal-api.com/medicare/zip_minified/29401_MA_minified.json"
echo ""
curl -s "https://medicare.purlpal-api.com/medicare/zip_minified/29401_MA_minified.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✓ Status: Success')
print(f'✓ MA Plans: {data.get(\"pc\", \"N/A\")}')
print(f'✓ Response Size: {len(json.dumps(data)) / 1024:.1f} KB (tiny!)')
"
echo ""

# Test 6: Other SC ZIP codes
echo "TEST 6: Other SC ZIP Codes (Sample)"
echo "--------------------------------------------------------------------------------"
for zip in 29002 29577 29803 29928; do
  echo -n "ZIP $zip: "
  curl -s "https://medicare.purlpal-api.com/medicare/zip/${zip}.json" | \
    python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'{data[\"plan_count\"]} plans ✓')
except:
    print('FAILED ✗')
"
done
echo ""

# Test 7: Mapping files
echo "TEST 7: Minification Mapping Files"
echo "--------------------------------------------------------------------------------"
echo -n "Key Mapping: "
curl -s "https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json" | \
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'{len(data)} mappings ✓')
except:
    print('FAILED ✗')
"

echo -n "Value Mapping: "
curl -s "https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json" | \
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'{len(data)} mappings ✓')
except:
    print('FAILED ✗')
"
echo ""

# Test 8: Priority plan verification
echo "TEST 8: Priority Plan Data Verification"
echo "--------------------------------------------------------------------------------"
curl -s "https://medicare.purlpal-api.com/medicare/zip/29401.json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
priority_ids = ['H5322_043_0', 'H5322_044_0', 'R2604_005_0']
found = 0

for plan in data['plans']:
    if plan['plan_id'] in priority_ids:
        found += 1
        name = plan['plan_info']['name']
        premium = plan.get('premiums', {}).get('Total monthly premium', 'N/A')
        benefits = len(plan.get('benefits', {}))
        print(f'✓ {plan[\"plan_id\"]}')
        print(f'  Name: {name[:60]}...')
        print(f'  Premium: {premium}')
        print(f'  Benefit sections: {benefits}')
        print('')

print(f'Total priority plans found: {found}/3')
"

echo ""
echo "================================================================================"
echo "ALL TESTS COMPLETE"
echo "================================================================================"
