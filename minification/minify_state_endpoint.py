#!/usr/bin/env python3
"""
Minify Medicare plan JSON files for a state with _minified.json suffix.
Creates files in static_api/medicare/zip_minified/ directory.

Usage: python3 minify_state_endpoint.py MD
"""

import json
import re
from pathlib import Path

# Load mappings
SCRIPT_DIR = Path(__file__).parent
with open(SCRIPT_DIR / 'key_mapping.json') as f:
    KEY_MAPPING = json.load(f)['mapping']

with open(SCRIPT_DIR / 'value_mapping.json') as f:
    value_data = json.load(f)
    VALUE_MAPPING = value_data['values']
    ORG_MAPPING = value_data['organizations']
    TYPE_MAPPING = value_data['plan_types']
    ADDR_MAPPING = value_data['addresses']
    NETWORK_TYPE_MAPPING = value_data['network_types']

# Reverse mappings for lookup
VALUE_REVERSE = {v: k for k, v in VALUE_MAPPING.items()}
ORG_REVERSE = {v: k for k, v in ORG_MAPPING.items()}
TYPE_REVERSE = {v: k for k, v in TYPE_MAPPING.items()}
ADDR_REVERSE = {v: k for k, v in ADDR_MAPPING.items()}
NETWORK_TYPE_REVERSE = {v: k for k, v in NETWORK_TYPE_MAPPING.items()}


def extract_network_type(plan_name):
    """Extract network type (HMO, PPO, PDP, etc.) from plan name."""
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    if match:
        network_type = match.group(1)
        # Return minified code if available, otherwise raw value
        return NETWORK_TYPE_REVERSE.get(network_type, network_type)
    return None


def minify_key(key):
    """Convert a key to its minified form."""
    return KEY_MAPPING.get(key, key)


def minify_value(value):
    """Convert a value to its minified form if it exists in mappings."""
    if not isinstance(value, str):
        return value
    
    # Check value mappings
    if value in VALUE_REVERSE:
        return VALUE_REVERSE[value]
    
    # Check organization mappings
    if value in ORG_REVERSE:
        return ORG_REVERSE[value]
    
    # Check type mappings
    if value in TYPE_REVERSE:
        return TYPE_REVERSE[value]
    
    # Check address mappings
    if value in ADDR_REVERSE:
        return ADDR_REVERSE[value]
    
    return value


def minify_object(obj):
    """Recursively minify an object."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            min_key = minify_key(key)
            min_value = minify_object(value)
            result[min_key] = min_value
        return result
    elif isinstance(obj, list):
        return [minify_object(item) for item in obj]
    elif isinstance(obj, str):
        return minify_value(obj)
    else:
        return obj


def minify_zip_file(input_path, output_path):
    """Minify a ZIP JSON file."""
    with open(input_path) as f:
        data = json.load(f)
    
    # Minify the structure
    minified = {
        'z': data['zip_code'],
        'mc': data.get('multi_county', False),
        'ms': data.get('multi_state', False),
        's': data.get('states', []),
        'ps': data.get('primary_state'),
        'c': [],  # counties
        'p': [],  # plans
        'pc': data.get('plan_count', 0)
    }
    
    # Minify counties
    for county in data.get('counties', []):
        minified['c'].append({
            'f': county.get('fips'),
            'n': county.get('name'),
            's': county.get('state'),
            'r': county.get('ratio'),
            'pa': county.get('plans_available', True),
            'pc': county.get('plan_count', 0)
        })
    
    # Minify plans
    for plan in data.get('plans', []):
        min_plan = minify_object(plan)
        
        # Extract and add network type (pt = plan_type like HMO, PPO, PDP)
        plan_name = plan.get('plan_info', {}).get('name', '')
        network_type = extract_network_type(plan_name)
        if network_type:
            min_plan['pt'] = network_type
        
        minified['p'].append(min_plan)
    
    # Write minified output (compact JSON)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(minified, f, separators=(',', ':'))
    
    return input_path.stat().st_size, output_path.stat().st_size


def get_state_zips(state):
    """Get list of ZIP codes for a state by scanning ZIP files."""
    zip_dir = Path('../static_api/medicare/zip')
    state_zips = []
    
    print(f"  Scanning ZIP files in {zip_dir}...")
    
    for zip_file in zip_dir.glob('*.json'):
        try:
            with open(zip_file) as f:
                data = json.load(f)
                # Check if this state is in the states list
                if state in data.get('states', []) or state == data.get('primary_state'):
                    state_zips.append(zip_file.stem)
        except Exception as e:
            continue
    
    return sorted(state_zips)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python minify_state_endpoint.py <state_abbrev>")
        print("Example: python minify_state_endpoint.py MD")
        sys.exit(1)
    
    state = sys.argv[1].upper()
    
    # Input/output directories
    input_dir = Path('../static_api/medicare/zip')
    output_dir = Path('../static_api/medicare/zip_minified')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get ZIP codes for this state
    print(f"Finding ZIP codes for {state}...")
    state_zips = get_state_zips(state)
    
    if not state_zips:
        print(f"Error: No ZIP codes found for {state}")
        sys.exit(1)
    
    print(f"Minifying {len(state_zips)} ZIP files for {state}...")
    
    total_original = 0
    total_minified = 0
    processed = 0
    
    for i, zip_code in enumerate(state_zips, 1):
        input_file = input_dir / f'{zip_code}.json'
        output_file = output_dir / f'{zip_code}_minified.json'
        
        if not input_file.exists():
            continue
        
        try:
            orig_size, min_size = minify_zip_file(input_file, output_file)
            total_original += orig_size
            total_minified += min_size
            processed += 1
            
            if i % 50 == 0:
                print(f"  Processed {i}/{len(state_zips)}...")
        except Exception as e:
            print(f"  Error processing {zip_code}: {e}")
    
    reduction = (1 - total_minified / total_original) * 100 if total_original > 0 else 0
    
    print(f"\nComplete!")
    print(f"  Processed: {processed} ZIP files")
    print(f"  Original size: {total_original / 1024:.1f} KB")
    print(f"  Minified size: {total_minified / 1024:.1f} KB")
    print(f"  Reduction: {reduction:.1f}%")
    print(f"\nOutput directory: {output_dir}")
    
    # Copy mapping files to the minified directory
    import shutil
    mapping_dir = output_dir.parent / 'mappings'
    mapping_dir.mkdir(exist_ok=True)
    shutil.copy(SCRIPT_DIR / 'key_mapping.json', mapping_dir)
    shutil.copy(SCRIPT_DIR / 'value_mapping.json', mapping_dir)
    print(f"Mapping files copied to {mapping_dir}")
    
    # Show example endpoint
    if state_zips:
        example_zip = state_zips[0]
        print(f"\nExample endpoint:")
        print(f"  https://medicare.purlpal-api.com/medicare/zip_minified/{example_zip}_minified.json")


if __name__ == '__main__':
    main()
