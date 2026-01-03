#!/usr/bin/env python3
"""
Universal Flask API for Medicare plan lookup v3
Supports both county-based states and region-based states (DC, Guam, etc.)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import json

app = Flask(__name__)
CORS(app)

# Global data structures
STATE_DATA = {}
UNIFIED_ZIP_MAP = {}  # ZIP -> counties (for ZIP-only lookups)

def load_unified_zip_map():
    """Load unified ZIP to FIPS mapping for ZIP-only lookups"""
    global UNIFIED_ZIP_MAP
    
    unified_file = Path('unified_zip_to_fips.json')
    if unified_file.exists():
        with open(unified_file) as f:
            UNIFIED_ZIP_MAP = json.load(f)
        print(f"✅ Loaded unified ZIP mapping: {len(UNIFIED_ZIP_MAP)} ZIPs")
    else:
        print("⚠️ unified_zip_to_fips.json not found - ZIP-only endpoint disabled")

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
        
        with open(info_file) as f:
            info = json.load(f)
        
        state_type = info.get('type', 'county')
        
        STATE_DATA[state_abbrev] = {
            'info': info,
            'type': state_type,
            'zip_mapping': {},
            'zip_to_plans': {},
            'plans': {},  # plan_id -> plan data
            'counties': {}  # county_name -> [plan_ids]
        }
        
        # Load ZIP to plans mapping (fast lookup)
        zip_plans_file = state_dir / 'zip_to_plans.json'
        if zip_plans_file.exists():
            with open(zip_plans_file) as f:
                STATE_DATA[state_abbrev]['zip_to_plans'] = json.load(f)
        
        if state_type == 'region':
            # Region-based - load region cache
            region_file = state_dir / 'region_cache.json'
            if region_file.exists():
                with open(region_file) as f:
                    region_data = json.load(f)
                    for plan in region_data.get('plans', []):
                        # Handle both formats: plan_id at top level or in plan_info
                        if isinstance(plan, dict):
                            plan_id = plan.get('plan_id') or plan.get('plan_info', {}).get('id', '')
                            # Normalize plan_id format (H7464-010-0 -> H7464_010_0)
                            plan_id = plan_id.replace('-', '_')
                            if plan_id:
                                plan['plan_id'] = plan_id
                                STATE_DATA[state_abbrev]['plans'][plan_id] = plan
            
            # Load zip_to_region for validation
            zip_region_file = state_dir / 'zip_to_region.json'
            if zip_region_file.exists():
                with open(zip_region_file) as f:
                    STATE_DATA[state_abbrev]['zip_mapping'] = json.load(f)
        
        else:
            # County-based - load ZIP mapping and county caches
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
                        county_plans = json.load(f)
                        STATE_DATA[state_abbrev]['counties'][county_name] = []
                        for plan in county_plans:
                            if isinstance(plan, dict):
                                plan_id = plan.get('plan_id') or plan.get('plan_info', {}).get('id', '')
                                # Normalize plan_id format
                                plan_id = plan_id.replace('-', '_')
                                if plan_id:
                                    plan['plan_id'] = plan_id
                                    STATE_DATA[state_abbrev]['plans'][plan_id] = plan
                                    STATE_DATA[state_abbrev]['counties'][county_name].append(plan_id)
        
        plan_count = len(STATE_DATA[state_abbrev]['plans'])
        print(f"✅ Loaded {state_abbrev}: {info['state']} ({state_type}) - {plan_count} plans")

def get_plan_summary(plan):
    """Extract summary info from a plan"""
    plan_info = plan.get('plan_info', {})
    premiums = plan.get('premiums', {})
    moop = plan.get('maximum_out_of_pocket', {})
    
    return {
        'plan_id': plan.get('plan_id') or plan_info.get('id', ''),
        'plan_name': plan_info.get('name', ''),
        'monthly_premium': premiums.get('Monthly Premium', premiums.get('Part C Premium', '')),
        'drug_premium': premiums.get('Drug Premium', premiums.get('Part D Total Premium', '')),
        'max_out_of_pocket': moop.get('Maximum Out-of-Pocket', moop.get('In-Network', ''))
    }

@app.route('/api/<state>/<zip_code>', methods=['GET'])
def get_plans_by_zip(state, zip_code):
    """Get all available plans for a ZIP code"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({
            'error': 'State not available',
            'state': state,
            'available_states': sorted(STATE_DATA.keys())
        }), 404
    
    state_info = STATE_DATA[state]
    include_details = request.args.get('details', 'false').lower() == 'true'
    
    # Check if ZIP exists
    if state_info['type'] == 'region':
        if zip_code not in state_info['zip_mapping']:
            return jsonify({
                'error': 'ZIP code not found',
                'state': state,
                'zip_code': zip_code
            }), 404
        
        # All plans available for region
        plans = list(state_info['plans'].values())
        
        response = {
            'zip_code': zip_code,
            'state': state_info['info']['state'],
            'state_abbrev': state,
            'type': 'region',
            'plan_count': len(plans),
            'plans': [get_plan_summary(p) for p in plans] if not include_details else plans
        }
    
    else:
        # County-based
        if zip_code not in state_info['zip_mapping']:
            return jsonify({
                'error': 'ZIP code not found',
                'state': state,
                'zip_code': zip_code
            }), 404
        
        zip_info = state_info['zip_mapping'][zip_code]
        
        # Get plans from zip_to_plans or aggregate from counties
        plan_ids = state_info['zip_to_plans'].get(zip_code, [])
        
        if not plan_ids:
            # Fallback: aggregate from counties
            plan_ids = set()
            for county in zip_info['counties']:
                county_name = county.get('name', '').replace(' ', '_')
                plan_ids.update(state_info['counties'].get(county_name, []))
            plan_ids = list(plan_ids)
        
        plans = [state_info['plans'][pid] for pid in plan_ids if pid in state_info['plans']]
        
        response = {
            'zip_code': zip_code,
            'state': state_info['info']['state'],
            'state_abbrev': state,
            'type': 'county',
            'multi_county': zip_info['multi_county'],
            'primary_county': zip_info['primary_county'],
            'counties': zip_info['counties'],
            'plan_count': len(plans),
            'plans': [get_plan_summary(p) for p in plans] if not include_details else plans
        }
    
    return jsonify(response)

@app.route('/api/<state>/plan/<plan_id>', methods=['GET'])
def get_plan_detail(state, plan_id):
    """Get details for a specific plan"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({'error': 'State not available', 'state': state}), 404
    
    state_info = STATE_DATA[state]
    
    if plan_id in state_info['plans']:
        plan = state_info['plans'][plan_id]
        return jsonify({
            'plan_id': plan_id,
            'state': state_info['info']['state'],
            'state_abbrev': state,
            'data': plan
        })
    
    return jsonify({'error': 'Plan not found', 'plan_id': plan_id, 'state': state}), 404

@app.route('/api/<state>/plans', methods=['GET'])
def list_all_plans(state):
    """List all plans for a state"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({'error': 'State not available', 'state': state}), 404
    
    state_info = STATE_DATA[state]
    include_details = request.args.get('details', 'false').lower() == 'true'
    
    plans = list(state_info['plans'].values())
    
    return jsonify({
        'state': state_info['info']['state'],
        'state_abbrev': state,
        'plan_count': len(plans),
        'plans': plans if include_details else [get_plan_summary(p) for p in plans]
    })

@app.route('/api/<state>/counties', methods=['GET'])
def list_counties(state):
    """List all counties for a state"""
    state = state.upper()
    
    if state not in STATE_DATA:
        return jsonify({'error': 'State not available', 'state': state}), 404
    
    state_info = STATE_DATA[state]
    
    if state_info['type'] == 'region':
        return jsonify({
            'state': state_info['info']['state'],
            'type': 'region',
            'message': 'This is a region-based state without counties'
        })
    
    counties = []
    for county_name, plan_ids in state_info['counties'].items():
        counties.append({
            'name': county_name.replace('_', ' '),
            'plan_count': len(plan_ids)
        })
    
    return jsonify({
        'state': state_info['info']['state'],
        'state_abbrev': state,
        'county_count': len(counties),
        'counties': sorted(counties, key=lambda x: x['name'])
    })

@app.route('/api/zip/<zip_code>', methods=['GET'])
def get_plans_by_zip_only(zip_code):
    """
    Get plans for a ZIP code without specifying state.
    Returns plans from all counties the ZIP covers.
    This is the preferred endpoint as it handles multi-state ZIPs correctly.
    """
    if not UNIFIED_ZIP_MAP:
        return jsonify({
            'error': 'ZIP-only lookup not available',
            'message': 'unified_zip_to_fips.json not loaded'
        }), 503
    
    if zip_code not in UNIFIED_ZIP_MAP:
        return jsonify({
            'error': 'ZIP code not found',
            'zip_code': zip_code
        }), 404
    
    zip_info = UNIFIED_ZIP_MAP[zip_code]
    include_details = request.args.get('details', 'false').lower() == 'true'
    
    # Collect plans from all counties
    all_plans = {}
    counties_with_plans = []
    
    for county in zip_info['counties']:
        state = county['state']
        fips = county['fips']
        county_name = county['name']
        
        # Skip if state not loaded
        if state not in STATE_DATA:
            counties_with_plans.append({
                'fips': fips,
                'name': county_name,
                'state': state,
                'ratio': county['ratio'],
                'plans_available': False,
                'message': f'State {state} not yet scraped'
            })
            continue
        
        state_info = STATE_DATA[state]
        
        # Get plans for this county
        plan_ids = []
        
        # Try to find plans via zip_to_plans first
        if zip_code in state_info['zip_to_plans']:
            plan_ids = state_info['zip_to_plans'][zip_code]
        else:
            # Fallback: look up by county name
            county_key = county_name.replace(' ', '_')
            plan_ids = state_info['counties'].get(county_key, [])
        
        county_plans = []
        for pid in plan_ids:
            if pid in state_info['plans'] and pid not in all_plans:
                all_plans[pid] = state_info['plans'][pid]
                county_plans.append(pid)
        
        counties_with_plans.append({
            'fips': fips,
            'name': county_name,
            'state': state,
            'ratio': county['ratio'],
            'plans_available': True,
            'plan_count': len(county_plans)
        })
    
    # Format response
    plans_list = list(all_plans.values())
    
    response = {
        'zip_code': zip_code,
        'multi_county': zip_info['multi_county'],
        'multi_state': zip_info['multi_state'],
        'states': zip_info['states'],
        'primary_state': zip_info['primary_state'],
        'counties': counties_with_plans,
        'plan_count': len(plans_list),
        'plans': plans_list if include_details else [get_plan_summary(p) for p in plans_list]
    }
    
    return jsonify(response)

@app.route('/api/states', methods=['GET'])
def list_states():
    """List all available states"""
    states = []
    for abbrev, data in STATE_DATA.items():
        states.append({
            'abbrev': abbrev,
            'name': data['info']['state'],
            'type': data['type'],
            'plan_count': len(data['plans']),
            'zip_count': data['info'].get('zip_count', 0)
        })
    
    return jsonify({
        'state_count': len(states),
        'total_plans': sum(s['plan_count'] for s in states),
        'states': sorted(states, key=lambda x: x['name'])
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'states_loaded': len(STATE_DATA),
        'total_plans': sum(len(d['plans']) for d in STATE_DATA.values()),
        'states': sorted(STATE_DATA.keys())
    })

@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    return jsonify({
        'name': 'Medicare Plan API',
        'version': '3.1',
        'description': 'Medicare Advantage and Part D plan lookup by ZIP code',
        'endpoints': {
            'GET /api/zip/<zip_code>': 'Get plans by ZIP (PREFERRED - handles multi-state ZIPs)',
            'GET /api/states': 'List all available states',
            'GET /api/<state>/<zip_code>': 'Get plans for a ZIP code in specific state',
            'GET /api/<state>/plans': 'List all plans in a state',
            'GET /api/<state>/plan/<plan_id>': 'Get specific plan details',
            'GET /api/<state>/counties': 'List counties in a state',
            'GET /health': 'Health check'
        },
        'parameters': {
            'details': 'Add ?details=true for full plan data'
        },
        'examples': [
            '/api/zip/03462',
            '/api/zip/96701',
            '/api/states',
            '/api/NH/plans',
            '/api/NH/plan/H5521_042_0'
        ],
        'notes': {
            'zip_endpoint': 'The /api/zip/<zip> endpoint is preferred as it correctly handles ZIPs that span multiple counties or states',
            'coverage': f'{len(UNIFIED_ZIP_MAP)} ZIP codes mapped to FIPS counties',
            'multi_state_zips': 'Some ZIPs span state borders - the ZIP endpoint returns plans from all applicable states'
        }
    })

if __name__ == '__main__':
    print("=" * 80)
    print("Medicare Plan API Server v3")
    print("=" * 80)
    
    load_unified_zip_map()
    load_state_data()
    
    total_plans = sum(len(d['plans']) for d in STATE_DATA.values())
    
    print("\n" + "=" * 80)
    print(f"Loaded {len(STATE_DATA)} states with {total_plans} total plans")
    print(f"Unified ZIP mapping: {len(UNIFIED_ZIP_MAP)} ZIPs")
    print("\nEndpoints:")
    print("  GET /                           - API documentation")
    print("  GET /api/zip/<zip>              - Plans by ZIP (PREFERRED)")
    print("  GET /api/states                 - List all states")
    print("  GET /api/<state>/<zip>          - Plans for ZIP in state")
    print("  GET /api/<state>/plans          - All state plans")
    print("  GET /api/<state>/plan/<id>      - Specific plan")
    print("  GET /api/<state>/counties       - List counties")
    print("  GET /health                     - Health check")
    print("\n" + "=" * 80)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
