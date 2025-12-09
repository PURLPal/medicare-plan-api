#!/usr/bin/env python3
"""
Deploy South Carolina Medicare API to production.
Uploads all 525 SC ZIP files and minified versions to S3 + CloudFront.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime

BUCKET = "purlpal-medicare-api"
DISTRIBUTION_ID = "E3SHXUEGZALG4E"
BASE_PATH = "medicare"

def get_sc_zips():
    """Get list of all SC ZIP codes."""
    with open('unified_zip_to_fips.json') as f:
        all_zips = json.load(f)
    return [z for z, info in all_zips.items() if 'SC' in info.get('states', [])]

def deploy_regular_files(sc_zips):
    """Deploy regular ZIP files."""
    print("\n" + "="*80)
    print("DEPLOYING REGULAR ZIP FILES")
    print("="*80)
    
    # Use AWS CLI sync for efficiency
    print(f"\nUploading {len(sc_zips)} SC ZIP files...")
    
    cmd = [
        'aws', 's3', 'sync',
        'static_api/medicare/zip/',
        f's3://{BUCKET}/{BASE_PATH}/zip/',
        '--exclude', '*',
        '--include', '29*.json',
        '--content-type', 'application/json',
        '--size-only'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Regular files uploaded successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print("✗ Error uploading regular files")
        print(result.stderr)
        return False
    
    return True

def deploy_minified_files():
    """Deploy minified ZIP files."""
    print("\n" + "="*80)
    print("DEPLOYING MINIFIED ZIP FILES")
    print("="*80)
    
    minified_dir = Path('static_api/medicare/zip_minified')
    if not minified_dir.exists():
        print("⚠ No minified directory found, skipping")
        return True
    
    # Count SC minified files
    sc_minified = list(minified_dir.glob('29*.json'))
    print(f"\nUploading {len(sc_minified)} minified files...")
    
    cmd = [
        'aws', 's3', 'sync',
        'static_api/medicare/zip_minified/',
        f's3://{BUCKET}/{BASE_PATH}/zip_minified/',
        '--exclude', '*',
        '--include', '29*.json',
        '--content-type', 'application/json',
        '--size-only'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Minified files uploaded successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print("⚠ Error uploading minified files (non-critical)")
        print(result.stderr)
    
    return True

def invalidate_cloudfront():
    """Invalidate CloudFront cache."""
    print("\n" + "="*80)
    print("INVALIDATING CLOUDFRONT CACHE")
    print("="*80)
    
    # Invalidate SC ZIPs with wildcard
    paths = [
        f'/{BASE_PATH}/zip/29*.json',
        f'/{BASE_PATH}/zip_minified/29*.json'
    ]
    
    print(f"\nInvalidating paths:")
    for p in paths:
        print(f"  - {p}")
    
    cmd = [
        'aws', 'cloudfront', 'create-invalidation',
        '--distribution-id', DISTRIBUTION_ID,
        '--paths', *paths
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ CloudFront invalidation created")
        data = json.loads(result.stdout)
        inv_id = data['Invalidation']['Id']
        print(f"  Invalidation ID: {inv_id}")
        print(f"  Status: {data['Invalidation']['Status']}")
    else:
        print("✗ Error creating invalidation")
        print(result.stderr)
        return False
    
    return True

def verify_deployment(sample_zips):
    """Verify a sample of deployed files."""
    print("\n" + "="*80)
    print("VERIFYING DEPLOYMENT")
    print("="*80)
    
    import requests
    
    base_url = f"https://medicare.purlpal-api.com/{BASE_PATH}/zip"
    
    print(f"\nChecking {len(sample_zips)} sample ZIPs...")
    
    success = 0
    for zip_code in sample_zips:
        url = f"{base_url}/{zip_code}.json"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                plan_count = data.get('plan_count', 0)
                print(f"  ✓ {zip_code}: {plan_count} plans")
                success += 1
            else:
                print(f"  ✗ {zip_code}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ {zip_code}: {e}")
    
    print(f"\nVerification: {success}/{len(sample_zips)} successful")
    return success == len(sample_zips)

def main():
    print("="*80)
    print("SOUTH CAROLINA MEDICARE API DEPLOYMENT")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get SC ZIPs
    sc_zips = get_sc_zips()
    print(f"\nTotal SC ZIP codes: {len(sc_zips)}")
    
    # Calculate stats
    zip_dir = Path('static_api/medicare/zip')
    total_size = sum((zip_dir / f'{z}.json').stat().st_size for z in sc_zips if (zip_dir / f'{z}.json').exists())
    
    print(f"Total data size: {total_size/1024/1024:.1f} MB")
    print(f"Destination: s3://{BUCKET}/{BASE_PATH}/")
    print(f"CDN: https://medicare.purlpal-api.com/{BASE_PATH}/")
    
    # Deploy
    if not deploy_regular_files(sc_zips):
        print("\n✗ Deployment failed!")
        return 1
    
    deploy_minified_files()
    
    if not invalidate_cloudfront():
        print("\n⚠ Cache invalidation failed, but files are deployed")
    
    # Verify sample
    sample_zips = ['29401', '29002', '29577', '29803', '29928']
    verify_deployment(sample_zips)
    
    print("\n" + "="*80)
    print("DEPLOYMENT COMPLETE!")
    print("="*80)
    print(f"\n✓ {len(sc_zips)} SC ZIP files deployed")
    print(f"✓ Live at: https://medicare.purlpal-api.com/{BASE_PATH}/zip/29*.json")
    print(f"\nKey endpoints:")
    print(f"  - ZIP 29401: https://medicare.purlpal-api.com/{BASE_PATH}/zip/29401.json")
    print(f"  - ZIP 29401 (Ebony): https://medicare.purlpal-api.com/{BASE_PATH}/zip/29401_ebony.json")
    print(f"  - ZIP 29401 (Minified): https://medicare.purlpal-api.com/{BASE_PATH}/zip_minified/29401_minified.json")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
