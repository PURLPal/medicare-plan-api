#!/usr/bin/env python3
"""
Build county cache files for all states we have complete data for
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import sys

STATE_CONFIGS = {
    'AK': {'name': 'Alaska', 'territory_name': 'Alaska'},
    'NH': {'name': 'New_Hampshire', 'territory_name': 'New Hampshire'},
    'VT': {'name': 'Vermont', 'territory_name': 'Vermont'},
    'WY': {'name': 'Wyoming', 'territory_name': 'Wyoming'}
}

def load_state_plans_from_csv(state_territory_name):
    """Load all plans for a state from CSV"""
    plans_by_county = defaultdict(list)
    all_counties_plans = []

    csv_path = Path('CY2026_Landscape_202511/CY2026_Landscape_202511.csv')

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['State Territory Name'] == state_territory_name:
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

def load_scraped_plan_details(state_name):
    """Load all scraped plan detail JSONs for a state"""
    scraped_dir = Path('scraped_json_all')
    plan_details = {}

    # Files are named like: Alaska-S4802_096_0.json
    state_files = list(scraped_dir.glob(f'{state_name}-*.json'))

    print(f"  Found {len(state_files)} scraped plan detail files")

    for json_file in state_files:
        # Extract plan ID from filename
        plan_id = json_file.stem.split('-', 1)[1]

        with open(json_file, 'r') as f:
            details = json.load(f)
            plan_details[plan_id] = details

    return plan_details

def build_county_caches_for_state(state_abbr, state_config):
    """Build enriched county cache files for one state"""

    state_name = state_config['name']
    territory_name = state_config['territory_name']

    print("\n" + "=" * 80)
    print(f"Building county caches for {territory_name} ({state_abbr})")
    print("=" * 80)

    # Load data
    county_plans, all_counties_plans = load_state_plans_from_csv(territory_name)
    scraped_details = load_scraped_plan_details(state_name)

    print(f"  'All Counties' plans: {len(all_counties_plans)}")
    print(f"  Scraped plan details: {len(scraped_details)}")
    print(f"  Counties with specific plans: {len(county_plans)}")

    # Create output directory
    output_dir = Path(f'mock_api/{state_abbr}/counties')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track statistics
    stats = {
        'total_counties': 0,
        'plans_with_details': 0,
        'plans_without_details': 0,
        'total_plans': 0
    }

    # Build cache for each county
    for county, county_specific in county_plans.items():
        stats['total_counties'] += 1

        # Combine all-counties plans + county-specific plans
        all_plans_for_county = []
        all_plans_for_county.extend(all_counties_plans)
        all_plans_for_county.extend(county_specific)

        stats['total_plans'] += len(all_plans_for_county)

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

        print(f"  ✓ {county:30s}: {len(enriched_plans):3d} plans ({county_cache['scraped_details_available']:3d} with details)")

    # Summary for this state
    print(f"\n  Counties: {stats['total_counties']}")
    print(f"  Total plans: {stats['total_plans']}")
    print(f"  With scraped details: {stats['plans_with_details']}")
    print(f"  Missing details: {stats['plans_without_details']}")

    coverage = (stats['plans_with_details'] / stats['total_plans'] * 100) if stats['total_plans'] > 0 else 0
    print(f"  Coverage: {coverage:.1f}%")

    return stats

def main():
    print("=" * 80)
    print("Building County Caches for All States")
    print("=" * 80)

    overall_stats = {
        'states': 0,
        'counties': 0,
        'plans': 0,
        'with_details': 0,
        'missing_details': 0
    }

    # Build caches for each state
    for state_abbr, config in STATE_CONFIGS.items():
        stats = build_county_caches_for_state(state_abbr, config)
        overall_stats['states'] += 1
        overall_stats['counties'] += stats['total_counties']
        overall_stats['plans'] += stats['total_plans']
        overall_stats['with_details'] += stats['plans_with_details']
        overall_stats['missing_details'] += stats['plans_without_details']

    # Final summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"States processed: {overall_stats['states']}")
    print(f"Total counties: {overall_stats['counties']}")
    print(f"Total plans: {overall_stats['plans']}")
    print(f"Plans with scraped details: {overall_stats['with_details']}")
    print(f"Plans missing details: {overall_stats['missing_details']}")

    coverage = (overall_stats['with_details'] / overall_stats['plans'] * 100) if overall_stats['plans'] > 0 else 0
    print(f"Overall coverage: {coverage:.1f}%")
    print("\n✓ County cache files ready for deployment!")

if __name__ == "__main__":
    main()
