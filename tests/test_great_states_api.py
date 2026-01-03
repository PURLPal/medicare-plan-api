#!/usr/bin/env python3
"""
Test script to verify GREAT states are queryable on the deployed API.
Tests both ZIP-based queries and direct plan lookups.
"""
import requests
import json

BASE_URL = 'https://medicare.purlpal-api.com/medicare'

# GREAT states (90%+ names, 50%+ premiums)
GREAT_STATES = {
    'AL': ('Alabama', '35203'),
    'AK': ('Alaska', '99501'),
    'AS': ('American Samoa', '96799'),
    'AZ': ('Arizona', '85001'),
    'CT': ('Connecticut', '06103'),
    'DE': ('Delaware', '19901'),
    'DC': ('District of Columbia', '20001'),
    'HI': ('Hawaii', '96814'),
    'ID': ('Idaho', '83702'),
    'IL': ('Illinois', '60601'),
    'IA': ('Iowa', '50316'),
    'KS': ('Kansas', '66101'),
    'ME': ('Maine', '04101'),
    'MD': ('Maryland', '21201'),
    'MA': ('Massachusetts', '02101'),
    'MT': ('Montana', '59101'),
    'NE': ('Nebraska', '68102'),
    'NH': ('New Hampshire', '03301'),
    'NM': ('New Mexico', '87101'),
    'NY': ('New York', '10001'),
    'ND': ('North Dakota', '58102'),
    'MP': ('Northern Mariana Islands', '96950'),
    'OK': ('Oklahoma', '73101'),
    'PA': ('Pennsylvania', '19019'),
    'RI': ('Rhode Island', '02903'),
    'SD': ('South Dakota', '57101'),
    'TX': ('Texas', '75201'),
    'UT': ('Utah', '84101'),
    'VT': ('Vermont', '05601'),
    'VI': ('Virgin Islands', '00801'),
    'WV': ('West Virginia', '25301'),
    'WY': ('Wyoming', '82001'),
}

def test_zip_query(state_abbrev, zip_code):
    """Test if a ZIP code returns plans."""
    try:
        url = f'{BASE_URL}/zip/{zip_code}.json'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            plan_count = len(data.get('plans', []))
            return 'PASS', plan_count
        else:
            return 'FAIL', f'HTTP {resp.status_code}'
    except Exception as e:
        return 'ERROR', str(e)[:30]

def test_plan_details(plan_id):
    """Test if a plan has full details."""
    try:
        url = f'{BASE_URL}/plan/{plan_id}.json'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            plan = resp.json()
            has_name = bool(plan.get('plan_info', {}).get('name'))
            has_premiums = bool(plan.get('premiums', {}))
            has_benefits = bool(plan.get('benefits', {}))
            
            if has_name and has_premiums and has_benefits:
                return 'EXCELLENT'
            elif has_name:
                return 'GOOD'
            else:
                return 'POOR'
        else:
            return 'MISSING'
    except Exception as e:
        return 'ERROR'

def main():
    print("=" * 80)
    print("TESTING GREAT STATES ON DEPLOYED API")
    print("=" * 80)
    print()
    
    results = {
        'deployed': [],
        'missing': [],
        'errors': []
    }
    
    print(f"{'State':<25} {'ZIP':<10} {'Status':<10} {'Plans':<10} {'Quality':<12}")
    print("-" * 80)
    
    for abbrev, (name, test_zip) in sorted(GREAT_STATES.items()):
        status, result = test_zip_query(abbrev, test_zip)
        
        if status == 'PASS':
            plan_count = result
            if plan_count > 0:
                # Test data quality on first plan
                url = f'{BASE_URL}/zip/{test_zip}.json'
                resp = requests.get(url, timeout=5)
                plans = resp.json().get('plans', [])
                if plans:
                    plan_id = plans[0].get('plan_id')
                    quality = test_plan_details(plan_id)
                else:
                    quality = 'N/A'
                
                print(f"{name:<25} {test_zip:<10} {'✓ PASS':<10} {plan_count:<10} {quality:<12}")
                results['deployed'].append(abbrev)
            else:
                print(f"{name:<25} {test_zip:<10} {'✓ Empty':<10} {plan_count:<10} {'N/A':<12}")
                results['deployed'].append(abbrev)
        elif status == 'FAIL':
            print(f"{name:<25} {test_zip:<10} {'✗ MISSING':<10} {'-':<10} {'-':<12}")
            results['missing'].append(abbrev)
        else:
            print(f"{name:<25} {test_zip:<10} {'✗ ERROR':<10} {'-':<10} {result[:12]:<12}")
            results['errors'].append(abbrev)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Deployed & Queryable: {len(results['deployed'])}/{len(GREAT_STATES)} states")
    print(f"✗ Missing from API: {len(results['missing'])} states")
    if results['errors']:
        print(f"⚠ Errors: {len(results['errors'])} states")
    
    if results['deployed']:
        print(f"\nDeployed: {', '.join(sorted(results['deployed']))}")
    if results['missing']:
        print(f"\nMissing: {', '.join(sorted(results['missing']))}")
    
    print()
    print(f"API Endpoint: {BASE_URL}")
    print("=" * 80)

if __name__ == '__main__':
    main()
