#!/usr/bin/env python3
"""
Test the API without running Flask server
Demonstrates the lookup logic
"""

import json
from pathlib import Path

def load_zip_to_county():
    """Load ZIP to county mapping"""
    with open('mock_api/NH/zip_to_county_multi.json', 'r') as f:
        zip_data = json.load(f)
        return {entry['zip']: entry for entry in zip_data}

def load_county_cache(county_name):
    """Load cached county data"""
    county_file = Path(f'mock_api/NH/counties/{county_name}.json')
    with open(county_file, 'r') as f:
        return json.load(f)

def get_plans_for_zip(zip_code, include_details=True):
    """Get plans for a ZIP code"""
    zip_to_county = load_zip_to_county()

    if zip_code not in zip_to_county:
        return {'error': 'ZIP code not found'}

    zip_info = zip_to_county[zip_code]

    response = {
        'zip_code': zip_code,
        'multi_county': zip_info['multi_county'],
        'primary_county': zip_info['primary_county']['name'],
        'counties': {}
    }

    # Load plans for each county
    for county_info in zip_info['counties']:
        county_name = county_info['name']
        county_data = load_county_cache(county_name)

        if include_details:
            plans = county_data['plans']
        else:
            # Summary only
            plans = [
                {
                    'contract_plan_segment_id': p['summary']['contract_plan_segment_id'],
                    'plan_name': p['summary']['plan_name'],
                    'plan_type': p['summary']['plan_type'],
                    'organization': p['summary']['organization'],
                    'has_scraped_details': p['has_scraped_details']
                }
                for p in county_data['plans']
            ]

        response['counties'][county_name] = {
            'fips': county_info['fips'],
            'percentage': county_info.get('percentage'),
            'plan_count': len(plans),
            'scraped_details_available': county_data['scraped_details_available'],
            'plans': plans
        }

    return response

def main():
    print("=" * 80)
    print("Testing Medicare Plan API")
    print("=" * 80)

    # Test 1: Single-county ZIP
    print("\n1. Testing single-county ZIP (03462 - Cheshire only)")
    print("-" * 80)
    result = get_plans_for_zip('03462', include_details=False)
    print(f"Multi-county: {result['multi_county']}")
    print(f"Counties: {list(result['counties'].keys())}")
    for county, data in result['counties'].items():
        print(f"\n  {county}:")
        print(f"    Total plans: {data['plan_count']}")
        print(f"    With scraped details: {data['scraped_details_available']}")
        print(f"    Sample plans:")
        for plan in data['plans'][:3]:
            print(f"      - {plan['plan_name']} ({plan['plan_type']})")

    # Test 2: Multi-county ZIP
    print("\n\n2. Testing multi-county ZIP (03602 - Cheshire/Sullivan)")
    print("-" * 80)
    result = get_plans_for_zip('03602', include_details=False)
    print(f"Multi-county: {result['multi_county']}")
    print(f"Primary county: {result['primary_county']}")
    print(f"Counties: {list(result['counties'].keys())}")
    for county, data in result['counties'].items():
        pct = data['percentage']
        print(f"\n  {county} ({pct}% of ZIP):")
        print(f"    Total plans: {data['plan_count']}")
        print(f"    With scraped details: {data['scraped_details_available']}")

    # Test 3: Get full details for one plan
    print("\n\n3. Testing full plan details")
    print("-" * 80)
    result = get_plans_for_zip('03462', include_details=True)
    first_plan = result['counties']['Cheshire']['plans'][0]

    print(f"Plan: {first_plan['summary']['plan_name']}")
    print(f"Organization: {first_plan['summary']['organization']}")
    print(f"Has scraped details: {first_plan['has_scraped_details']}")

    if first_plan['has_scraped_details'] and first_plan['details']:
        print("\nScraped Details:")
        print(f"  Address: {first_plan['details']['contact_info'].get('Plan address', 'N/A')}")
        if 'premiums' in first_plan['details']:
            print(f"  Premiums: {first_plan['details']['premiums']}")
        if 'deductibles' in first_plan['details']:
            print(f"  Deductibles: {first_plan['details']['deductibles']}")

    # Test 4: Response size comparison
    print("\n\n4. Response size comparison")
    print("-" * 80)
    summary_response = get_plans_for_zip('03462', include_details=False)
    full_response = get_plans_for_zip('03462', include_details=True)

    summary_size = len(json.dumps(summary_response))
    full_size = len(json.dumps(full_response))

    print(f"Summary only: {summary_size:,} bytes")
    print(f"Full details: {full_size:,} bytes")
    print(f"Ratio: {full_size / summary_size:.1f}x larger")

    print("\n" + "=" * 80)
    print("Tests complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
