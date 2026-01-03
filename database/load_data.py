#!/usr/bin/env python3
"""
Load scraped Medicare data into PostgreSQL database.
"""
import json
import psycopg2
from pathlib import Path
import re
from decimal import Decimal

# Data paths
SCRAPED_DATA_DIR = Path('scraped_data/json')
PLAN_COUNTY_MAPPINGS = Path('plan_county_mappings.json')
UNIFIED_ZIP_FILE = Path('unified_zip_to_fips.json')

STATE_NAME_TO_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District_of_Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New_Hampshire': 'NH', 'New_Jersey': 'NJ', 'New_Mexico': 'NM',
    'New_York': 'NY', 'North_Carolina': 'NC', 'North_Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode_Island': 'RI',
    'South_Carolina': 'SC', 'South_Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West_Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'American_Samoa': 'AS', 'Guam': 'GU', 'Northern_Mariana_Islands': 'MP',
    'Puerto_Rico': 'PR', 'Virgin_Islands': 'VI'
}

CMS_CATEGORY_TO_SUNFIRE = {
    'MA-PD': 'MAPD',
    'SNP': 'MAPD',
    'MA': 'MA',
    'PDP': 'PD',
}

def parse_currency(value):
    """Extract numeric value from currency string."""
    if not value or value == 'N/A':
        return None
    # Remove $, commas, and other non-numeric chars except decimal
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return Decimal(cleaned) if cleaned else None
    except:
        return None

def extract_plan_type(plan_name):
    """Extract network type from plan name."""
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    return match.group(1) if match else None

def load_data(db_config):
    """Load all data into PostgreSQL."""
    
    print("Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    try:
        # Load plan-county mappings
        print("\nLoading plan-county mappings...")
        with open(PLAN_COUNTY_MAPPINGS) as f:
            plan_county_mappings = json.load(f)
        
        # Load scraped plans
        print("Loading scraped plans...")
        scraped_plans = {}
        for state_dir in SCRAPED_DATA_DIR.iterdir():
            if not state_dir.is_dir():
                continue
            for plan_file in state_dir.glob('*.json'):
                try:
                    with open(plan_file) as f:
                        plan = json.load(f)
                    plan_id = plan.get('plan_id', '')
                    if plan_id:
                        scraped_plans[plan_id] = plan
                except Exception as e:
                    print(f"  ⚠️  Error loading {plan_file}: {e}")
        
        print(f"  Loaded {len(scraped_plans):,} scraped plans")
        
        # Load ZIP mappings
        print("Loading ZIP mappings...")
        with open(UNIFIED_ZIP_FILE) as f:
            unified_zip = json.load(f)
        
        # Insert states
        print("\nInserting states...")
        state_counts = {}
        for plan_id, mapping in plan_county_mappings.items():
            state_abbrev = mapping['state_abbrev']
            state_counts[state_abbrev] = state_counts.get(state_abbrev, 0) + 1
        
        for abbrev, count in state_counts.items():
            state_name = mapping.get('state', abbrev)
            cur.execute(
                "INSERT INTO states (abbrev, name, plan_count) VALUES (%s, %s, %s) ON CONFLICT (abbrev) DO UPDATE SET plan_count = EXCLUDED.plan_count",
                (abbrev, state_name, count)
            )
        print(f"  Inserted {len(state_counts)} states")
        
        # Insert plans
        print("\nInserting plans...")
        plan_count = 0
        for plan_id, plan in scraped_plans.items():
            cms_mapping = plan_county_mappings.get(plan_id, {})
            state_abbrev = cms_mapping.get('state_abbrev', '')
            
            if not state_abbrev:
                continue
            
            plan_info = plan.get('plan_info', {})
            plan_name = plan_info.get('name', '')
            premiums = plan.get('premiums', {})
            deductibles = plan.get('deductibles', {})
            out_of_pocket = plan.get('out_of_pocket', {})
            
            # Get category
            cms_category = cms_mapping.get('category', '')
            category = CMS_CATEGORY_TO_SUNFIRE.get(cms_category, 'MAPD')
            
            # Parse numeric values
            monthly_premium_display = premiums.get('Total monthly premium', '')
            monthly_premium_value = parse_currency(monthly_premium_display)
            
            health_deductible_display = deductibles.get('Health deductible', '')
            health_deductible_value = parse_currency(health_deductible_display)
            
            drug_deductible_display = deductibles.get('Drug deductible', '')
            drug_deductible_value = parse_currency(drug_deductible_display)
            
            max_oop_display = out_of_pocket.get('Maximum out-of-pocket', '')
            max_oop_value = parse_currency(max_oop_display)
            
            cur.execute("""
                INSERT INTO plans (
                    plan_id, state_abbrev, plan_name, plan_type, category,
                    monthly_premium_display, monthly_premium_value,
                    health_deductible_display, health_deductible_value,
                    drug_deductible_display, drug_deductible_value,
                    max_out_of_pocket_display, max_out_of_pocket_value,
                    plan_info, premiums, deductibles, out_of_pocket,
                    benefits, drug_coverage, extra_benefits
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (plan_id) DO NOTHING
            """, (
                plan_id, state_abbrev, plan_name, extract_plan_type(plan_name), category,
                monthly_premium_display, monthly_premium_value,
                health_deductible_display, health_deductible_value,
                drug_deductible_display, drug_deductible_value,
                max_oop_display, max_oop_value,
                json.dumps(plan_info), json.dumps(premiums),
                json.dumps(deductibles), json.dumps(out_of_pocket),
                json.dumps(plan.get('benefits', {})),
                json.dumps(plan.get('drug_coverage', {})),
                json.dumps(plan.get('extra_benefits', []))
            ))
            plan_count += 1
            
            if plan_count % 500 == 0:
                print(f"  Inserted {plan_count} plans...")
        
        print(f"  ✅ Inserted {plan_count} plans")
        
        # Insert counties and plan-county relationships
        print("\nInserting counties and plan-county mappings...")
        county_map = {}  # (state, county_name) -> county_id
        county_count = 0
        
        for plan_id, mapping in plan_county_mappings.items():
            # Skip plans that weren't scraped
            if plan_id not in scraped_plans:
                continue
            
            state_abbrev = mapping['state_abbrev']
            all_counties = mapping['all_counties']
            counties_list = mapping['counties']
            
            if all_counties:
                # This plan serves all counties in the state
                # We'll handle this specially in plan_counties table
                pass
            
            for county_name in counties_list:
                key = (state_abbrev, county_name)
                if key not in county_map:
                    # Insert county (we don't have FIPS here, will add later from ZIP data)
                    cur.execute("""
                        INSERT INTO counties (state_abbrev, county_name, fips)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (state_abbrev, county_name) DO NOTHING
                        RETURNING id
                    """, (state_abbrev, county_name, '00000'))
                    
                    result = cur.fetchone()
                    if result:
                        county_map[key] = result[0]
                        county_count += 1
                    else:
                        # County already exists, fetch its ID
                        cur.execute(
                            "SELECT id FROM counties WHERE state_abbrev = %s AND county_name = %s",
                            (state_abbrev, county_name)
                        )
                        county_map[key] = cur.fetchone()[0]
                
                # Insert plan-county relationship
                county_id = county_map[key]
                cur.execute("""
                    INSERT INTO plan_counties (plan_id, county_id, all_counties)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plan_id, county_id) DO NOTHING
                """, (plan_id, county_id, all_counties))
        
        print(f"  ✅ Inserted {county_count} counties")
        
        # Insert ZIP codes and ZIP-county relationships
        print("\nInserting ZIP codes...")
        zip_count = 0
        
        for zip_code, zip_info in unified_zip.items():
            multi_county = zip_info.get('multi_county', False)
            multi_state = zip_info.get('multi_state', False)
            states_list = zip_info.get('states', [])
            primary_state = zip_info.get('primary_state')
            
            cur.execute("""
                INSERT INTO zip_codes (zip_code, multi_county, multi_state, primary_state, states)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (zip_code) DO NOTHING
            """, (zip_code, multi_county, multi_state, primary_state, states_list))
            
            # Insert ZIP-county relationships
            for county in zip_info.get('counties', []):
                state_abbrev = county['state']
                county_name = county['name']
                fips = county['fips']
                ratio = county.get('ratio', 1.0)
                
                # Get or create county
                key = (state_abbrev, county_name)
                if key not in county_map:
                    cur.execute("""
                        INSERT INTO counties (state_abbrev, county_name, fips)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (state_abbrev, county_name) DO UPDATE SET fips = EXCLUDED.fips
                        RETURNING id
                    """, (state_abbrev, county_name, fips))
                    
                    result = cur.fetchone()
                    if result:
                        county_map[key] = result[0]
                    else:
                        cur.execute(
                            "SELECT id FROM counties WHERE state_abbrev = %s AND county_name = %s",
                            (state_abbrev, county_name)
                        )
                        county_map[key] = cur.fetchone()[0]
                
                county_id = county_map[key]
                
                cur.execute("""
                    INSERT INTO zip_counties (zip_code, county_id, state_abbrev, ratio)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (zip_code, county_id) DO NOTHING
                """, (zip_code, county_id, state_abbrev, ratio))
            
            zip_count += 1
            if zip_count % 5000 == 0:
                print(f"  Inserted {zip_count} ZIP codes...")
        
        print(f"  ✅ Inserted {zip_count} ZIP codes")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*80)
        print("DATABASE LOAD COMPLETE ✅")
        print("="*80)
        print(f"  States: {len(state_counts)}")
        print(f"  Plans: {plan_count}")
        print(f"  Counties: {len(county_map)}")
        print(f"  ZIP Codes: {zip_count}")
        print("="*80)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 load_data.py <db_connection_string>")
        print("Example: python3 load_data.py 'host=localhost dbname=medicare user=postgres password=xxx'")
        sys.exit(1)
    
    # Parse connection string
    conn_parts = {}
    for part in sys.argv[1].split():
        key, val = part.split('=', 1)
        conn_parts[key] = val
    
    load_data(conn_parts)
