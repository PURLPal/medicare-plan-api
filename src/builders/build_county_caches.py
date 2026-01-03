#!/usr/bin/env python3
"""
Build pre-computed county cache files with full plan details
This combines the basic plan info from CSV with scraped detail JSONs
"""

import json
import csv
from pathlib import Path
from collections import defaultdict

def load_nh_plans_from_csv():
    """Load all NH plans from CSV"""
    plans_by_county = defaultdict(list)
    all_counties_plans = []

    csv_path = Path('CY2026_Landscape_202511/CY2026_Landscape_202511.csv')

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['State Territory Name'] == 'New Hampshire':
                county = row['County Name']
                plan_id = row['ContractPlanSegmentID']

                plan_info = {
                    'contract_plan_segment_id': plan_id,
                    'plan_name': row['Plan Name'],
                    'plan_type': row['Plan Type'],
                    'organization': row['Organization Marketing Name'],
                    'part_c_premium': row['Part C Premium'],
                    'part_d_total_premium': row['Part D Total Premium'],
                    'overall_star_rating': row['Overall Star Rating'],
                    'county': county,
                    'snp_type': row['SNP Type'],
                    'parent_organization': row['Parent Organization Name']
                }

                if county == 'All Counties':
                    all_counties_plans.append(plan_info)
                else:
                    plans_by_county[county].append(plan_info)

    return plans_by_county, all_counties_plans

def load_scraped_plan_details():
    """Load all scraped plan detail JSONs, indexed by plan ID"""
    scraped_dir = Path('scraped_json_all')
    plan_details = {}

    # We have New_Hampshire-{plan_id}.json files
    nh_files = list(scraped_dir.glob('New_Hampshire-*.json'))

    print(f"Found {len(nh_files)} scraped NH plan detail files")

    for json_file in nh_files:
        # Extract plan ID from filename: New_Hampshire-S4802_096_0.json -> S4802_096_0
        plan_id = json_file.stem.split('-', 1)[1]

        with open(json_file, 'r') as f:
            details = json.load(f)
            plan_details[plan_id] = details

    return plan_details

def build_county_caches(state_abbr='NH', state_name='New_Hampshire'):
    """Build enriched county cache files"""

    print("=" * 80)
    print(f"Building county cache files for {state_name}")
    print("=" * 80)

    # Load data
    county_plans, all_counties_plans = load_nh_plans_from_csv()
    scraped_details = load_scraped_plan_details()

    print(f"\nLoaded {len(all_counties_plans)} 'All Counties' plans")
    print(f"Loaded {len(scraped_details)} scraped plan details")
    print(f"County-specific plans for {len(county_plans)} counties")

    # Create output directory
    output_dir = Path(f'mock_api/{state_abbr}/counties')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track statistics
    stats = {
        'total_counties': 0,
        'plans_with_details': 0,
        'plans_without_details': 0
    }

    # Build cache for each county
    for county, county_specific in county_plans.items():
        stats['total_counties'] += 1

        # Combine all-counties plans + county-specific plans
        all_plans_for_county = []
        all_plans_for_county.extend(all_counties_plans)
        all_plans_for_county.extend(county_specific)

        # Enrich with scraped details
        enriched_plans = []
        for plan in all_plans_for_county:
            plan_id = plan['contract_plan_segment_id']

            # Start with CSV data
            enriched_plan = {
                'summary': plan,
                'details': None,
                'has_scraped_details': False
            }

            # Add scraped details if available
            if plan_id in scraped_details:
                enriched_plan['details'] = scraped_details[plan_id]
                enriched_plan['has_scraped_details'] = True
                stats['plans_with_details'] += 1
            else:
                stats['plans_without_details'] += 1

            enriched_plans.append(enriched_plan)

        # Save county cache
        county_cache = {
            'state': state_name,
            'state_abbr': state_abbr,
            'county': county,
            'plan_count': len(enriched_plans),
            'all_counties_plan_count': len(all_counties_plans),
            'county_specific_plan_count': len(county_specific),
            'scraped_details_available': sum(1 for p in enriched_plans if p['has_scraped_details']),
            'plans': enriched_plans
        }

        output_file = output_dir / f'{county}.json'
        with open(output_file, 'w') as f:
            json.dump(county_cache, f, indent=2)

        print(f"✓ {county:20s}: {len(enriched_plans):3d} plans ({county_cache['scraped_details_available']:3d} with details)")

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total counties: {stats['total_counties']}")
    print(f"Plans with scraped details: {stats['plans_with_details']}")
    print(f"Plans without scraped details: {stats['plans_without_details']}")
    print(f"\nCounty cache files saved to: {output_dir}/")

def main():
    build_county_caches()

if __name__ == "__main__":
    main()
