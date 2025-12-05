#!/usr/bin/env python3
"""
Build ZIP code to plans mapping for New Hampshire
For each ZIP code, returns all counties it could be in, with plans for each county
"""

import json
import csv
from pathlib import Path
from collections import defaultdict

def load_nh_plans_from_csv():
    """Load all NH plans from the CSV, organized by county"""
    plans_by_county = defaultdict(list)
    all_counties_plans = []

    csv_path = Path('CY2026_Landscape_202511/CY2026_Landscape_202511.csv')

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['State Territory Name'] == 'New Hampshire':
                county = row['County Name']

                plan_info = {
                    'contract_plan_segment_id': row['ContractPlanSegmentID'],
                    'plan_name': row['Plan Name'],
                    'plan_type': row['Plan Type'],
                    'organization': row['Organization Marketing Name'],
                    'part_c_premium': row['Part C Premium'],
                    'part_d_total_premium': row['Part D Total Premium'],
                    'overall_star_rating': row['Overall Star Rating'],
                    'county': county
                }

                if county == 'All Counties':
                    all_counties_plans.append(plan_info)
                else:
                    plans_by_county[county].append(plan_info)

    return plans_by_county, all_counties_plans

def build_zip_to_plans_mapping():
    """Build mapping from ZIP code to counties to plans"""

    print("Loading NH plans from CSV...")
    county_specific_plans, all_counties_plans = load_nh_plans_from_csv()

    print(f"Found {len(all_counties_plans)} 'All Counties' plans")
    print(f"Found county-specific plans for {len(county_specific_plans)} counties")

    # Load ZIP to county mapping
    zip_to_county_path = Path('mock_api/NH/zip_to_county_multi.json')
    with open(zip_to_county_path, 'r') as f:
        zip_to_county_data = json.load(f)

    print(f"Loaded {len(zip_to_county_data)} ZIP codes")

    # Build the mapping
    zip_to_plans = {}

    for zip_entry in zip_to_county_data:
        zip_code = zip_entry['zip']

        # For multi-county ZIPs, include all possible counties
        # For single-county ZIPs, just include that one county
        counties_for_this_zip = {}

        if zip_entry['multi_county']:
            # Multi-county ZIP: show all counties user could be in
            for county_info in zip_entry['counties']:
                county_name = county_info['name']

                # Combine all-counties plans + county-specific plans
                plans_for_county = []
                plans_for_county.extend(all_counties_plans)
                plans_for_county.extend(county_specific_plans.get(county_name, []))

                counties_for_this_zip[county_name] = {
                    'percentage': county_info['percentage'],
                    'fips': county_info['fips'],
                    'plans': plans_for_county,
                    'plan_count': len(plans_for_county)
                }
        else:
            # Single county ZIP
            county_name = zip_entry['county']

            # Combine all-counties plans + county-specific plans
            plans_for_county = []
            plans_for_county.extend(all_counties_plans)
            plans_for_county.extend(county_specific_plans.get(county_name, []))

            counties_for_this_zip[county_name] = {
                'fips': zip_entry['fips'],
                'plans': plans_for_county,
                'plan_count': len(plans_for_county)
            }

        zip_to_plans[zip_code] = {
            'multi_county': zip_entry['multi_county'],
            'county_count': zip_entry['county_count'],
            'primary_county': zip_entry['primary_county']['name'],
            'counties': counties_for_this_zip
        }

    return zip_to_plans

def main():
    print("=" * 80)
    print("Building New Hampshire ZIP to Plans Mapping")
    print("=" * 80)

    zip_to_plans = build_zip_to_plans_mapping()

    # Save the mapping
    output_path = Path('mock_api/NH/zip_to_plans.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(zip_to_plans, f, indent=2)

    print(f"\n✓ Saved mapping to {output_path}")
    print(f"  Total ZIP codes: {len(zip_to_plans)}")

    # Show some examples
    print("\n" + "=" * 80)
    print("Example 1: Multi-county ZIP (03602)")
    print("=" * 80)
    if '03602' in zip_to_plans:
        example = zip_to_plans['03602']
        print(f"Multi-county: {example['multi_county']}")
        print(f"Primary county: {example['primary_county']}")
        print(f"Counties available:")
        for county, data in example['counties'].items():
            pct = data.get('percentage', 'N/A')
            print(f"  - {county}: {data['plan_count']} plans (percentage: {pct})")

    print("\n" + "=" * 80)
    print("Example 2: Single-county ZIP (03462)")
    print("=" * 80)
    if '03462' in zip_to_plans:
        example = zip_to_plans['03462']
        print(f"Multi-county: {example['multi_county']}")
        print(f"Primary county: {example['primary_county']}")
        print(f"Counties available:")
        for county, data in example['counties'].items():
            print(f"  - {county}: {data['plan_count']} plans")
            print(f"    Sample plans:")
            for plan in data['plans'][:3]:
                print(f"      • {plan['plan_name']} ({plan['plan_type']})")

    print("\n" + "=" * 80)
    print("Multi-county ZIP statistics:")
    print("=" * 80)
    multi_county_zips = [z for z, d in zip_to_plans.items() if d['multi_county']]
    single_county_zips = [z for z, d in zip_to_plans.items() if not d['multi_county']]

    print(f"Multi-county ZIPs: {len(multi_county_zips)}")
    print(f"Single-county ZIPs: {len(single_county_zips)}")

    print("\nDone!")

if __name__ == "__main__":
    main()
