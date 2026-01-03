# AWS Migration Plan - Medicare Scraping & Processing

**Goal:** Move entire Medicare data workflow to AWS to eliminate 41 GB local disk usage

---

## 📊 Current State Analysis

### Local Storage (41.3 GB Total)
```
static_api/          39.0 GB (95%) - Final API files, already in S3
mock_api/             1.8 GB (4%)  - Intermediate processing
scraped_html_all/   329 MB (1%)  - Raw HTML from scraping
scraped_json_all/    67 MB (<1%) - Parsed plan data
raw_*_plans/        140 MB (<1%) - State-specific raw HTML
state_data/         4.6 MB (<1%) - State metadata
```

### Current Workflow
1. **Scrape** (local) → Raw HTML files (329 MB)
2. **Parse** (local) → JSON files (67 MB)
3. **Build API** (local) → static_api files (39 GB)
4. **Deploy** → aws s3 sync to S3 (39 GB transfer)

**Problem:** Step 3 duplicates everything locally before uploading, requires 39+ GB free space

---

## 🏗️ AWS Architecture Options

### Option A: EC2-Based (Simplest Migration)

**Infrastructure:**
- **EC2 Instance:** t3.large (2 vCPU, 8 GB RAM, $60/mo)
- **EBS Volume:** 100 GB gp3 ($8/mo)
- **S3 Buckets:**
  - `medicare-scraping-raw/` - Raw HTML (329 MB)
  - `medicare-scraping-parsed/` - Parsed JSON (67 MB)
  - `medicare-scraping-working/` - Intermediate files (1.8 GB)
  - `purlpal-medicare-api/` - Final API (existing, 39 GB)

**Workflow:**
```
EC2 Instance:
├─ Scrape state → Upload HTML to S3 immediately
├─ Parse from S3 → Upload JSON to S3 immediately
├─ Build API from S3 → Stream directly to final S3 bucket
└─ No local storage accumulation (only temp files)
```

**Cost:** ~$70/mo (run only when needed, stop when idle)

**Pros:**
- Simple migration, existing scripts work with minor mods
- Full control, can SSH and debug
- Pay only when running
- Easy to scale up for heavy processing

**Cons:**
- Must manually start/stop instance
- Still need some EC2 disk (but 100 GB is plenty)

---

### Option B: Serverless (Most Cost-Effective)

**Infrastructure:**
- **AWS Batch + Fargate:** For scraping jobs
- **Lambda:** For parsing and building (15 min timeout limit)
- **Step Functions:** Orchestrate workflow
- **S3 Buckets:** Same as Option A
- **EventBridge:** Schedule scraping runs

**Workflow:**
```
1. EventBridge triggers Step Function
2. Step Function launches Batch job per state
3. Batch job (Fargate):
   - Runs scraper in container
   - Uploads HTML directly to S3
   - Triggers Lambda for parsing
4. Lambda reads from S3, parses, writes back to S3
5. Lambda builds API files directly in S3
```

**Cost:** ~$5-15/mo (pay per execution)

**Pros:**
- Zero maintenance, fully automated
- Pay only for actual compute time
- Auto-scales for multiple states
- No idle costs

**Cons:**
- Complex setup initially
- Lambda 15-min timeout (must split large builds)
- Container image needed for Selenium scraping
- Debugging harder (CloudWatch logs only)

---

### Option C: Hybrid (Recommended)

**Infrastructure:**
- **EC2 Spot Instance:** t3.large spot (~$18/mo, 70% cheaper)
- **Auto-scaling:** Launch on-demand, terminate when done
- **Lambda:** For light parsing tasks
- **S3:** All data storage
- **CloudWatch Events:** Trigger workflows

**Workflow:**
```
1. Lambda detects new state to scrape
2. Launch EC2 spot instance via AWS SDK
3. EC2 runs scraper, streams to S3
4. EC2 runs parser, streams to S3
5. EC2 builds API, streams to S3
6. EC2 self-terminates
7. Lambda handles post-processing
```

**Cost:** ~$25/mo (mostly storage, minimal compute)

**Pros:**
- Best balance of cost and simplicity
- Can debug on EC2 when needed
- Automated but not over-engineered
- 70% cheaper than on-demand EC2

**Cons:**
- Spot instances can be interrupted (rare)
- Slightly more complex than pure EC2

---

## 💰 Detailed Cost Estimates

### Storage Costs (S3)
```
Raw HTML:              329 MB  × $0.023/GB = $0.01/mo
Parsed JSON:            67 MB  × $0.023/GB = $0.00/mo
Working files:         1.8 GB  × $0.023/GB = $0.04/mo
Final API:              39 GB  × $0.023/GB = $0.90/mo (already paying)
---------------------------------------------------------------
Total S3:                                   = $0.95/mo
```

### Compute Costs (Hybrid Approach)
```
EC2 Spot (t3.large):    $0.025/hr × 20 hrs/mo = $0.50/mo
Lambda (parsing):        $0.20/1M requests     = $0.10/mo
Data Transfer OUT:       1 GB free, minimal    = $0.00/mo
CloudWatch Logs:         500 MB/mo             = $0.50/mo
---------------------------------------------------------------
Total Compute:                                = $1.10/mo
```

### Total AWS Cost: ~$2/mo (vs 41 GB local disk)

---

## 🔄 Migration Strategy

### Phase 1: Move Existing Data to S3 (One-time)
```bash
# Upload all existing data
aws s3 sync scraped_html_all/ s3://medicare-scraping-raw/html/
aws s3 sync scraped_json_all/ s3://medicare-scraping-parsed/json/
aws s3 sync mock_api/ s3://medicare-scraping-working/mock_api/
aws s3 sync state_data/ s3://medicare-scraping-working/state_data/

# Delete local copies after verification
```

### Phase 2: Modify Scripts to Use S3

**Scraper modifications:**
```python
# OLD: Save locally
with open(f'scraped_html_all/{plan_id}.html', 'w') as f:
    f.write(html_content)

# NEW: Upload to S3 immediately
import boto3
s3 = boto3.client('s3')
s3.put_object(
    Bucket='medicare-scraping-raw',
    Key=f'html/{state}/{plan_id}.html',
    Body=html_content.encode('utf-8')
)
```

**Parser modifications:**
```python
# OLD: Read local file
with open(f'scraped_html_all/{plan_id}.html') as f:
    html = f.read()

# NEW: Read from S3
obj = s3.get_object(Bucket='medicare-scraping-raw', Key=f'html/{state}/{plan_id}.html')
html = obj['Body'].read().decode('utf-8')

# Save parsed JSON directly to S3
s3.put_object(
    Bucket='medicare-scraping-parsed',
    Key=f'json/{state}/{plan_id}.json',
    Body=json.dumps(parsed_data).encode('utf-8')
)
```

**API Builder modifications:**
```python
# OLD: Write to local static_api/ then sync
with open(f'static_api/medicare/zip/{zip_code}.json', 'w') as f:
    json.dump(data, f)

# NEW: Write directly to final S3 bucket
s3.put_object(
    Bucket='purlpal-medicare-api',
    Key=f'medicare/zip/{zip_code}.json',
    Body=json.dumps(data, separators=(',', ':')).encode('utf-8'),
    ContentType='application/json'
)
```

### Phase 3: Setup EC2 Auto-Launch (Optional)

**Create launch template:**
```bash
aws ec2 create-launch-template \
  --launch-template-name medicare-scraper \
  --version-description "Medicare scraping instance" \
  --launch-template-data '{
    "ImageId": "ami-xxx",
    "InstanceType": "t3.large",
    "IamInstanceProfile": {"Name": "medicare-scraper-role"},
    "UserData": "<base64-encoded-startup-script>"
  }'
```

**User data script (runs on launch):**
```bash
#!/bin/bash
cd /home/ubuntu/medicare_overview_test
git pull
python3 scrape_next_state.py  # Your scraping logic
python3 parse_latest.py         # Parse new data
python3 build_api.py            # Build API files
# Auto-terminate when done
aws ec2 terminate-instances --instance-ids $(ec2-metadata --instance-id | cut -d ' ' -f 2)
```

### Phase 4: Local Cleanup
```bash
# Once verified on AWS, delete local data
rm -rf static_api/        # 39 GB freed
rm -rf mock_api/          # 1.8 GB freed
rm -rf scraped_html_all/  # 329 MB freed
rm -rf scraped_json_all/  # 67 MB freed
rm -rf raw_*_plans/       # 140 MB freed

# Keep only scripts
# Total freed: 41+ GB → 0 GB
```

---

## 📋 Implementation Checklist

### Week 1: Setup S3 Infrastructure
- [ ] Create S3 buckets with lifecycle policies
- [ ] Upload existing data to S3
- [ ] Verify data integrity (checksums)
- [ ] Test S3 read/write from scripts

### Week 2: Modify Scripts
- [ ] Update scraper to use S3 (test with 1 state)
- [ ] Update parser to use S3
- [ ] Update API builder to stream to S3
- [ ] Add error handling for S3 operations

### Week 3: EC2 Setup (if using)
- [ ] Create EC2 instance with required software
- [ ] Create AMI for easy relaunch
- [ ] Test full scrape → parse → build pipeline
- [ ] Setup CloudWatch monitoring

### Week 4: Automation & Cleanup
- [ ] Create auto-launch scripts
- [ ] Document new workflow
- [ ] Delete local data after verification
- [ ] Monitor costs for first month

---

## 🚀 Quick Start - Minimal Migration

**If you want to start immediately with minimal changes:**

1. **Keep scripts on local machine**
2. **Only change output destinations:**
   ```python
   # Add to top of each script
   import boto3
   s3 = boto3.client('s3')
   
   # Replace all file writes with S3 uploads
   # Replace all file reads with S3 downloads (only when needed)
   ```

3. **Benefits:**
   - Immediately eliminate 39 GB (static_api)
   - Raw data stays in cloud (329 MB)
   - Can delete local files right after processing
   - No need to run builds locally

4. **Your machine only needs:**
   - Scripts (~100 MB)
   - Temp files during active scraping (deleted after upload)
   - Total: < 500 MB vs 41 GB

---

## 🔐 Security Considerations

1. **IAM Roles:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
       "Resource": [
         "arn:aws:s3:::medicare-scraping-*",
         "arn:aws:s3:::medicare-scraping-*/*",
         "arn:aws:s3:::purlpal-medicare-api",
         "arn:aws:s3:::purlpal-medicare-api/*"
       ]
     }]
   }
   ```

2. **S3 Bucket Policies:**
   - Enable versioning (protect against accidental deletion)
   - Lifecycle rules (delete raw HTML after 90 days)
   - Server-side encryption (AES-256)

3. **Credentials:**
   - Use EC2 instance profiles (no hardcoded keys)
   - Use AWS SSM Parameter Store for secrets

---

## 📈 Scaling for Future Growth

**If you add more states:**
- S3 scales infinitely (no concern)
- Lambda can handle 1,000 concurrent executions
- EC2 can be upgraded to larger instance
- Spot fleets can launch multiple instances in parallel

**Cost at 50 states (10x current):**
- Storage: ~$5/mo (400 GB S3)
- Compute: ~$10/mo (more Lambda/EC2 time)
- Total: ~$15/mo (still cheaper than local disk)

---

## ✅ Recommended Approach

**Start with Option C (Hybrid) + Quick Start:**

1. **This week:** Modify scripts to write directly to S3
2. **Next week:** Test full workflow, delete local static_api/
3. **Month 2:** Setup EC2 spot auto-launch if needed
4. **Future:** Consider Lambda/Batch if scraping 50+ states

**This gives you:**
- ✅ Immediate 39 GB savings
- ✅ Minimal code changes
- ✅ ~$2/mo cost
- ✅ Can scale later if needed
- ✅ Keep development flexibility
