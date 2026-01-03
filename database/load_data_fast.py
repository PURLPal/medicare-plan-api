#!/usr/bin/env python3
"""
Fast batch loader for Medicare data into PostgreSQL.
Uses executemany() for bulk inserts.
"""
import json
import psycopg2
import psycopg2.extras
from pathlib import Path
import re
from decimal import Decimal

# Data paths
SCRAPED_DATA_DIR = Path('scraped_data/json')
PLAN_COUNTY_MAPPINGS = Path('plan_county_mappings.json')
UNIFIED_ZIP_FILE = Path('unified_zip_to_fips.json')

CMS_CATEGORY_TO_SUNFIRE = {
    'MA-PD': 'MAPD',
    'SNP': 'MAPD',
    'MA': 'MA',
    'PDP': 'PD',
}

def parse_currency(value):
    if not value or value == 'N/A':
        return None
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return Decimal(cleaned) if cleaned else None
    except:
        return None

def extract_plan_type(plan_name):
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    return match.group(1) if match else None

def load_data(db_config):
    print("Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    try:
        # Load data
        print("\nLoading plan-county mappings...")
        with open(PLAN_COUNTY_MAPPINGS) as f:
            plan_county_mappings = json.load(f)
        
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
        
        print("Loading ZIP mappings...")
        with open(UNIFIED_ZIP_FILE) as f:
            unified_zip = json.load(f)
        
        # Insert states (batch) - get from both plan data and ZIP data
        print("\nInserting states...")
        state_counts = {}
        state_names = {}
        
        # From plan mappings
        for plan_id, mapping in plan_county_mappings.items():
            if plan_id in scraped_plans:
                state_abbrev = mapping['state_abbrev']
                state_counts[state_abbrev] = state_counts.get(state_abbrev, 0) + 1
                state_names[state_abbrev] = mapping.get('state', state_abbrev)
        
        # From ZIP data (to catch states without scraped plans)
        for zip_info in unified_zip.values():
            for county in zip_info.get('counties', []):
                state_abbrev = county['state']
                if state_abbrev not in state_counts:
                    state_counts[state_abbrev] = 0
                if state_abbrev not in state_names:
                    state_names[state_abbrev] = state_abbrev
        
        states_data = [(abbrev, state_names.get(abbrev, abbrev), state_counts.get(abbrev, 0)) 
                       for abbrev in state_counts.keys()]
        
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO states (abbrev, name, plan_count) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (abbrev) DO UPDATE SET plan_count = EXCLUDED.plan_count
        """, states_data, page_size=100)
        print(f"  Inserted {len(state_counts)} states")
        
        # Insert plans (batch)
        print("\nInserting plans...")
        plans_data = []
        
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
            
            cms_category = cms_mapping.get('category', '')
            category = CMS_CATEGORY_TO_SUNFIRE.get(cms_category, 'MAPD')
            
            monthly_premium_display = premiums.get('Total monthly premium', '')
            monthly_premium_value = parse_currency(monthly_premium_display)
            
            health_deductible_display = deductibles.get('Health deductible', '')
            health_deductible_value = parse_currency(health_deductible_display)
            
            drug_deductible_display = deductibles.get('Drug deductible', '')
            drug_deductible_value = parse_currency(drug_deductible_display)
            
            max_oop_display = out_of_pocket.get('Maximum out-of-pocket', '')
            max_oop_value = parse_currency(max_oop_display)
            
            plans_data.append((
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
        
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO plans (
                plan_id, state_abbrev, plan_name, plan_type, category,
                monthly_premium_display, monthly_premium_value,
                health_deductible_display, health_deductible_value,
                drug_deductible_display, drug_deductible_value,
                max_out_of_pocket_display, max_out_of_pocket_value,
                plan_info, premiums, deductibles, out_of_pocket,
                benefits, drug_coverage, extra_benefits
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (plan_id) DO NOTHING
        """, plans_data, page_size=500)
        
        print(f"  ✅ Inserted {len(plans_data)} plans")
        
        # Build county list from both sources
        print("\nCollecting all counties...")
        all_counties = set()
        
        # From plan mappings
        for plan_id, mapping in plan_county_mappings.items():
            if plan_id in scraped_plans:
                state_abbrev = mapping['state_abbrev']
                for county_name in mapping['counties']:
                    all_counties.add((state_abbrev, county_name, '00000'))
        
        # From ZIP data
        for zip_info in unified_zip.values():
            for county in zip_info.get('counties', []):
                all_counties.add((county['state'], county['name'], county['fips']))
        
        print(f"  Found {len(all_counties)} unique counties")
        
        # Batch insert counties
        print("Inserting counties...")
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO counties (state_abbrev, county_name, fips)
            VALUES (%s, %s, %s)
            ON CONFLICT (state_abbrev, county_name) DO UPDATE SET fips = EXCLUDED.fips
        """, list(all_counties), page_size=500)
        
        print(f"  ✅ Inserted {len(all_counties)} counties")
        
        # Fetch county IDs
        print("Fetching county IDs...")
        cur.execute("SELECT id, state_abbrev, county_name FROM counties")
        county_map = {(row[1], row[2]): row[0] for row in cur.fetchall()}
        
        # Build plan-county relationships
        print("Building plan-county relationships...")
        plan_county_data = []
        
        for plan_id, mapping in plan_county_mappings.items():
            if plan_id not in scraped_plans:
                continue
            
            state_abbrev = mapping['state_abbrev']
            all_counties_flag = mapping['all_counties']
            
            for county_name in mapping['counties']:
                key = (state_abbrev, county_name)
                if key in county_map:
                    plan_county_data.append((plan_id, county_map[key], all_counties_flag))
        
        print(f"  Inserting {len(plan_county_data)} plan-county relationships...")
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO plan_counties (plan_id, county_id, all_counties)
            VALUES (%s, %s, %s)
            ON CONFLICT (plan_id, county_id) DO NOTHING
        """, plan_county_data, page_size=1000)
        
        print(f"  ✅ Inserted plan-county relationships")
        
        # Insert ZIP codes
        print("\nInserting ZIP codes...")
        zip_data = [
            (zip_code, info.get('multi_county', False), info.get('multi_state', False),
             info.get('primary_state'), info.get('states', []))
            for zip_code, info in unified_zip.items()
        ]
        
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO zip_codes (zip_code, multi_county, multi_state, primary_state, states)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (zip_code) DO NOTHING
        """, zip_data, page_size=1000)
        
        print(f"  ✅ Inserted {len(zip_data)} ZIP codes")
        
        # Insert ZIP-county relationships
        print("Inserting ZIP-county relationships...")
        zip_county_data = []
        
        for zip_code, zip_info in unified_zip.items():
            for county in zip_info.get('counties', []):
                key = (county['state'], county['name'])
                if key in county_map:
                    zip_county_data.append((
                        zip_code,
                        county_map[key],
                        county['state'],
                        county.get('ratio', 1.0)
                    ))
        
        print(f"  Inserting {len(zip_county_data)} ZIP-county relationships...")
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO zip_counties (zip_code, county_id, state_abbrev, ratio)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (zip_code, county_id) DO NOTHING
        """, zip_county_data, page_size=2000)
        
        print(f"  ✅ Inserted ZIP-county relationships")
        
        # Commit
        conn.commit()
        
        print("\n" + "="*80)
        print("DATABASE LOAD COMPLETE ✅")
        print("="*80)
        print(f"  States: {len(state_counts)}")
        print(f"  Plans: {len(plans_data)}")
        print(f"  Counties: {len(all_counties)}")
        print(f"  ZIP Codes: {len(zip_data)}")
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
        print("Usage: python3 load_data_fast.py <db_connection_string>")
        sys.exit(1)
    
    conn_parts = {}
    for part in sys.argv[1].split():
        key, val = part.split('=', 1)
        conn_parts[key] = val
    
    load_data(conn_parts)
