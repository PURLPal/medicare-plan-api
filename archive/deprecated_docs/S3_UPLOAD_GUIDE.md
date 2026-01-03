# S3 Upload Guide - EC2 to S3 Data Transfer

**Status: ✅ READY - AWS CLI configured and S3 access verified**

---

## Quick Commands

### After Scraping Completes

**Option 1: Automatic Upload (Recommended)**
```bash
# On EC2, run the upload script
python3 upload_to_s3.py
```

**Option 2: Manual AWS CLI**
```bash
# Upload parsed JSON data (most important)
aws s3 sync output/json/ s3://purlpal-medicare-api/scraped_data/json/

# Upload state summaries
aws s3 sync output/summaries/ s3://purlpal-medicare-api/scraped_data/summaries/

# Upload progress file
aws s3 cp scraping_progress.json s3://purlpal-medicare-api/scraped_data/

# Optional: Upload raw HTML (large files)
aws s3 sync output/html/ s3://purlpal-medicare-api/scraped_data/html/
```

---

## What's Configured

✅ **AWS CLI:** v2.32.24 installed on EC2  
✅ **Credentials:** Configured from silverman profile  
✅ **S3 Access:** Verified - can read/write to `purlpal-medicare-api`  
✅ **Upload Script:** `upload_to_s3.py` ready on EC2  

---

## S3 Structure

```
s3://purlpal-medicare-api/
└── scraped_data/
    ├── json/              # Parsed plan data (MOST IMPORTANT)
    │   ├── Florida/
    │   │   ├── H1036_297_0.json
    │   │   └── ... (621 files)
    │   ├── Oregon/
    │   │   └── ... (1,905 files)
    │   └── ... (54 more states)
    │
    ├── summaries/         # Per-state statistics
    │   ├── Florida_summary.json
    │   ├── Oregon_summary.json
    │   └── ... (56 files)
    │
    ├── html/              # Raw HTML (optional, large)
    │   ├── Florida/
    │   └── ...
    │
    ├── scraping_progress.json
    └── upload_summary.json
```

---

## Upload Estimates

**Parsed JSON Data:**
- Size: ~1-2 GB
- Files: ~6,581 JSON files
- Upload time: 2-5 minutes
- Cost: $0.00 (data transfer within AWS region)

**Raw HTML Data (optional):**
- Size: ~2-3 GB
- Files: ~6,581 HTML files
- Upload time: 5-10 minutes
- Cost: $0.00

**Storage Cost:**
- JSON: ~$0.02/month ($0.023/GB)
- HTML: ~$0.05/month (if uploaded)

---

## Complete Workflow

### 1. Scrape All States on EC2
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
tmux new -s medicare_scrape
python3 scrape_all_states.py
# Ctrl+B, then D to detach
```

### 2. Monitor Progress (from local machine)
```bash
# Check progress
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68 \
  "cat scraping_progress.json | python3 -m json.tool | head -20"

# Count completed states
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68 \
  "ls output/json/ -d */ 2>/dev/null | wc -l"
```

### 3. Upload to S3 (after scraping completes)
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
python3 upload_to_s3.py
```

### 4. Verify Upload
```bash
# List uploaded states
aws s3 ls s3://purlpal-medicare-api/scraped_data/json/ --profile silverman

# Check specific state
aws s3 ls s3://purlpal-medicare-api/scraped_data/json/Florida/ --profile silverman | wc -l

# Download summary to verify
aws s3 cp s3://purlpal-medicare-api/scraped_data/upload_summary.json . --profile silverman
```

### 5. Download to Local (optional, for backup)
```bash
# Download all JSON data
aws s3 sync s3://purlpal-medicare-api/scraped_data/json/ ./all_states_json/ --profile silverman

# Or download specific states
aws s3 sync s3://purlpal-medicare-api/scraped_data/json/Florida/ ./florida_json/ --profile silverman
```

### 6. Cleanup EC2 (after upload verified)
```bash
# Stop instance to save money
aws ec2 stop-instances --instance-ids i-0a3e8716a404141a5 --profile silverman

# Or terminate (can't restart, but saves more)
aws ec2 terminate-instances --instance-ids i-0a3e8716a404141a5 --profile silverman
```

---

## One-Line Complete Pipeline

From local machine, kick off everything:
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68 \
  "tmux new -d -s medicare 'python3 scrape_all_states.py && python3 upload_to_s3.py'"
```

Check progress:
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68 \
  "tail -50 scraping_progress.json"
```

---

## Advanced: Direct Integration

Add S3 upload to the scraper (automatically upload after each state):

```python
# In scrape_all_states.py, after each state completes:
import subprocess

def upload_state_to_s3(state_name):
    """Upload a completed state to S3 immediately."""
    cmd = f"aws s3 sync output/json/{state_name}/ s3://purlpal-medicare-api/scraped_data/json/{state_name}/"
    subprocess.run(cmd, shell=True)
    
    cmd = f"aws s3 cp output/summaries/{state_name}_summary.json s3://purlpal-medicare-api/scraped_data/summaries/"
    subprocess.run(cmd, shell=True)
```

Benefits:
- Data backed up as you go
- Can free disk space during long runs
- No need for separate upload step

---

## Troubleshooting

**"Unable to locate credentials"**
```bash
# Reconfigure AWS credentials
aws configure
# Enter access key and secret from silverman profile
```

**"Access Denied" errors**
```bash
# Verify credentials work
aws sts get-caller-identity

# Check bucket access
aws s3 ls s3://purlpal-medicare-api/
```

**Upload is slow**
```bash
# Use AWS CLI sync (faster than copying individual files)
aws s3 sync output/json/ s3://purlpal-medicare-api/scraped_data/json/ --size-only

# Skip unchanged files with --size-only
```

**Out of disk space**
```bash
# Upload what you have, then delete local files
python3 upload_to_s3.py
rm -rf output/html/  # Delete raw HTML (already in S3)
```

---

## Summary

**Everything is ready for seamless S3 uploads!**

1. ✅ AWS CLI installed on EC2
2. ✅ Credentials configured (silverman profile)
3. ✅ S3 access verified
4. ✅ Upload script ready (`upload_to_s3.py`)
5. ✅ Can upload 6,581 JSON files in ~2-5 minutes
6. ✅ $0.00 transfer cost (within AWS)
7. ✅ ~$0.02/month storage cost

**After scraping completes, just run:**
```bash
python3 upload_to_s3.py
```

**All data will be in S3 at:**
```
s3://purlpal-medicare-api/scraped_data/
```
