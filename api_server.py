#!/usr/bin/env python3
"""
Simple Flask API for Medicare plan lookup by ZIP code
"""

from flask import Flask, jsonify, request
from pathlib import Path
import json

app = Flask(__name__)

# Load ZIP to county mapping once at startup
ZIP_TO_COUNTY = {}
COUNTY_CACHES = {}

def load_data():
    """Load all data files at startup"""
    global ZIP_TO_COUNTY, COUNTY_CACHES

    # Load ZIP to county mapping
    zip_file = Path('mock_api/NH/zip_to_county_multi.json')
    with open(zip_file, 'r') as f:
        zip_data = json.load(f)
        for entry in zip_data:
            ZIP_TO_COUNTY[entry['zip']] = entry

    print(f"Loaded {len(ZIP_TO_COUNTY)} ZIP codes")

    # Pre-load all county caches for fast access
    county_dir = Path('mock_api/NH/counties')
    for county_file in county_dir.glob('*.json'):
        county_name = county_file.stem
        with open(county_file, 'r') as f:
            COUNTY_CACHES[county_name] = json.load(f)

    print(f"Loaded {len(COUNTY_CACHES)} county caches")

@app.route('/api/nh/<zip_code>', methods=['GET'])
def get_plans_by_zip(zip_code):
    """
    Get all available plans for a ZIP code
    Returns counties with their full plan details
    """
    # Validate ZIP
    if zip_code not in ZIP_TO_COUNTY:
        return jsonify({
            'error': 'ZIP code not found',
            'zip_code': zip_code
        }), 404

    zip_info = ZIP_TO_COUNTY[zip_code]

    # Get include_details parameter (default: true)
    include_details = request.args.get('include_details', 'true').lower() == 'true'

    # Build response with counties
    response = {
        'zip_code': zip_code,
        'multi_county': zip_info['multi_county'],
        'primary_county': zip_info['primary_county']['name'],
        'counties': {}
    }

    # Load plans for each county
    for county_info in zip_info['counties']:
        county_name = county_info['name']

        if county_name not in COUNTY_CACHES:
            continue

        county_data = COUNTY_CACHES[county_name]

        # Filter plans based on include_details parameter
        if include_details:
            # Include full details
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

    return jsonify(response)

@app.route('/api/nh/plan/<plan_id>', methods=['GET'])
def get_plan_detail(plan_id):
    """Get details for a specific plan"""
    # Search through county caches
    for county_name, county_data in COUNTY_CACHES.items():
        for plan in county_data['plans']:
            if plan['summary']['contract_plan_segment_id'] == plan_id:
                return jsonify({
                    'plan_id': plan_id,
                    'county': county_name,
                    'summary': plan['summary'],
                    'details': plan['details'],
                    'has_scraped_details': plan['has_scraped_details']
                })

    return jsonify({
        'error': 'Plan not found',
        'plan_id': plan_id
    }), 404

@app.route('/api/nh/counties', methods=['GET'])
def list_counties():
    """List all counties with plan counts"""
    counties = []
    for county_name, county_data in COUNTY_CACHES.items():
        counties.append({
            'name': county_name,
            'plan_count': county_data['plan_count'],
            'scraped_details_available': county_data['scraped_details_available']
        })

    return jsonify({
        'state': 'New Hampshire',
        'county_count': len(counties),
        'counties': sorted(counties, key=lambda x: x['name'])
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'zip_codes_loaded': len(ZIP_TO_COUNTY),
        'counties_loaded': len(COUNTY_CACHES)
    })

if __name__ == '__main__':
    print("=" * 80)
    print("Medicare Plan API Server")
    print("=" * 80)

    load_data()

    print("\nStarting server...")
    print("\nEndpoints:")
    print("  GET /api/nh/<zip_code>              - Get plans for ZIP code")
    print("  GET /api/nh/<zip_code>?include_details=false  - Summary only")
    print("  GET /api/nh/plan/<plan_id>          - Get specific plan details")
    print("  GET /api/nh/counties                - List all counties")
    print("  GET /health                         - Health check")
    print("\nExamples:")
    print("  curl http://localhost:5000/api/nh/03462")
    print("  curl http://localhost:5000/api/nh/03602")
    print("  curl 'http://localhost:5000/api/nh/03602?include_details=false'")
    print("  curl http://localhost:5000/api/nh/plan/S4802_075_0")
    print("\n" + "=" * 80)

    app.run(debug=True, port=5000)
