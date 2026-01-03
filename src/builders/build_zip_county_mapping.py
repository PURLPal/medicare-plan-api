#!/usr/bin/env python3
"""
Build ZIP to County mapping from HUD USPS Crosswalk file.
Handles multi-county ZIPs by collecting all counties for each ZIP.

Output: JSON files per state with ZIP -> counties mapping
"""
import json
import openpyxl
from collections import defaultdict
from pathlib import Path

# State FIPS codes to state names/abbreviations
STATE_FIPS = {
    '01': ('Alabama', 'AL'), '02': ('Alaska', 'AK'), '04': ('Arizona', 'AZ'),
    '05': ('Arkansas', 'AR'), '06': ('California', 'CA'), '08': ('Colorado', 'CO'),
    '09': ('Connecticut', 'CT'), '10': ('Delaware', 'DE'), '11': ('District of Columbia', 'DC'),
    '12': ('Florida', 'FL'), '13': ('Georgia', 'GA'), '15': ('Hawaii', 'HI'),
    '16': ('Idaho', 'ID'), '17': ('Illinois', 'IL'), '18': ('Indiana', 'IN'),
    '19': ('Iowa', 'IA'), '20': ('Kansas', 'KS'), '21': ('Kentucky', 'KY'),
    '22': ('Louisiana', 'LA'), '23': ('Maine', 'ME'), '24': ('Maryland', 'MD'),
    '25': ('Massachusetts', 'MA'), '26': ('Michigan', 'MI'), '27': ('Minnesota', 'MN'),
    '28': ('Mississippi', 'MS'), '29': ('Missouri', 'MO'), '30': ('Montana', 'MT'),
    '31': ('Nebraska', 'NE'), '32': ('Nevada', 'NV'), '33': ('New Hampshire', 'NH'),
    '34': ('New Jersey', 'NJ'), '35': ('New Mexico', 'NM'), '36': ('New York', 'NY'),
    '37': ('North Carolina', 'NC'), '38': ('North Dakota', 'ND'), '39': ('Ohio', 'OH'),
    '40': ('Oklahoma', 'OK'), '41': ('Oregon', 'OR'), '42': ('Pennsylvania', 'PA'),
    '44': ('Rhode Island', 'RI'), '45': ('South Carolina', 'SC'), '46': ('South Dakota', 'SD'),
    '47': ('Tennessee', 'TN'), '48': ('Texas', 'TX'), '49': ('Utah', 'UT'),
    '50': ('Vermont', 'VT'), '51': ('Virginia', 'VA'), '53': ('Washington', 'WA'),
    '54': ('West Virginia', 'WV'), '55': ('Wisconsin', 'WI'), '56': ('Wyoming', 'WY'),
    '72': ('Puerto Rico', 'PR'), '78': ('Virgin Islands', 'VI'), '66': ('Guam', 'GU'),
    '69': ('Northern Mariana Islands', 'MP'), '60': ('American Samoa', 'AS')
}

# We need county names - let's load from CY2026 data
def load_county_names_from_csv():
    """Load county FIPS to name mapping from CY2026 data"""
    import csv
    
    county_fips_to_name = {}
    csv_path = 'downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv'
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # The CSV has county names but not FIPS directly
            # We'll need to build this differently
            pass
    
    return county_fips_to_name

def build_zip_county_mapping(xlsx_path, output_dir='zip_county_data'):
    """
    Parse HUD ZIP-County crosswalk and build state-level mappings.
    
    Structure per ZIP:
    {
        "zip": "03256",
        "state": "NH",
        "multi_county": true,
        "county_count": 2,
        "counties": [
            {"fips": "33001", "ratio": 0.985},
            {"fips": "33009", "ratio": 0.015}
        ],
        "primary_county": {"fips": "33001", "ratio": 0.985}
    }
    """
    print("="*80)
    print("Building ZIP to County Mapping from HUD Data")
    print("="*80)
    print()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load the Excel file
    print(f"Loading: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active
    
    # Structure: {state_fips: {zip: [{fips, ratio}, ...]}}
    state_zip_counties = defaultdict(lambda: defaultdict(list))
    
    # Track stats
    total_rows = 0
    multi_county_zips = set()
    
    print("Parsing rows...")
    
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):  # Skip header
        if i % 50000 == 0 and i > 0:
            print(f"  Processed {i:,} rows...")
        
        zip_code = str(row[0]).zfill(5) if row[0] else None
        county_fips = str(row[1]).zfill(5) if row[1] else None
        state_abbrev = row[3] if len(row) > 3 else None
        res_ratio = float(row[4]) if row[4] is not None else 0
        tot_ratio = float(row[7]) if len(row) > 7 and row[7] is not None else res_ratio
        
        if not zip_code or not county_fips:
            continue
        
        state_fips = county_fips[:2]
        
        # Add to state's ZIP mapping
        state_zip_counties[state_fips][zip_code].append({
            'fips': county_fips,
            'ratio': round(tot_ratio, 4)
        })
        
        total_rows += 1
    
    wb.close()
    print(f"  Total rows processed: {total_rows:,}")
    print()
    
    # Now build output files per state
    print("Building state files...")
    
    state_stats = {}
    
    for state_fips, zip_data in sorted(state_zip_counties.items()):
        if state_fips not in STATE_FIPS:
            print(f"  Skipping unknown state FIPS: {state_fips}")
            continue
        
        state_name, state_abbrev = STATE_FIPS[state_fips]
        
        # Build ZIP mapping list
        zip_mapping = []
        multi_count = 0
        
        for zip_code, counties in sorted(zip_data.items()):
            # Sort counties by ratio (highest first)
            counties_sorted = sorted(counties, key=lambda x: -x['ratio'])
            
            # Determine primary county
            primary = counties_sorted[0]
            is_multi = len(counties_sorted) > 1
            
            if is_multi:
                multi_count += 1
            
            zip_entry = {
                'zip': zip_code,
                'state': state_abbrev,
                'multi_county': is_multi,
                'county_count': len(counties_sorted),
                'counties': counties_sorted,
                'primary_county': primary
            }
            
            zip_mapping.append(zip_entry)
        
        # Save state file
        state_file = output_path / f"{state_abbrev}_zip_county.json"
        with open(state_file, 'w') as f:
            json.dump(zip_mapping, f, indent=2)
        
        state_stats[state_abbrev] = {
            'name': state_name,
            'zip_count': len(zip_mapping),
            'multi_county_zips': multi_count
        }
        
        print(f"  {state_abbrev}: {len(zip_mapping):,} ZIPs ({multi_count} multi-county)")
    
    # Save summary
    summary = {
        'total_states': len(state_stats),
        'total_zips': sum(s['zip_count'] for s in state_stats.values()),
        'states': state_stats
    }
    
    with open(output_path / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print()
    print("="*80)
    print(f"COMPLETE!")
    print(f"  States: {len(state_stats)}")
    print(f"  Total ZIPs: {summary['total_zips']:,}")
    print(f"  Output: {output_path}/")
    print("="*80)
    
    return state_stats

if __name__ == '__main__':
    xlsx_path = 'downloaded_data/ZIP_COUNTY_062025.xlsx'
    build_zip_county_mapping(xlsx_path)
