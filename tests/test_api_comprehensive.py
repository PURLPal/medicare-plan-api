#!/usr/bin/env python3
"""
Comprehensive API Test Script
Tests multiple random ZIP codes per state via the Medicare API
"""

import json
import random
import time
import sys
from pathlib import Path
import urllib.request
import urllib.error
from collections import defaultdict
import ssl

API_BASE_URL = "https://medicare.purlpal-api.com/medicare"

# Test configuration
ZIPS_PER_STATE = int(sys.argv[1]) if len(sys.argv) > 1 else 5  # Default 5 ZIPs per state
REQUESTS_PER_SECOND = 2
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

def load_zip_data():
    """Load ZIP code data to sample from"""
    zip_file = Path("unified_zip_to_fips.json")
    if not zip_file.exists():
        print("❌ unified_zip_to_fips.json not found")
        return {}
    
    with open(zip_file) as f:
        return json.load(f)

def get_zips_by_state(zip_data):
    """Organize ZIP codes by state"""
    zips_by_state = defaultdict(list)
    
    for zip_code, info in zip_data.items():
        states = info.get('states', [])
        primary_state = info.get('primary_state')
        
        if primary_state:
            zips_by_state[primary_state].append(zip_code)
        elif states:
            zips_by_state[states[0]].append(zip_code)
    
    return zips_by_state

def test_api_endpoint(url, timeout=30, retry_count=0):
    """Test a single API endpoint with retry logic"""
    start_time = time.time()
    
    try:
        # Create SSL context that's more tolerant
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Medicare-API-Test/1.0')
        
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            elapsed = time.time() - start_time
            data = json.loads(response.read().decode('utf-8'))
            
            return {
                'success': True,
                'status_code': response.status,
                'elapsed_ms': round(elapsed * 1000, 2),
                'data': data,
                'retries': retry_count
            }
    
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        try:
            error_data = json.loads(e.read().decode('utf-8'))
        except:
            error_data = {'error': str(e)}
        
        return {
            'success': False,
            'status_code': e.code,
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': error_data,
            'retries': retry_count
        }
    
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as e:
        # Retry on network/SSL errors
        if retry_count < RETRY_ATTEMPTS:
            time.sleep(RETRY_DELAY)
            return test_api_endpoint(url, timeout, retry_count + 1)
        
        elapsed = time.time() - start_time
        return {
            'success': False,
            'status_code': 0,
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': f'{type(e).__name__}: {str(e)}',
            'retries': retry_count
        }
    
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'success': False,
            'status_code': 0,
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': str(e),
            'retries': retry_count
        }

def test_zip_code(zip_code, state):
    """Test all endpoints for a ZIP code"""
    results = {
        'zip_code': zip_code,
        'state': state,
        'tests': {}
    }
    
    # Test 1: All plans
    print(f"  Testing {zip_code}...", end=" ", flush=True)
    all_plans_url = f"{API_BASE_URL}/zip/{zip_code}.json"
    result = test_api_endpoint(all_plans_url)
    results['tests']['all_plans'] = result
    
    if result['success']:
        plan_count = result['data'].get('plan_count', 0)
        categories = result['data'].get('plan_counts_by_category', {})
        print(f"✅ {plan_count} plans ({result['elapsed_ms']}ms)", end=" ")
        
        # Test 2: MAPD plans if available
        if categories.get('MAPD', 0) > 0:
            mapd_url = f"{API_BASE_URL}/zip/{zip_code}_MAPD.json"
            mapd_result = test_api_endpoint(mapd_url)
            results['tests']['mapd'] = mapd_result
            if mapd_result['success']:
                print(f"MAPD: {mapd_result['data'].get('plan_count', 0)}", end=" ")
        
        # Test 3: MA plans if available
        if categories.get('MA', 0) > 0:
            ma_url = f"{API_BASE_URL}/zip/{zip_code}_MA.json"
            ma_result = test_api_endpoint(ma_url)
            results['tests']['ma'] = ma_result
            if ma_result['success']:
                print(f"MA: {ma_result['data'].get('plan_count', 0)}", end=" ")
        
        # Test 4: PD plans if available
        if categories.get('PD', 0) > 0:
            pd_url = f"{API_BASE_URL}/zip/{zip_code}_PD.json"
            pd_result = test_api_endpoint(pd_url)
            results['tests']['pd'] = pd_result
            if pd_result['success']:
                print(f"PD: {pd_result['data'].get('plan_count', 0)}", end=" ")
        
        print()
    else:
        status = result.get('status_code', 'unknown')
        error = result.get('error', {})
        error_msg = error.get('error', str(error)) if isinstance(error, dict) else str(error)
        print(f"❌ Failed ({status}): {error_msg}")
    
    return results

def main():
    """Main test execution"""
    print("=" * 70)
    print("🏥 Medicare API Comprehensive Test")
    print("=" * 70)
    print(f"📊 Testing {ZIPS_PER_STATE} random ZIP code(s) per state")
    print(f"⏱️  Rate limit: {REQUESTS_PER_SECOND} requests/second")
    print(f"🔄 Retry attempts: {RETRY_ATTEMPTS}")
    print()
    
    # Load ZIP code data
    print("📂 Loading ZIP code data...")
    zip_data = load_zip_data()
    if not zip_data:
        print("❌ Cannot proceed without ZIP code data")
        return
    
    print(f"✅ Loaded {len(zip_data):,} ZIP codes")
    print()
    
    # Organize by state
    zips_by_state = get_zips_by_state(zip_data)
    print(f"✅ Found ZIP codes for {len(zips_by_state)} states/territories")
    print()
    
    # Test states endpoint first
    print("🔍 Testing states list endpoint...")
    states_url = f"{API_BASE_URL}/states.json"
    states_result = test_api_endpoint(states_url)
    
    if not states_result['success']:
        print(f"❌ States endpoint failed: {states_result.get('error')}")
        return
    
    api_states = states_result['data'].get('states', [])
    print(f"✅ API returned {len(api_states)} states ({states_result['elapsed_ms']}ms)")
    print()
    
    # Filter to states with plans (exclude territories without data)
    states_to_test = [s['abbrev'] for s in api_states if s.get('plan_count', 0) > 0]
    print(f"📊 Testing {len(states_to_test)} states with plans")
    print()
    
    # Run tests
    all_results = []
    successful_tests = 0
    failed_tests = 0
    total_response_time = 0
    states_tested = 0
    
    for state in sorted(states_to_test):
        if state not in zips_by_state or len(zips_by_state[state]) == 0:
            print(f"⚠️  {state}: No ZIP codes available in dataset")
            continue
        
        print(f"\n🏛️  {state} ({len(zips_by_state[state])} ZIPs available)")
        
        # Sample random ZIPs (configurable)
        sample_size = min(ZIPS_PER_STATE, len(zips_by_state[state]))
        test_zips = random.sample(zips_by_state[state], sample_size)
        
        for zip_code in test_zips:
            result = test_zip_code(zip_code, state)
            all_results.append(result)
            
            # Count successes/failures
            for test_name, test_result in result['tests'].items():
                if test_result['success']:
                    successful_tests += 1
                    total_response_time += test_result['elapsed_ms']
                else:
                    failed_tests += 1
        
        states_tested += 1
        
        # Rate limiting: delay between requests
        time.sleep(1.0 / REQUESTS_PER_SECOND)
    
    # Summary
    print()
    print("=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"States Tested: {states_tested}")
    print(f"ZIP Codes Tested: {len(all_results)}")
    print(f"Successful API Calls: {successful_tests}")
    print(f"Failed API Calls: {failed_tests}")
    
    if successful_tests > 0:
        avg_response = total_response_time / successful_tests
        print(f"Average Response Time: {avg_response:.2f}ms")
    
    success_rate = (successful_tests / (successful_tests + failed_tests) * 100) if (successful_tests + failed_tests) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Save detailed results
    output_file = Path("api_test_results.json")
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'states_tested': states_tested,
                'zip_codes_tested': len(all_results),
                'successful_calls': successful_tests,
                'failed_calls': failed_tests,
                'success_rate': success_rate,
                'avg_response_ms': total_response_time / successful_tests if successful_tests > 0 else 0
            },
            'results': all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Show any failures
    if failed_tests > 0:
        print()
        print("❌ Failed Tests:")
        for result in all_results:
            for test_name, test_result in result['tests'].items():
                if not test_result['success']:
                    error = test_result.get('error', 'Unknown error')
                    print(f"   {result['state']} {result['zip_code']} ({test_name}): {error}")
    
    print()
    print("=" * 70)
    
    if success_rate >= 95:
        print("✅ API is performing well!")
    elif success_rate >= 80:
        print("⚠️  API has some issues but mostly working")
    else:
        print("❌ API has significant issues")

if __name__ == "__main__":
    main()
