#!/usr/bin/env python3
"""
Universal Flask API for Medicare plan lookup
Supports both county-based states (NH, VT, etc.) and region-based (DC, Guam)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global data structures
STATE_DATA = {}

def load_state_data():
    """Load all available state API data at startup"""
    global STATE_DATA
    
    api_dir = Path('mock_api')
    
    for state_dir in api_dir.iterdir():
        if not state_dir.is_dir():
            continue
        
        state_abbrev = state_dir.name
        info_file = state_dir / 'api_info.json'
        
        if not info_file.exists():
            continue
        
        # Load state info
        with open(info_file) as f:
            info = json.load(f)
        
        state_type = info.get('type', 'county')  # 'county' or 'region'
        
        STATE_DATA[state_abbrev] = {
            'info': info,
            'type': state_type,
            'zip_mapping': {},
            'data_cache': {}
        }
        
        # Load ZIP mapping
        if state_type == 'region':
            # Region-based (DC, Guam) - load zip_to_plans
            zip_file = state_dir / 'zip_to_plans.json'
            if zip_file.exists():
                with open(zip_file) as f:
                    STATE_DATA[state_abbrev]['zip_mapping'] = json.load(f)
            
            # Load region cache
            region_file = state_dir / 'region_cache.json'
            if region_file.exists():
                with open(region_file) as f:
                    STATE_DATA[state_abbrev]['data_cache'] = json.load(f)
        
        else:
            # County-based - load zip_to_county and county caches
            zip_file = state_dir / 'zip_to_county_multi.json'
            if zip_file.exists():
                with open(zip_file) as f:
                    zip_data = json.load(f)
                    for entry in zip_data:
                        STATE_DATA[state_abbrev]['zip_mapping'][entry['zip']] = entry
            
            # Load county caches
            county_dir = state_dir / 'counties'
            if county_dir.exists():
                for county_file in county_dir.glob('*.json'):
                    county_name = county_file.stem
                    with open(county_file) as f:
                        STATE_DATA[state_abbrev]['data_cache'][county_name] = json.load(f)
        
        print(f"✅ Loaded {state_abbrev}: {info['state']} ({state_type}) - {info['plan_count']} plans")

@app.route('/api/<state>/<zip_code>', methods=['GET'])
def get_plans_by_zip(state, zip_code):
    """
    Get all available plans for a ZIP code in a state
    Supports both county-based and region-based states
    """
    state = state.upper()
    
    # Validate state
    if state not in STATE_DATA:
        return jsonify({
            'error': 'State not available',
            'state': state,
            'available_states': list(STATE_DATA.keys())
        }), 404
    
    state_info = STATE_DATA[state]
    include_details = request.args.get('include_details', 'true').lower() == 'true'
    
    # Region-based state (DC, Guam)
    if state_info['type'] == 'region':
        if zip_code not in state_info['zip_mapping']:
            return jsonify({
                'error': 'ZIP code not found in region',
                'state': state,
                'zip_code': zip_code
            }), 404
        
        region_data = state_info['data_cache']
        plans = region_data['plans']
        
        if not include_details:
            plans = [
                {
                    'contract_plan_segment_id': p['summary']['contract_plan_segment_id'],
                    'plan_name': p['summary']['plan_name'],
                    'plan_type': p['summary']['plan_type'],
                    'organization': p['summary']['organization'],
                    'has_scraped_details': p['has_scraped_details']
                }
                for p in plans
            ]
        
        return jsonify({
            'zip_code': zip_code,
            'state': state_info['info']['state'],
            'type': 'region',
            'plan_count': len(plans),
            'scraped_details_available': region_data['scraped_details_available'],
            'plans': plans
        })
    
    # County-based state
    else:
        if zip_code not in state_info['zip_mapping']:
            return jsonify({
                'error': 'ZIP code not found',
                'state': state,
                'zip_code': zip_code
            }), 404
        
        zip_info = state_info['zip_mapping'][zip_code]
        
        response = {
            'zip_code': zip_code,
            'state': state_info['info']['state'],
            'type': 'county',
            'multi_county': zip_info['multi_county'],
            'primary_county': zip_info['primary_county']['name'],
            'counties': {}
        }
        
        # Load plans for each county
        for county_info in zip_info['counties']:
            county_name = county_info['name']
            
            if county_name not in state_info['data_cache']:
                continue
            
            county_data = state_info['data_cache'][county_name]
            plans = county_data['plans']
            
            if not include_details:
                plans = [
                    {
                        'contract_plan_segment_id': p['summary']['contract_plan_segment_id'],
                        'plan_name': p['summary']['plan_name'],
                        'plan_type': p['summary']['plan_type'],
                        'organization': p['summary']['organization'],
                        'has_scraped_details': p['has_scraped_details']
                    }
                    for p in plans
                ]
            
            response['counties'][county_name] = {
                'fips': county_info['fips'],
                'percentage': county_info.get('percentage'),
                'plan_count': len(plans),
                'scraped_details_available': county_data['scraped_details_available'],
                'plans': plans
            }
        
        return jsonify(response)

@app.route('/api/<state>/plan/<plan_id>', methods=['GET'])
def get_plan_detail(state, plan_id):
    """Get details for a specific plan"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({
            'error': 'State not available',
            'state': state
        }), 404
    
    state_info = STATE_DATA[state]
    
    # Search through caches
    if state_info['type'] == 'region':
        # Region-based - single cache
        for plan in state_info['data_cache']['plans']:
            if plan['summary']['contract_plan_segment_id'] == plan_id:
                return jsonify({
                    'plan_id': plan_id,
                    'state': state_info['info']['state'],
                    'type': 'region',
                    'summary': plan['summary'],
                    'details': plan['details'],
                    'has_scraped_details': plan['has_scraped_details']
                })
    else:
        # County-based - search all counties
        for county_name, county_data in state_info['data_cache'].items():
            for plan in county_data['plans']:
                if plan['summary']['contract_plan_segment_id'] == plan_id:
                    return jsonify({
                        'plan_id': plan_id,
                        'state': state_info['info']['state'],
                        'county': county_name,
                        'summary': plan['summary'],
                        'details': plan['details'],
                        'has_scraped_details': plan['has_scraped_details']
                    })
    
    return jsonify({
        'error': 'Plan not found',
        'plan_id': plan_id,
        'state': state
    }), 404

@app.route('/api/<state>/plans', methods=['GET'])
def list_all_plans(state):
    """List all plans for a state"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({
            'error': 'State not available',
            'state': state
        }), 404
    
    state_info = STATE_DATA[state]
    include_details = request.args.get('include_details', 'false').lower() == 'true'
    
    all_plans = []
    
    if state_info['type'] == 'region':
        all_plans = state_info['data_cache']['plans']
    else:
        # Aggregate from all counties
        for county_data in state_info['data_cache'].values():
            all_plans.extend(county_data['plans'])
    
    if not include_details:
        all_plans = [
            {
                'contract_plan_segment_id': p['summary']['contract_plan_segment_id'],
                'plan_name': p['summary']['plan_name'],
                'plan_type': p['summary']['plan_type'],
                'organization': p['summary']['organization']
            }
            for p in all_plans
        ]
    
    return jsonify({
        'state': state_info['info']['state'],
        'plan_count': len(all_plans),
        'plans': all_plans
    })

@app.route('/api/states', methods=['GET'])
def list_states():
    """List all available states"""
    states = []
    for abbrev, data in STATE_DATA.items():
        states.append({
            'abbrev': abbrev,
            'name': data['info']['state'],
            'type': data['type'],
            'plan_count': data['info']['plan_count']
        })
    
    return jsonify({
        'state_count': len(states),
        'states': sorted(states, key=lambda x: x['name'])
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'states_loaded': len(STATE_DATA),
        'states': list(STATE_DATA.keys())
    })

if __name__ == '__main__':
    print("=" * 80)
    print("Medicare Plan API Server v2 - Universal")
    print("=" * 80)
    
    load_state_data()
    
    print("\n" + "=" * 80)
    print("Available States:")
    for abbrev, data in STATE_DATA.items():
        print(f"  {abbrev}: {data['info']['state']} ({data['type']}) - {data['info']['plan_count']} plans")
    
    print("\nEndpoints:")
    print("  GET /api/<state>/<zip_code>           - Get plans for ZIP code")
    print("  GET /api/<state>/plan/<plan_id>       - Get specific plan details")
    print("  GET /api/<state>/plans                - List all state plans")
    print("  GET /api/states                       - List all available states")
    print("  GET /health                           - Health check")
    
    print("\nExamples:")
    print("  curl http://localhost:5000/api/DC/20001")
    print("  curl http://localhost:5000/api/GU/96910")
    print("  curl http://localhost:5000/api/NH/03462")
    print("  curl http://localhost:5000/api/DC/plans")
    print("  curl http://localhost:5000/api/states")
    
    print("\n" + "=" * 80)
    
    app.run(debug=True, port=5000)
