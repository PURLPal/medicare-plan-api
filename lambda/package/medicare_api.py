"""
Medicare Plan API - Lambda Function
Handles all API endpoints for Medicare plan queries
"""
import json
import os
import pg8000.native

# OpenAPI specification
OPENAPI_SPEC = '''openapi: 3.0.3
info:
  title: Medicare Plan API
  description: Database-backed API for Medicare plan lookup by ZIP code. 5,804 plans, 98.6% ZIP coverage, 290-400ms response time.
  version: 2.0.0
servers:
  - url: https://medicare.purlpal-api.com/medicare
paths:
  /states.json:
    get:
      summary: List all states with plan counts
  /state/{state}/info.json:
    get:
      summary: Get state information
  /state/{state}/plans.json:
    get:
      summary: Get all plans in state
  /zip/{zipcode}.json:
    get:
      summary: Get plans by ZIP code
  /zip/{zipcode}_{category}.json:
    get:
      summary: Get plans by category (MAPD, MA, or PD)
  /plan/{planId}.json:
    get:
      summary: Get individual plan details
For full schema, visit: https://github.com/yourusername/medicare-api/blob/main/openapi-compact.yaml
'''

# Database connection from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# Global connection for reuse across Lambda invocations
_db_connection = None

def get_db_connection():
    """Get database connection (reuses existing connection if available)."""
    global _db_connection
    
    # Try to reuse existing connection
    if _db_connection is not None:
        try:
            # Test connection is still alive
            _db_connection.run("SELECT 1")
            return _db_connection
        except:
            # Connection is dead, create new one
            _db_connection = None
    
    # Create new connection
    _db_connection = pg8000.native.Connection(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        ssl_context=True  # Enable SSL for RDS
    )
    return _db_connection

def lambda_handler(event, context):
    """Main Lambda handler for all Medicare API endpoints."""
    
    # Parse request - API Gateway v2 uses different field names
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    raw_path = event.get('rawPath', event.get('path', ''))
    query_params = event.get('queryStringParameters') or {}
    
    # Strip stage prefix (/prod, /dev, etc.) from path
    stage = event.get('requestContext', {}).get('stage', '')
    if stage and raw_path.startswith(f'/{stage}/'):
        path = raw_path[len(f'/{stage}'):]
    else:
        path = raw_path
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # Handle OPTIONS (CORS preflight)
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Route to appropriate handler
        if path == '/medicare/openapi.yaml':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/yaml',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': OPENAPI_SPEC
            }
        elif path.startswith('/medicare/zip/'):
            return handle_zip_query(path, query_params, headers)
        elif path.startswith('/medicare/state/'):
            return handle_state_query(path, headers)
        elif path.startswith('/medicare/plan/'):
            return handle_plan_query(path, headers)
        elif path == '/medicare/states.json':
            return handle_states_list(headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }

def handle_zip_query(path, query_params, headers):
    """Handle /medicare/zip/{zip_code}.json endpoint."""
    
    # Extract ZIP code from path
    parts = path.split('/')
    zip_file = parts[-1]  # e.g., "12345.json" or "12345_MAPD.json"
    
    # Parse ZIP and optional category
    if '_' in zip_file:
        zip_code, cat_part = zip_file.split('_', 1)
        category = cat_part.replace('.json', '')
    else:
        zip_code = zip_file.replace('.json', '')
        category = None
    
    conn = get_db_connection()
    
    # Get ZIP info
    rows = conn.run("""
        SELECT zip_code, multi_county, multi_state, primary_state, states
        FROM zip_codes
        WHERE zip_code = :zip
    """, zip=zip_code)
    
    if not rows:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'ZIP code not found'})
        }
    
    zip_row = rows[0]
    zip_info = {
        'zip_code': zip_row[0],
        'multi_county': zip_row[1],
        'multi_state': zip_row[2],
        'primary_state': zip_row[3],
        'states': zip_row[4]
    }
    
    # Get counties for this ZIP
    county_rows = conn.run("""
        SELECT c.id, c.county_name, c.fips, zc.state_abbrev, zc.ratio
        FROM zip_counties zc
        JOIN counties c ON zc.county_id = c.id
        WHERE zc.zip_code = :zip
    """, zip=zip_code)
    
    counties = [{
        'id': row[0],
        'name': row[1],
        'fips': row[2],
        'state': row[3],
        'ratio': float(row[4]) if row[4] else 1.0
    } for row in county_rows]
    
    # Get ALL plans for ALL counties in a single query
    county_ids = [c['id'] for c in counties]
    
    if category:
        plan_rows = conn.run("""
            SELECT DISTINCT ON (pc.county_id, p.plan_id)
                pc.county_id,
                p.plan_id,
                p.category,
                p.plan_type,
                p.plan_info,
                p.premiums,
                p.deductibles,
                p.out_of_pocket,
                p.benefits,
                p.drug_coverage,
                p.extra_benefits
            FROM plans p
            INNER JOIN plan_counties pc ON p.plan_id = pc.plan_id
            WHERE pc.county_id = ANY(:county_ids) AND p.category = :cat
            ORDER BY pc.county_id, p.plan_id, p.category, p.monthly_premium_value NULLS LAST
        """, county_ids=county_ids, cat=category)
    else:
        plan_rows = conn.run("""
            SELECT DISTINCT ON (pc.county_id, p.plan_id)
                pc.county_id,
                p.plan_id,
                p.category,
                p.plan_type,
                p.plan_info,
                p.premiums,
                p.deductibles,
                p.out_of_pocket,
                p.benefits,
                p.drug_coverage,
                p.extra_benefits
            FROM plans p
            INNER JOIN plan_counties pc ON p.plan_id = pc.plan_id
            WHERE pc.county_id = ANY(:county_ids)
            ORDER BY pc.county_id, p.plan_id, p.category, p.monthly_premium_value NULLS LAST
        """, county_ids=county_ids)
    
    # Group plans by county
    plans_by_county_id = {}
    for row in plan_rows:
        county_id = row[0]
        if county_id not in plans_by_county_id:
            plans_by_county_id[county_id] = []
        
        plan_data = {
            'plan_id': row[1],
            'category': row[2],
            'plan_type': row[3],
            'plan_info': row[4] if row[4] else {},
            'premiums': row[5] if row[5] else {},
            'deductibles': row[6] if row[6] else {},
            'out_of_pocket': row[7] if row[7] else {},
            'benefits': row[8] if row[8] else {},
            'drug_coverage': row[9] if row[9] else {},
            'extra_benefits': row[10] if row[10] else []
        }
        plans_by_county_id[county_id].append(plan_data)
    
    # Build county response with plans
    counties_with_plans = []
    all_plans = []
    seen_plan_ids = set()
    plans_by_category = {'MAPD': [], 'PD': [], 'MA': []}
    
    for county in counties:
        county_id = county['id']
        county_plans = plans_by_county_id.get(county_id, [])
        
        # Add to all_plans if not already present (for backwards compatibility)
        for plan_data in county_plans:
            if plan_data['plan_id'] not in seen_plan_ids:
                seen_plan_ids.add(plan_data['plan_id'])
                all_plans.append(plan_data)
                if plan_data['category'] in plans_by_category:
                    plans_by_category[plan_data['category']].append(plan_data)
        
        # Add county with its plans
        county_with_plans = {
            'name': county['name'],
            'fips': county['fips'],
            'state': county['state'],
            'ratio': county['ratio'],
            'plans': county_plans,
            'plan_count': len(county_plans),
            'plans_available': len(county_plans) > 0
        }
        counties_with_plans.append(county_with_plans)
    
    response = {
        'zip_code': zip_code,
        'multi_county': zip_info['multi_county'],
        'multi_state': zip_info['multi_state'],
        'states': zip_info['states'],
        'primary_state': zip_info['primary_state'],
        'counties': counties_with_plans,
        'plans': all_plans,  # For backwards compatibility
        'plan_count': len(all_plans),
        'plan_counts_by_category': {
            'MAPD': len(plans_by_category['MAPD']),
            'PD': len(plans_by_category['PD']),
            'MA': len(plans_by_category['MA'])
        }
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_state_query(path, headers):
    """Handle /medicare/state/{state}/info.json or /plans.json."""
    
    parts = path.split('/')
    state_abbrev = parts[3]
    endpoint = parts[4] if len(parts) > 4 else 'info.json'
    
    conn = get_db_connection()
    
    if endpoint == 'info.json':
        # State info
        rows = conn.run("""
            SELECT abbrev, name, plan_count
            FROM states
            WHERE abbrev = :state
        """, state=state_abbrev)
        
        if not rows:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'State not found'})
            }
        
        state = rows[0]
        response = {
            'state': state[1],
            'state_abbrev': state[0],
            'plan_count': state[2]
        }
    
    elif endpoint == 'plans.json':
        # All plans in state (summary)
        rows = conn.run("""
            SELECT 
                plan_id,
                plan_name,
                monthly_premium_display,
                health_deductible_display,
                drug_deductible_display
            FROM plans
            WHERE state_abbrev = :state
            ORDER BY category, monthly_premium_value NULLS LAST
        """, state=state_abbrev)
        
        plans = rows
        
        rows = conn.run("SELECT name FROM states WHERE abbrev = :state", state=state_abbrev)
        state_name = rows[0][0]
        
        response = {
            'state': state_name,
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'plans': [dict(zip(['plan_id', 'plan_name', 'monthly_premium_display', 'health_deductible_display', 'drug_deductible_display'], row)) for row in plans]
        }
    
    else:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Endpoint not found'})
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_plan_query(path, headers):
    """Handle /medicare/plan/{plan_id}.json."""
    
    parts = path.split('/')
    plan_file = parts[-1]
    plan_id = plan_file.replace('.json', '')
    
    conn = get_db_connection()
    
    rows = conn.run("""
        SELECT 
            plan_id,
            state_abbrev,
            plan_info,
            premiums,
            deductibles,
            out_of_pocket,
            benefits,
            drug_coverage,
            extra_benefits
        FROM plans
        WHERE plan_id = :plan
    """, plan=plan_id)
    
    if not rows:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Plan not found'})
        }
    
    plan = rows[0]
    response = {
        'plan_id': plan[0],
        'state': plan[1],
        'plan_info': plan[2],
        'premiums': plan[3],
        'deductibles': plan[4],
        'out_of_pocket': plan[5],
        'benefits': plan[6],
        'drug_coverage': plan[7],
        'extra_benefits': plan[8]
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_states_list(headers):
    """Handle /medicare/states.json."""
    
    conn = get_db_connection()
    
    rows = conn.run("""
        SELECT abbrev, name, plan_count
        FROM states
        WHERE abbrev NOT IN ('AS', 'GU', 'MP', 'PR', 'VI')
        ORDER BY name
    """)
    
    states = rows
    
    response = {
        'state_count': len(states),
        'total_plans': sum(row[2] for row in states),
        'states': [
            {
                'abbrev': row[0],
                'name': row[1],
                'plan_count': row[2],
                'info_url': f"/medicare/state/{row[0]}/info.json",
                'plans_url': f"/medicare/state/{row[0]}/plans.json"
            }
            for row in states
        ]
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }
