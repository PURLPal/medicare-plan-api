#!/usr/bin/env python3
"""
Investigate network requests to find API endpoints
"""
from playwright.sync_api import sync_playwright
import json

def capture_network_traffic(url):
    """Capture all network requests while loading a page"""

    api_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Capture all requests
        def handle_request(request):
            api_requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type,
                'headers': dict(request.headers)
            })

        # Capture all responses
        responses = []
        def handle_response(response):
            responses.append({
                'url': response.url,
                'status': response.status,
                'content_type': response.headers.get('content-type', ''),
                'method': response.request.method
            })

        page.on('request', handle_request)
        page.on('response', handle_response)

        print(f"Loading: {url}")
        page.goto(url, wait_until='load', timeout=60000)

        # Give it time to load content
        page.wait_for_timeout(10000)

        browser.close()

    return api_requests, responses

# Test with a sample plan
test_url = "https://www.medicare.gov/plan-compare/#/plan-details/2026-H2001-068-1?year=2026&lang=en"

print("="*80)
print("INVESTIGATING NETWORK REQUESTS")
print("="*80)
print()

requests, responses = capture_network_traffic(test_url)

print(f"\nCaptured {len(requests)} requests and {len(responses)} responses")

# Filter for potential API calls (JSON, fetch, XHR)
print("\n" + "="*80)
print("POTENTIAL API ENDPOINTS")
print("="*80)

api_candidates = []
for resp in responses:
    url = resp['url']
    content_type = resp['content_type']

    # Look for JSON responses or API-like URLs
    if 'json' in content_type.lower() or '/api/' in url or 'graphql' in url:
        api_candidates.append(resp)
        print(f"\n{resp['method']} {resp['status']}")
        print(f"URL: {url}")
        print(f"Content-Type: {content_type}")

# Save all requests to file for analysis
with open('network_requests.json', 'w') as f:
    json.dump({
        'requests': requests,
        'responses': responses
    }, f, indent=2)

print(f"\n\nAll network traffic saved to: network_requests.json")
print(f"Found {len(api_candidates)} potential API endpoints")
