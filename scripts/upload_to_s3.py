#!/usr/bin/env python3
"""
Upload scraped Medicare data from EC2 to S3
Handles both JSON (parsed) and HTML (raw) data
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

# S3 Configuration
S3_BUCKET = 'purlpal-medicare-api'
S3_JSON_PREFIX = 'scraped_data/json'
S3_HTML_PREFIX = 'scraped_data/html'
S3_SUMMARIES_PREFIX = 'scraped_data/summaries'

# Local paths
OUTPUT_BASE = Path('output')

def run_aws_command(cmd):
    """Run AWS CLI command and return result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️  Warning: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def upload_directory(local_dir, s3_prefix, description):
    """Upload a directory to S3."""
    if not local_dir.exists():
        print(f"  ⚠️  {local_dir} does not exist, skipping")
        return 0
    
    print(f"\n📤 Uploading {description}...")
    print(f"  Source: {local_dir}")
    print(f"  Destination: s3://{S3_BUCKET}/{s3_prefix}/")
    
    # Count files
    file_count = sum(1 for _ in local_dir.rglob('*') if _.is_file())
    print(f"  Files: {file_count}")
    
    # Upload with AWS CLI (faster than boto3 for bulk uploads)
    cmd = f"aws s3 sync {local_dir} s3://{S3_BUCKET}/{s3_prefix}/ --size-only --delete"
    
    if run_aws_command(cmd):
        print(f"  ✅ {description} uploaded successfully")
        return file_count
    else:
        print(f"  ❌ {description} upload failed")
        return 0

def upload_file(local_file, s3_key, description):
    """Upload a single file to S3."""
    if not local_file.exists():
        print(f"  ⚠️  {local_file} does not exist, skipping")
        return False
    
    print(f"\n📤 Uploading {description}...")
    cmd = f"aws s3 cp {local_file} s3://{S3_BUCKET}/{s3_key}"
    
    if run_aws_command(cmd):
        print(f"  ✅ {description} uploaded")
        return True
    else:
        print(f"  ❌ {description} upload failed")
        return False

def generate_upload_summary():
    """Generate summary of what will be uploaded."""
    summary = {
        'upload_time': datetime.utcnow().isoformat() + 'Z',
        'json_states': [],
        'html_states': [],
        'total_json_files': 0,
        'total_html_files': 0,
        'summaries': 0
    }
    
    # Count JSON files
    json_dir = OUTPUT_BASE / 'json'
    if json_dir.exists():
        for state_dir in sorted(json_dir.iterdir()):
            if state_dir.is_dir():
                file_count = sum(1 for _ in state_dir.glob('*.json'))
                summary['json_states'].append({
                    'state': state_dir.name,
                    'files': file_count
                })
                summary['total_json_files'] += file_count
    
    # Count HTML files
    html_dir = OUTPUT_BASE / 'html'
    if html_dir.exists():
        for state_dir in sorted(html_dir.iterdir()):
            if state_dir.is_dir():
                file_count = sum(1 for _ in state_dir.glob('*.html'))
                summary['html_states'].append({
                    'state': state_dir.name,
                    'files': file_count
                })
                summary['total_html_files'] += file_count
    
    # Count summaries
    summaries_dir = OUTPUT_BASE / 'summaries'
    if summaries_dir.exists():
        summary['summaries'] = sum(1 for _ in summaries_dir.glob('*.json'))
    
    return summary

def main():
    print("="*80)
    print("UPLOAD MEDICARE DATA TO S3")
    print("="*80)
    
    # Generate summary
    summary = generate_upload_summary()
    
    print(f"\n📊 Upload Summary:")
    print(f"  States with JSON data: {len(summary['json_states'])}")
    print(f"  Total JSON files: {summary['total_json_files']:,}")
    print(f"  States with HTML data: {len(summary['html_states'])}")
    print(f"  Total HTML files: {summary['total_html_files']:,}")
    print(f"  Summary files: {summary['summaries']}")
    
    if summary['total_json_files'] == 0 and summary['total_html_files'] == 0:
        print("\n⚠️  No data to upload!")
        return
    
    print(f"\n🎯 S3 Destination: s3://{S3_BUCKET}/")
    
    # Upload JSON data (parsed, most important)
    json_files = upload_directory(
        OUTPUT_BASE / 'json',
        S3_JSON_PREFIX,
        'Parsed JSON data'
    )
    
    # Upload summaries
    summaries_uploaded = upload_directory(
        OUTPUT_BASE / 'summaries',
        S3_SUMMARIES_PREFIX,
        'State summaries'
    )
    
    # Upload HTML (raw data, optional - can skip to save space/time)
    print("\n❓ Upload raw HTML files? (large, can be skipped)")
    print("   JSON data is already uploaded and contains all parsed information")
    
    # For automation, skip HTML by default (uncomment to enable)
    # html_files = upload_directory(
    #     OUTPUT_BASE / 'html',
    #     S3_HTML_PREFIX,
    #     'Raw HTML data'
    # )
    html_files = 0
    print("  ⏭️  Skipping HTML files (uncomment in script to enable)")
    
    # Upload progress file
    progress_file = Path('scraping_progress.json')
    upload_file(
        progress_file,
        'scraped_data/scraping_progress.json',
        'Scraping progress'
    )
    
    # Save and upload summary
    summary['uploaded'] = {
        'json_files': json_files,
        'html_files': html_files,
        'summary_files': summaries_uploaded
    }
    
    upload_summary_file = Path('upload_summary.json')
    with open(upload_summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    upload_file(
        upload_summary_file,
        'scraped_data/upload_summary.json',
        'Upload summary'
    )
    
    # Final summary
    print(f"\n{'='*80}")
    print("UPLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"✅ JSON files uploaded: {json_files:,}")
    print(f"✅ HTML files uploaded: {html_files:,}")
    print(f"✅ Summary files uploaded: {summaries_uploaded}")
    print(f"\n📍 S3 Location: s3://{S3_BUCKET}/scraped_data/")
    print(f"\nView in console:")
    print(f"  https://s3.console.aws.amazon.com/s3/buckets/{S3_BUCKET}?prefix=scraped_data/")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
