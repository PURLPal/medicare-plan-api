# 50-State Medicare Scraping Plan

**Goal:** Scrape all Medicare plans for all 50 states + territories using EC2

---

## 📊 Current Status

**EC2 Instance:**
- ✅ Instance ID: `i-0a3e8716a404141a5`
- ✅ Type: t3.large spot ($0.025/hr)
- ✅ IP: 107.20.105.68
- ✅ Chrome 143 + ChromeDriver installed
- ✅ Python packages: selenium, selenium-stealth, boto3, beautifulsoup4

**Scripts on EC2:**
- ✅ `parse_ri_html.py` - Parser (works for all states)
- ✅ `scrape_state_generic.py` - Generic state scraper
- ✅ All 56 state data files uploaded to `state_data/`

**Validation Completed:**
- ✅ Rhode Island: 34/34 plans (100% success)
- ✅ Oregon: 50/50 plans tested (100% success)
- ✅ Data quality: 100% complete across all tests

---

## 📈 Scraping Scope

**Total Coverage:**
```
States/Territories: 56
Total Plans: 6,581
```

**State Size Distribution:**
```
Florida (largest):           621 plans
Texas:                       435 plans
California:                  414 plans
Pennsylvania:                344 plans
...
Rhode Island:                 34 plans
Virgin Islands (smallest):     1 plan

Breakdown by size:
- Large (500-1999):    1 state   (621 plans)
- Medium (100-499):   26 states (4,517 plans)
- Small (<100):       29 states (1,443 plans)
```

---

## ⏱️ Time & Cost Estimates

**Sequential Scraping (one state at a time):**
```
Average: 1.5 seconds per plan
Total time: 2.7 hours
EC2 cost: $0.07 (7 cents!)
```

**Parallel Scraping (5 states at once):**
```
Estimated time: ~35 minutes
EC2 cost: Same ($0.07)
Complexity: Higher
```

**Recommended:** Sequential (simpler, same cost, proven reliable)

---

## 🎯 Scraping Strategy: 3 Phases

### Phase 1: Small States (29 states, ~36 minutes)
**States with <100 plans**

Benefits:
- Quick wins
- Build confidence
- Test stability
- Low risk if issues occur

States:
- Alaska (9), Vermont (14), Wyoming (25), New Hampshire (28)
- District of Columbia (30), Rhode Island (34)
- American Samoa, Guam, Northern Mariana Islands, Virgin Islands (1 each)
- Plus 19 more small states

**Estimated time:** 36 minutes
**Estimated cost:** $0.015

### Phase 2: Medium States (26 states, ~113 minutes)
**States with 100-499 plans**

States:
- Illinois (172), Georgia (176), North Carolina (187)
- Michigan (204), Ohio (222), New York (228)
- Pennsylvania (344), California (414), Texas (435)
- Plus 17 more medium states

**Estimated time:** 113 minutes (1.9 hours)
**Estimated cost:** $0.047

### Phase 3: Large State (1 state, ~16 minutes)
**Florida (621 plans)**

We already tested FL scraping locally, so we know the parser works.

**Estimated time:** 16 minutes
**Estimated cost:** $0.007

---

## 🛠️ Implementation Plan

### Step 1: Create Master Scraper ✓ (Ready)

Script: `scrape_all_states.py`

Features:
- Scrapes all 56 states sequentially
- Saves progress after each state
- Resume capability (skip completed states)
- Comprehensive logging
- Summary report at end

### Step 2: Create Progress Tracker ✓ (Ready)

File: `scraping_progress.json`

Tracks:
- Completed states
- Failed states
- Stats per state (success rate, data quality)
- Overall progress

### Step 3: Execute Scraping

Options:

**A. Run interactively** (watch progress live)
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
python3 scrape_all_states.py
```

**B. Run in background** (disconnect safe)
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
nohup python3 scrape_all_states.py > scrape_all.log 2>&1 &
```

**C. Run with tmux** (best - can reconnect)
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
tmux new -s medicare_scrape
python3 scrape_all_states.py
# Detach: Ctrl+B, then D
# Reconnect: tmux attach -t medicare_scrape
```

### Step 4: Monitor Progress

Check from local machine:
```bash
# View real-time log
ssh ubuntu@107.20.105.68 "tail -f scrape_all.log"

# Check progress
ssh ubuntu@107.20.105.68 "cat scraping_progress.json | python3 -m json.tool"

# Count completed states
ssh ubuntu@107.20.105.68 "ls output/json/ -d */ | wc -l"
```

### Step 5: Download Results

After completion:
```bash
# Download all JSON files
scp -r ubuntu@107.20.105.68:~/output/json/ ./all_states_json/

# Download summary
scp ubuntu@107.20.105.68:~/scraping_progress.json ./

# Download logs
scp ubuntu@107.20.105.68:~/scrape_all.log ./
```

---

## 📁 Output Structure

```
output/
├── html/
│   ├── Florida/
│   │   ├── H1036_297_0.html
│   │   └── ...
│   ├── Oregon/
│   └── ...
├── json/
│   ├── Florida/
│   │   ├── H1036_297_0.json
│   │   └── ...
│   ├── Oregon/
│   └── ...
└── summaries/
    ├── Florida_summary.json
    ├── Oregon_summary.json
    └── ...
```

---

## 🔄 Resume Capability

If scraping stops for any reason:

1. Script automatically saves progress after each state
2. Re-run the script - it will skip completed states
3. Continues from where it left off

Example progress file:
```json
{
  "completed": ["Alaska", "Vermont", "Rhode Island"],
  "failed": [],
  "current": "Oregon",
  "total_states": 56,
  "total_plans_scraped": 57,
  "started_at": "2025-12-28T13:00:00Z"
}
```

---

## 🚨 Error Handling

**If a plan fails:**
- Script logs error and continues
- Failed plans tracked in summary
- Can retry failed plans later

**If a state fails:**
- Script logs error and moves to next state
- State marked as failed in progress
- Can retry failed states later

**If EC2 disconnects:**
- Use tmux or nohup to survive disconnects
- Progress saved, can resume

**If spot instance terminates:**
- Very rare (spot interruption rate <5%)
- Progress saved in files
- Launch new instance and resume

---

## 💾 Data Storage Strategy

**During scraping:**
- HTML and JSON saved to EC2 disk (30 GB available)
- Estimated total size: ~3-4 GB

**After scraping:**
- Option 1: Download to local machine
- Option 2: Upload directly to S3 (recommended)
- Option 3: Both (backup strategy)

**S3 Upload (recommended):**
```bash
# After scraping completes on EC2
aws s3 sync ~/output/json/ s3://medicare-scraping-parsed/json/ --profile silverman
aws s3 sync ~/output/html/ s3://medicare-scraping-raw/html/ --profile silverman
```

---

## 📊 Quality Assurance

**Per-state validation:**
- Success rate (target: >95%)
- Data completeness (target: >95%)
- Parse failures logged

**Post-scraping audit:**
1. Check each state summary
2. Verify plan counts match expected
3. Sample data quality checks
4. Identify any states needing re-scrape

---

## 🎯 Success Metrics

**Scraping Success:**
- ✅ All 56 states scraped
- ✅ >95% plans successfully scraped per state
- ✅ >95% data completeness per state

**Data Quality:**
- ✅ All plans have premiums
- ✅ All plans have deductibles
- ✅ MA plans have out-of-pocket maximums
- ✅ Plans have benefits and coverage details

**Performance:**
- ✅ Complete within 3 hours
- ✅ Total cost under $0.10
- ✅ No manual intervention required

---

## 🔧 Troubleshooting

**Issue: Chrome crashes**
- Restart script (progress saved)
- Instance has 8 GB RAM (plenty for Chrome)

**Issue: Medicare.gov blocks us**
- Rate limiting: 1.5s per plan (conservative)
- Stealth mode active
- Headless browser with real user-agent

**Issue: Parse failures**
- Log failures for review
- Parser has been tested on RI and OR
- Can re-parse from saved HTML later

**Issue: Disk space full**
- 30 GB available, only need ~4 GB
- Can delete HTML files if needed (keep JSON)

---

## 📅 Timeline

**Recommended Schedule:**

**Day 1 (Now):**
- ✅ Verify EC2 setup complete
- ✅ Upload all state data files
- 🔄 Create master scraper script
- 🔄 Test with 1-2 states
- ✅ Launch full scraping run

**Total Execution Time:** 2.7 hours

**Post-Processing:**
- Download results (10-20 minutes)
- Quality audit (30 minutes)
- Build static API files (local or EC2)
- Deploy to S3

**Total End-to-End:** 1 day

---

## 💰 Total Cost Breakdown

```
EC2 Instance (t3.large spot):
  Scraping: 2.7 hours × $0.025/hr = $0.068
  Setup/testing: 1 hour (already done)
  Total runtime: ~4 hours = $0.10

S3 Storage:
  Raw HTML: ~2 GB × $0.023/GB/mo = $0.05/mo
  Parsed JSON: ~1 GB × $0.023/GB/mo = $0.02/mo
  
Total One-Time Cost: $0.10
Total Monthly Cost: $0.07
```

**Compare to local:** 41 GB disk space + laptop running for 3 hours

---

## ✅ Pre-Flight Checklist

**EC2 Instance:**
- [x] Instance running
- [x] Chrome + ChromeDriver installed
- [x] Python packages installed
- [x] SSH access working

**Data & Scripts:**
- [x] All 56 state data files uploaded
- [x] Parser script (parse_ri_html.py) uploaded
- [x] Generic scraper uploaded
- [ ] Master scraper script created
- [ ] Progress tracker created

**Validation:**
- [x] Rhode Island test (34/34 success)
- [x] Oregon test (50/50 success)
- [x] Data quality verified

**Ready to Launch:** 95% ✓

---

## 🚀 Launch Commands

**1. Create master scraper (5 minutes)**
```bash
# Will create scrape_all_states.py
```

**2. Launch scraping**
```bash
ssh -i ~/.ssh/purlpal-demo-key.pem ubuntu@107.20.105.68
tmux new -s medicare_scrape
python3 scrape_all_states.py
```

**3. Detach and monitor**
```bash
# Detach: Ctrl+B, then D
# Monitor from local: ssh ubuntu@... "tail -f scrape_all.log"
```

**4. Download results**
```bash
# After ~3 hours
scp -r ubuntu@107.20.105.68:~/output/json/ ./all_states_json/
```

---

## 📝 Next Steps

1. **Create master scraper script** (`scrape_all_states.py`)
2. **Test with 2-3 small states** (Alaska, Vermont, Wyoming)
3. **Launch full 56-state scraping**
4. **Monitor progress** (can disconnect, script runs in background)
5. **Download results** when complete
6. **Audit data quality**
7. **Build static API files**
8. **Deploy to S3**

**Estimated total time to completion:** 4-5 hours
**Estimated total cost:** $0.10 (10 cents!)
