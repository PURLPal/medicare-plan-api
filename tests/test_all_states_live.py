#!/usr/bin/env python3
"""
Test which states are actually deployed and operational on the live API
"""
import requests
import json
from pathlib import Path

print("="*80)
print("LIVE DEPLOYMENT STATUS - TESTING ACTUAL ENDPOINTS")
print("="*80)
print()

# Representative ZIP codes for each state
test_zips = {
    'AK': '99501',  # Anchorage
    'AL': '35203',  # Birmingham
    'AR': '72201',  # Little Rock
    'AS': '96799',  # Pago Pago
    'AZ': '85001',  # Phoenix
    'CA': '90001',  # Los Angeles
    'CO': '80201',  # Denver
    'CT': '06101',  # Hartford
    'DC': '20001',  # Washington DC
    'DE': '19901',  # Dover
    'FL': '33101',  # Miami
    'GA': '30301',  # Atlanta
    'GU': '96910',  # Guam
    'HI': '96801',  # Honolulu
    'IA': '50301',  # Des Moines
    'ID': '83701',  # Boise
    'IL': '60601',  # Chicago
    'IN': '46201',  # Indianapolis
    'KS': '66101',  # Kansas City
    'KY': '40201',  # Louisville
    'LA': '70112',  # New Orleans
    'MA': '02101',  # Boston
    'MD': '21201',  # Baltimore
    'ME': '04101',  # Portland
    'MI': '48201',  # Detroit
    'MN': '55401',  # Minneapolis
    'MO': '63101',  # St. Louis
    'MP': '96950',  # Saipan
    'MS': '39201',  # Jackson
    'MT': '59601',  # Helena
    'NC': '27601',  # Raleigh
    'ND': '58501',  # Bismarck
    'NE': '68901',  # Hastings
    'NH': '03101',  # Manchester
    'NJ': '07101',  # Newark
    'NM': '87101',  # Albuquerque
    'NV': '89101',  # Las Vegas
    'NY': '10001',  # Manhattan
    'OH': '43201',  # Columbus
    'OK': '73101',  # Oklahoma City
    'OR': '97201',  # Portland
    'PA': '15201',  # Pittsburgh
    'PR': '00901',  # San Juan
    'RI': '02901',  # Providence
    'SC': '29401',  # Charleston
    'SD': '57501',  # Sioux Falls
    'TN': '37201',  # Nashville
    'TX': '75201',  # Dallas
    'UT': '84101',  # Salt Lake City
    'VI': '00802',  # St Thomas
    'VT': '05601',  # Montpelier
    'VA': '23219',  # Richmond
    'WA': '98101',  # Seattle
    'WI': '53201',  # Milwaukee
    'WV': '25301',  # Charleston
    'WY': '82001',  # Cheyenne
}

deployed_states = {}
failed_states = {}

print("Testing live endpoints for all 50+ states/territories...")
print()

for state, zip_code in sorted(test_zips.items()):
    url = f'https://medicare.purlpal-api.com/medicare/zip/{zip_code}.json'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            plan_count = data.get('plan_count', 0)
            if plan_count > 0:
                deployed_states[state] = {
                    'zip': zip_code,
                    'plans': plan_count,
                    'primary_state': data.get('primary_state', state)
                }
                status = f"✓ {plan_count} plans"
            else:
                status = "⚠️  0 plans (empty)"
                failed_states[state] = 'No plans'
        else:
            status = f"✗ HTTP {response.status_code}"
            failed_states[state] = f'HTTP {response.status_code}'
    except Exception as e:
        status = f"✗ {str(e)[:40]}"
        failed_states[state] = 'Connection error'
    
    print(f"  {state} ({zip_code}): {status}")

print()
print("="*80)
print("DEPLOYMENT SUMMARY")
print("="*80)
print()

# Categorize states
print(f"✅ DEPLOYED & OPERATIONAL: {len(deployed_states)} states/territories")
print("-" * 80)

# Group by region for better organization
regions = {
    'New England': ['CT', 'ME', 'MA', 'NH', 'RI', 'VT'],
    'Mid-Atlantic': ['DC', 'DE', 'MD', 'NJ', 'NY', 'PA'],
    'Southeast': ['AL', 'AR', 'FL', 'GA', 'KY', 'LA', 'MS', 'NC', 'SC', 'TN', 'VA', 'WV'],
    'Midwest': ['IA', 'IL', 'IN', 'KS', 'MI', 'MN', 'MO', 'ND', 'NE', 'OH', 'SD', 'WI'],
    'Southwest': ['AZ', 'NM', 'OK', 'TX'],
    'West': ['AK', 'CA', 'CO', 'HI', 'ID', 'MT', 'NV', 'OR', 'UT', 'WA', 'WY'],
    'Territories': ['AS', 'GU', 'MP', 'PR', 'VI']
}

for region, states in regions.items():
    deployed_in_region = [s for s in states if s in deployed_states]
    if deployed_in_region:
        print(f"\n{region}:")
        for state in deployed_in_region:
            info = deployed_states[state]
            print(f"  • {state}: {info['plans']} plans (ZIP {info['zip']})")

print()
print("-" * 80)

# Separate states from territories
territories = ['AS', 'GU', 'MP', 'PR', 'VI']
failed_territories = {s: r for s, r in failed_states.items() if s in territories}
failed_regular_states = {s: r for s, r in failed_states.items() if s not in territories}

print(f"\n❌ NOT DEPLOYED: {len(failed_regular_states)} states, {len(failed_territories)} territories")
if failed_regular_states:
    print()
    print("States:")
    for state, reason in sorted(failed_regular_states.items()):
        print(f"  • {state}: {reason}")

if failed_territories:
    print()
    print("Territories:")
    for territory, reason in sorted(failed_territories.items()):
        print(f"  • {territory}: {reason}")

print()
print("="*80)
print("STATISTICS")
print("="*80)

total_plans = sum(s['plans'] for s in deployed_states.values())
avg_plans = total_plans / len(deployed_states) if deployed_states else 0

print(f"Total states/territories tested: {len(test_zips)}")
print(f"Successfully deployed: {len(deployed_states)}")
print(f"Not deployed/empty: {len(failed_states)}")
print(f"Deployment rate: {len(deployed_states)/len(test_zips)*100:.1f}%")
print()
print(f"Total plans across deployed states: {total_plans:,}")
print(f"Average plans per state: {avg_plans:.1f}")
print()

# Top states by plan count
print("Top 10 States by Plan Count:")
print("-" * 80)
top_states = sorted(deployed_states.items(), key=lambda x: x[1]['plans'], reverse=True)[:10]
for i, (state, info) in enumerate(top_states, 1):
    print(f"  {i:2}. {state}: {info['plans']:4} plans")

print()
print("="*80)
