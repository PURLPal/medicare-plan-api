#!/usr/bin/env python3
"""
Expand minified Medicare plan JSON files back to full format.
Used for testing and verification.
"""

import json
from pathlib import Path

# Load mappings
with open(Path(__file__).parent / 'key_mapping.json') as f:
    key_data = json.load(f)
    KEY_MAPPING = key_data['mapping']
    # Build reverse mapping
    KEY_REVERSE = {v: k for k, v in KEY_MAPPING.items()}

with open(Path(__file__).parent / 'value_mapping.json') as f:
    value_data = json.load(f)
    VALUE_MAPPING = value_data['values']
    ORG_MAPPING = value_data['organizations']
    TYPE_MAPPING = value_data['plan_types']
    ADDR_MAPPING = value_data.get('addresses', {})
    NETWORK_TYPE_MAPPING = value_data.get('network_types', {})

# Top-level key reverse mapping (special cases)
TOP_LEVEL_REVERSE = {
    'z': 'zip_code',
    'mc': 'multi_county',
    'ms': 'multi_state',
    's': 'states',
    'ps': 'primary_state',
    'c': 'counties',
    'p': 'plans',
    'pc': 'plan_count'
}

COUNTY_REVERSE = {
    'f': 'fips',
    'n': 'name',
    's': 'state',
    'r': 'ratio',
    'pa': 'plans_available',
    'pc': 'plan_count'
}


def expand_value(val):
    """Expand a minified value back to full form."""
    if not isinstance(val, str):
        return val
    
    # Check value mappings
    if val in VALUE_MAPPING:
        return VALUE_MAPPING[val]
    
    # Check organization mappings
    if val in ORG_MAPPING:
        return ORG_MAPPING[val]
    
    # Check type mappings
    if val in TYPE_MAPPING:
        return TYPE_MAPPING[val]
    
    # Check address mappings
    if val in ADDR_MAPPING:
        return ADDR_MAPPING[val]
    
    # Check network type mappings
    if val in NETWORK_TYPE_MAPPING:
        return NETWORK_TYPE_MAPPING[val]
    
    return val


def expand_key(key):
    """Expand a minified key back to full form."""
    # Special case for pt -> plan_type (not in original data, added during minification)
    if key == 'pt':
        return 'plan_type'
    return KEY_REVERSE.get(key, key)


def expand_object(obj):
    """Recursively expand a minified object."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            exp_key = expand_key(key)
            exp_value = expand_object(value)
            result[exp_key] = exp_value
        return result
    elif isinstance(obj, list):
        return [expand_object(item) for item in obj]
    elif isinstance(obj, str):
        return expand_value(obj)
    else:
        return obj


def expand_zip_file(input_path, output_path=None):
    """Expand a minified ZIP JSON file back to full format."""
    with open(input_path) as f:
        data = json.load(f)
    
    # Expand top-level structure
    expanded = {
        'zip_code': data.get('z'),
        'multi_county': data.get('mc', False),
        'multi_state': data.get('ms', False),
        'states': data.get('s', []),
        'primary_state': data.get('ps'),
        'counties': [],
        'plans': [],
        'plan_count': data.get('pc', 0)
    }
    
    # Expand counties
    for county in data.get('c', []):
        expanded['counties'].append({
            'fips': county.get('f'),
            'name': county.get('n'),
            'state': county.get('s'),
            'ratio': county.get('r'),
            'plans_available': county.get('pa', True),
            'plan_count': county.get('pc', 0)
        })
    
    # Expand plans
    for plan in data.get('p', []):
        exp_plan = expand_object(plan)
        expanded['plans'].append(exp_plan)
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(expanded, f, indent=2)
    
    return expanded


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python expand_plans.py <minified_file.json> [output_file.json]")
        print("Example: python expand_plans.py ../static_api_minified/medicare/zip/03462.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    expanded = expand_zip_file(input_file, output_file)
    
    if output_file:
        print(f"Expanded to: {output_file}")
    else:
        # Print to stdout
        print(json.dumps(expanded, indent=2))


if __name__ == '__main__':
    main()
