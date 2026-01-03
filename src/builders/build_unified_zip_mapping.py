#!/usr/bin/env python3
"""
Build a unified ZIP to FIPS (county) mapping for all US ZIPs.
This enables ZIP-first lookups without requiring state.

Output: unified_zip_to_fips.json
Structure:
{
    "03462": {
        "counties": [
            {"fips": "33005", "name": "Cheshire County", "state": "NH", "ratio": 1.0}
        ],
        "multi_county": false,
        "multi_state": false,
        "primary_state": "NH"
    }
}
"""
import json
import os
from collections import defaultdict

# Territories to skip (focus on proper states)
TERRITORIES = {'AS', 'GU', 'MP', 'PR', 'VI'}

# US States only
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 
    'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 
    'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 
    'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}

def build_unified_mapping():
    print("="*80)
    print("Building Unified ZIP to FIPS Mapping")
    print("="*80)
    print()
    
    unified = {}
    zip_county_dir = 'zip_county_data'
    
    # Process each state file
    for filename in sorted(os.listdir(zip_county_dir)):
        if not filename.endswith('_zip_county.json'):
            continue
        
        state = filename.replace('_zip_county.json', '')
        
        # Skip territories
        if state in TERRITORIES:
            print(f"  Skipping territory: {state}")
            continue
        
        filepath = os.path.join(zip_county_dir, filename)
        with open(filepath) as f:
            state_data = json.load(f)
        
        for entry in state_data:
            zip_code = entry['zip']
            
            if zip_code not in unified:
                unified[zip_code] = {
                    'counties': [],
                    'states': set(),
                    'multi_county': False,
                    'multi_state': False
                }
            
            # Add counties from this state
            for county in entry['counties']:
                county_entry = {
                    'fips': county['fips'],
                    'name': county.get('name', ''),
                    'state': state,
                    'ratio': county.get('ratio', 1.0)
                }
                unified[zip_code]['counties'].append(county_entry)
                unified[zip_code]['states'].add(state)
        
        print(f"  Processed {state}: {len(state_data)} ZIPs")
    
    # Finalize entries
    multi_state_count = 0
    multi_county_count = 0
    
    for zip_code, data in unified.items():
        states = data['states']
        data['multi_state'] = len(states) > 1
        data['multi_county'] = len(data['counties']) > 1
        data['primary_state'] = sorted(states)[0] if states else None
        data['states'] = sorted(states)  # Convert set to sorted list
        
        if data['multi_state']:
            multi_state_count += 1
        if data['multi_county']:
            multi_county_count += 1
        
        # Sort counties by ratio (highest first)
        data['counties'] = sorted(data['counties'], key=lambda x: -x['ratio'])
    
    # Save
    with open('unified_zip_to_fips.json', 'w') as f:
        json.dump(unified, f, indent=2)
    
    print()
    print("="*80)
    print(f"COMPLETE!")
    print(f"  Total ZIPs: {len(unified)}")
    print(f"  Multi-county ZIPs: {multi_county_count}")
    print(f"  Multi-state ZIPs: {multi_state_count}")
    print(f"  Output: unified_zip_to_fips.json")
    print("="*80)
    
    return unified

if __name__ == '__main__':
    build_unified_mapping()
