"""
AWS Lambda function for Medicare plan lookup
Optimized for Lambda with minimal dependencies
Supports: AK, NH, VT, WY
"""

import json
import os
from pathlib import Path

# State configurations
STATES = {
    'ak': {'name': 'Alaska', 'abbr': 'AK'},
    'nh': {'name': 'New Hampshire', 'abbr': 'NH'},
    'vt': {'name': 'Vermont', 'abbr': 'VT'},
    'wy': {'name': 'Wyoming', 'abbr': 'WY'}
}

# Global cache - persists across warm Lambda invocations
_ZIP_TO_COUNTY = {}  # {state: {zip: data}}
_COUNTY_CACHES = {}  # {state: {county: data}}
_LOADED = False

def load_data():
    """Load all data files for all states - called once per cold start"""
    global _ZIP_TO_COUNTY, _COUNTY_CACHES, _LOADED

    if _LOADED:
        return  # Already loaded

    # In Lambda, data files will be in /var/task/ or we'll bundle them
    base_path = Path(__file__).parent

    total_zips = 0
    total_counties = 0

    # Load data for each state
    for state_key, state_config in STATES.items():
        state_abbr = state_config['abbr']

        # Load ZIP to county mapping
        zip_file = base_path / f'mock_api/{state_abbr}/zip_to_county_multi.json'
        if zip_file.exists():
            with open(zip_file, 'r') as f:
                zip_data = json.load(f)
                _ZIP_TO_COUNTY[state_key] = {entry['zip']: entry for entry in zip_data}
                total_zips += len(zip_data)

        # Pre-load all county caches for this state
        county_dir = base_path / f'mock_api/{state_abbr}/counties'
        if county_dir.exists():
            _COUNTY_CACHES[state_key] = {}
            for county_file in county_dir.glob('*.json'):
                county_name = county_file.stem
                with open(county_file, 'r') as f:
                    _COUNTY_CACHES[state_key][county_name] = json.load(f)
                    total_counties += 1

    _LOADED = True
    print(f"Loaded {len(STATES)} states, {total_zips} ZIP codes, {total_counties} county caches")

def get_plans_by_zip(state_key, zip_code, include_details=True):
    """Get all available plans for a ZIP code in a specific state"""
    load_data()

    # Validate state
    if state_key not in STATES:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'State not found',
                'state': state_key,
                'available_states': list(STATES.keys())
            })
        }

    # Validate ZIP
    if state_key not in _ZIP_TO_COUNTY or zip_code not in _ZIP_TO_COUNTY[state_key]:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'ZIP code not found',
                'zip_code': zip_code,
                'state': state_key
            })
        }

    zip_info = _ZIP_TO_COUNTY[state_key][zip_code]

    # Build response with counties
    response = {
        'zip_code': zip_code,
        'state': STATES[state_key]['name'],
        'state_abbr': STATES[state_key]['abbr'],
        'multi_county': zip_info['multi_county'],
        'primary_county': zip_info['primary_county']['name'],
        'counties': {}
    }

    # Load plans for each county
    for county_info in zip_info['counties']:
        county_name = county_info['name']

        if state_key not in _COUNTY_CACHES or county_name not in _COUNTY_CACHES[state_key]:
            continue

        county_data = _COUNTY_CACHES[state_key][county_name]

        # Filter plans based on include_details parameter
        if include_details:
            plans = county_data['plans']
        else:
            # Summary only (faster response, smaller payload)
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

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }

def get_plan_detail(state_key, plan_id):
    """Get details for a specific plan in a state"""
    load_data()

    # Validate state
    if state_key not in STATES:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'State not found',
                'state': state_key
            })
        }

    # Search through county caches for this state
    if state_key in _COUNTY_CACHES:
        for county_name, county_data in _COUNTY_CACHES[state_key].items():
            for plan in county_data['plans']:
                if plan['summary']['contract_plan_segment_id'] == plan_id:
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'plan_id': plan_id,
                            'state': STATES[state_key]['name'],
                            'county': county_name,
                            'summary': plan['summary'],
                            'details': plan['details'],
                            'has_scraped_details': plan['has_scraped_details']
                        })
                    }

    return {
        'statusCode': 404,
        'body': json.dumps({
            'error': 'Plan not found',
            'plan_id': plan_id,
            'state': state_key
        })
    }

def list_counties(state_key):
    """List all counties with plan counts for a state"""
    load_data()

    # Validate state
    if state_key not in STATES:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'State not found',
                'state': state_key
            })
        }

    counties = []
    if state_key in _COUNTY_CACHES:
        for county_name, county_data in _COUNTY_CACHES[state_key].items():
            counties.append({
                'name': county_name,
                'plan_count': county_data['plan_count'],
                'scraped_details_available': county_data['scraped_details_available']
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'state': STATES[state_key]['name'],
            'state_abbr': STATES[state_key]['abbr'],
            'county_count': len(counties),
            'counties': sorted(counties, key=lambda x: x['name'])
        })
    }

def list_states():
    """List all available states"""
    load_data()

    states_info = []
    for state_key, state_config in STATES.items():
        zip_count = len(_ZIP_TO_COUNTY.get(state_key, {}))
        county_count = len(_COUNTY_CACHES.get(state_key, {}))

        states_info.append({
            'key': state_key,
            'name': state_config['name'],
            'abbr': state_config['abbr'],
            'zip_codes': zip_count,
            'counties': county_count
        })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'states': sorted(states_info, key=lambda x: x['name']),
            'total_states': len(states_info)
        })
    }

def lambda_handler(event, context):
    """
    AWS Lambda handler

    Routes:
      GET /nh/{zip_code}              - Get plans for ZIP code
      GET /nh/{zip_code}?details=0    - Summary only
      GET /nh/plan/{plan_id}          - Get specific plan
      GET /nh/counties                - List all counties
    """

    # Handle both API Gateway and Function URL formats
    http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path = event.get('path') or event.get('rawPath', '')
    query_params = event.get('queryStringParameters') or {}

    # Parse path
    path_parts = [p for p in path.split('/') if p]

    # Response headers - NO CORS headers (Lambda Function URL handles CORS automatically)
    # Only set Content-Type - AWS adds CORS headers based on Function URL config
    headers = {
        'Content-Type': 'application/json'
    }

    # Handle OPTIONS for CORS preflight - Just return 200, AWS adds CORS headers
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    try:
        # Health check
        if not path_parts or path_parts == ['health']:
            load_data()
            total_zips = sum(len(zips) for zips in _ZIP_TO_COUNTY.values())
            total_counties = sum(len(counties) for counties in _COUNTY_CACHES.values())
            response = {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'healthy',
                    'states_loaded': len(STATES),
                    'zip_codes_loaded': total_zips,
                    'counties_loaded': total_counties
                })
            }

        # Route: GET /states
        elif path_parts == ['states']:
            response = list_states()

        # Route: GET /{state}/counties
        elif len(path_parts) >= 2 and path_parts[1] == 'counties':
            state_key = path_parts[0].lower()
            response = list_counties(state_key)

        # Route: GET /{state}/plan/{plan_id}
        elif len(path_parts) >= 3 and path_parts[1] == 'plan':
            state_key = path_parts[0].lower()
            plan_id = path_parts[2]
            response = get_plan_detail(state_key, plan_id)

        # Route: GET /{state}/{zip_code}
        elif len(path_parts) >= 2:
            state_key = path_parts[0].lower()
            zip_code = path_parts[1]
            include_details = query_params.get('details', '1') != '0'
            response = get_plans_by_zip(state_key, zip_code, include_details)

        else:
            response = {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not found',
                    'path': path,
                    'available_routes': [
                        'GET /states',
                        'GET /{state}/{zip_code}',
                        'GET /{state}/{zip_code}?details=0',
                        'GET /{state}/plan/{plan_id}',
                        'GET /{state}/counties',
                        'GET /health'
                    ],
                    'available_states': ['ak', 'nh', 'vt', 'wy']
                })
            }

        # Add CORS headers
        response['headers'] = headers
        return response

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

# For local testing
if __name__ == '__main__':
    print("Testing Lambda function locally...")

    tests = [
        {'name': 'List states', 'path': '/states'},
        {'name': 'Health check', 'path': '/health'},
        {'name': 'NH single-county ZIP', 'path': '/nh/03462', 'query': {'details': '0'}},
        {'name': 'NH multi-county ZIP', 'path': '/nh/03602', 'query': {}},
        {'name': 'VT ZIP', 'path': '/vt/05401', 'query': {'details': '0'}},
        {'name': 'WY ZIP', 'path': '/wy/82001', 'query': {'details': '0'}},
        {'name': 'AK ZIP', 'path': '/ak/99501', 'query': {'details': '0'}},
        {'name': 'NH plan detail', 'path': '/nh/plan/S4802_075_0', 'query': {}},
        {'name': 'NH counties', 'path': '/nh/counties', 'query': {}},
    ]

    for i, test in enumerate(tests, 1):
        event = {
            'httpMethod': 'GET',
            'path': test['path'],
            'queryStringParameters': test.get('query')
        }
        result = lambda_handler(event, None)
        body = json.loads(result['body']) if result['statusCode'] == 200 else None
        status = '✓' if result['statusCode'] == 200 else '✗'
        print(f"\nTest {i} - {test['name']}: {status} {result['statusCode']}")
        if body and 'counties' in body:
            if isinstance(body['counties'], dict):
                print(f"  Counties: {list(body['counties'].keys())}")
            else:
                print(f"  County count: {body.get('county_count', 0)}")
        elif body and 'states' in body:
            print(f"  States: {len(body['states'])}")
