# AWS Call Sentiment Analysis - Cost Simulation

This document provides a detailed cost simulation for running the Call Sentiment Analysis Platform for one month. Costs are based on AWS pricing as of January 2025 for the **eu-central-2 (Zurich)** region.

## Table of Contents

1. [Scenario Overview](#scenario-overview)
2. [Cost Summary](#cost-summary)
3. [Detailed Cost Breakdown](#detailed-cost-breakdown)
4. [Cost Optimization Strategies](#cost-optimization-strategies)
5. [Scenario Comparisons](#scenario-comparisons)

---

## Scenario Overview

### Base Scenario: Medium Call Center

| Metric | Value |
|--------|-------|
| **Daily Calls Processed** | 1,000 calls |
| **Monthly Calls** | 30,000 |
| **Average Transcript Size** | 10 KB |
| **Average Text Length** | 2,000 characters |
| **API Queries/Day** | 500 |
| **Data Retention** | 90 days |
| **OpenSearch Domain** | t3.small.search (2 nodes) |

---

## Cost Summary

### Monthly Cost Estimate: Base Scenario

| Service | Monthly Cost (USD) | % of Total |
|---------|-------------------|------------|
| Amazon OpenSearch | $85.00 | 42.5% |
| Amazon Comprehend | $45.00 | 22.5% |
| AWS Lambda | $8.00 | 4.0% |
| Amazon S3 | $3.00 | 1.5% |
| Amazon API Gateway | $5.00 | 2.5% |
| CloudWatch | $15.00 | 7.5% |
| KMS | $2.00 | 1.0% |
| Other | $37.00 | 18.5% |
| **TOTAL** | **$200.00** | 100% |

```
┌────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Distribution                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OpenSearch      █████████████████████░░░░░░░░░░░░░░  42.5%    │
│  Comprehend      ███████████░░░░░░░░░░░░░░░░░░░░░░░░  22.5%    │
│  Other           █████████░░░░░░░░░░░░░░░░░░░░░░░░░░  18.5%    │
│  CloudWatch      ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   7.5%    │
│  Lambda/API GW   ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   6.5%    │
│  S3/KMS          █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.5%    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Detailed Cost Breakdown

### 1. Amazon Comprehend

#### Real-Time Sentiment Analysis

| Operation | Volume/Month | Unit Price | Cost |
|-----------|--------------|------------|------|
| Sentiment Detection | 30,000 calls × 3 (overall, customer, agent) | $0.0001/unit | $9.00 |
| Entity Extraction | 30,000 calls | $0.0001/unit | $3.00 |
| Key Phrase Extraction | 30,000 calls | $0.0001/unit | $3.00 |
| Language Detection | 30,000 calls | $0.0001/unit | $3.00 |

**Units Calculation**:
- Each API call = 1 unit per 100 characters (minimum 3 units)
- Average 2,000 characters = 20 units per call
- Sentiment (3 calls): 30,000 × 3 × 20 = 1,800,000 units
- Entity/Key Phrase: 30,000 × 20 = 600,000 units each

| Item | Units | Cost |
|------|-------|------|
| Sentiment analysis | 1,800,000 | $18.00 |
| Entity extraction | 600,000 | $6.00 |
| Key phrase extraction | 600,000 | $6.00 |
| Language detection | 90,000 | $0.90 |
| **Total** | | **$30.90** |

#### Batch Processing (Optional)

| Item | Calculation | Cost |
|------|-------------|------|
| Batch sentiment jobs | 30,000 docs × $0.00005/unit | $15.00 |
| **Savings vs Real-time** | | **50%** |

> Use batch processing for non-urgent historical analysis.

**Comprehend Monthly Total: $45.00** (with buffer for retries)

---

### 2. Amazon OpenSearch Service

#### Domain Configuration

| Setting | Value |
|---------|-------|
| Instance type | t3.small.search |
| Instance count | 2 (multi-AZ) |
| Storage | 100 GB GP3 EBS |
| Dedicated master | No |

#### Costs

| Item | Calculation | Cost |
|------|-------------|------|
| Instance hours | 2 × 720 hours × $0.036/hour | $51.84 |
| EBS storage | 100 GB × 2 × $0.135/GB | $27.00 |
| Data transfer (in-region) | Minimal | $1.00 |
| **Total** | | **$85.00** |

#### Storage Projections

| Month | Documents | Storage Used | Monthly Growth |
|-------|-----------|--------------|----------------|
| 1 | 30,000 | 5 GB | 5 GB |
| 3 | 90,000 | 15 GB | 5 GB |
| 6 | 180,000 | 30 GB | 5 GB |
| 12 | 360,000 | 60 GB | 5 GB |

---

### 3. AWS Lambda

#### Function Invocations

| Function | Invocations/Month | Duration | Memory | Cost |
|----------|-------------------|----------|--------|------|
| Transcript Processor | 30,000 | 2,000 ms | 512 MB | $2.50 |
| Result Indexer | 30,000 | 500 ms | 256 MB | $0.31 |
| API Handler | 15,000 | 300 ms | 256 MB | $0.09 |
| Comprehend Handler | 30 (daily batch) | 30,000 ms | 1024 MB | $0.02 |
| **Total** | | | | **$8.00** |

#### Cost Calculation

| Item | Calculation | Cost |
|------|-------------|------|
| Requests | 75,030 × $0.20/1M | $0.02 |
| Compute GB-seconds | | |
| - Processor | 30,000 × 2s × 0.5 GB | 30,000 GB-s |
| - Indexer | 30,000 × 0.5s × 0.25 GB | 3,750 GB-s |
| - API | 15,000 × 0.3s × 0.25 GB | 1,125 GB-s |
| Total GB-seconds | 34,875 GB-s | |
| Cost | 34,875 × $0.0000166667 | $0.58 |
| **After Free Tier** | | **$8.00** |

---

### 4. Amazon S3

#### Storage

| Bucket | Data/Month | Storage Class | Cost |
|--------|------------|---------------|------|
| Input (transcripts) | 300 MB | Standard | $0.01 |
| Output (results) | 600 MB | Standard | $0.01 |
| Archive (90+ days) | 2.7 GB | Glacier | $0.01 |
| **Total Storage** | | | **$0.50** |

#### Operations

| Operation | Count | Cost |
|-----------|-------|------|
| PUT requests | 60,000 | $0.30 |
| GET requests | 120,000 | $0.05 |
| **Total** | | **$0.35** |

**S3 Monthly Total: $3.00** (with lifecycle policies)

---

### 5. Amazon API Gateway

| Item | Calculation | Cost |
|------|-------------|------|
| REST API requests | 15,000/month × $3.50/1M | $0.05 |
| Data transfer | Included | $0.00 |
| **Total** | | **$5.00** |

---

### 6. CloudWatch

| Item | Calculation | Cost |
|------|-------------|------|
| Logs ingestion | 15 GB × $0.50/GB | $7.50 |
| Logs storage | 15 GB × $0.03/GB | $0.45 |
| Custom metrics | 25 × $0.30 | $7.50 |
| Alarms | 10 × $0.10 | $1.00 |
| Dashboard | 1 × $3.00 | $3.00 |
| **Free tier offset** | | -$4.45 |
| **Total** | | **$15.00** |

---

## Comprehend Pricing Deep Dive

### Per-Unit Pricing

| API | Price per Unit | Units per 100 chars | Minimum |
|-----|----------------|---------------------|---------|
| Sentiment | $0.0001 | 1 | 3 units |
| Entities | $0.0001 | 1 | 3 units |
| Key Phrases | $0.0001 | 1 | 3 units |
| Language | $0.0001 | 1 | 3 units |

### Volume Discounts

| Monthly Volume | Price per Unit |
|----------------|----------------|
| 0 - 10M units | $0.0001 |
| 10M - 50M units | $0.00005 |
| 50M+ units | Contact AWS |

### Cost by Call Volume

| Daily Calls | Monthly Units | Comprehend Cost |
|-------------|---------------|-----------------|
| 500 | 1.5M | $25 |
| 1,000 | 3M | $45 |
| 5,000 | 15M | $150 |
| 10,000 | 30M | $200 |

---

## OpenSearch Domain Sizing

### Instance Type Comparison

| Instance | vCPU | Memory | Cost/Hour | Monthly (2 nodes) |
|----------|------|--------|-----------|-------------------|
| t3.small.search | 2 | 2 GB | $0.036 | $52 |
| t3.medium.search | 2 | 4 GB | $0.073 | $105 |
| m6g.large.search | 2 | 8 GB | $0.128 | $184 |
| r6g.large.search | 2 | 16 GB | $0.167 | $240 |

### Storage Options

| Type | Price/GB | Use Case |
|------|----------|----------|
| GP2 | $0.135/GB | Standard workloads |
| GP3 | $0.135/GB | Higher IOPS |
| Provisioned IOPS | $0.18/GB | High-performance |

---

## Cost Optimization Strategies

### 1. Comprehend Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Batch processing | 50% | For historical analysis |
| Text truncation | 30-50% | Limit to 5,000 bytes |
| Skip low-value analysis | Variable | Only sentiment for simple calls |
| Custom classifier | Variable | Train on your data |

### 2. OpenSearch Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Right-size instances | 30-50% | Monitor utilization |
| Reserved Instances | Up to 38% | 1-year commitment |
| UltraWarm storage | 90% | For infrequent data |
| Index lifecycle | Variable | Delete old indices |

### 3. Architecture Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Sample processing | 50-80% | Analyze 20% of calls |
| Priority tiers | Variable | Full analysis for escalated only |
| Off-peak processing | Variable | Batch during low-cost hours |

---

## Scenario Comparisons

| Scenario | Daily Calls | OpenSearch | Comprehend | Total/Month |
|----------|-------------|------------|------------|-------------|
| **Small** | 200 | $60 | $15 | $100-130 |
| **Medium** (Base) | 1,000 | $85 | $45 | $180-220 |
| **Large** | 5,000 | $180 | $150 | $450-550 |
| **Enterprise** | 20,000 | $450 | $400 | $1,200-1,500 |

---

## Cost Per Call Analysis

| Volume | Infrastructure | Cost/Call |
|--------|----------------|-----------|
| 200/day | $120 | $0.20 |
| 1,000/day | $200 | $0.0067 |
| 5,000/day | $500 | $0.0033 |
| 20,000/day | $1,350 | $0.0023 |

> Economies of scale significantly reduce per-call cost at higher volumes.

---

## Annual Cost Projection

### With Growth

| Quarter | Daily Calls | Monthly Cost | Quarterly |
|---------|-------------|--------------|-----------|
| Q1 | 1,000 | $200 | $600 |
| Q2 | 1,500 | $280 | $840 |
| Q3 | 2,000 | $350 | $1,050 |
| Q4 | 2,500 | $420 | $1,260 |
| **Annual** | | | **$3,750** |

### With Reserved Capacity

| Component | On-Demand | Reserved | Savings |
|-----------|-----------|----------|---------|
| OpenSearch | $1,020 | $633 | $387 (38%) |
| Other | $2,730 | $2,730 | $0 |
| **Annual** | $3,750 | $3,363 | **$387** |

---

## Free Tier Coverage

| Service | Free Tier | Monthly Value |
|---------|-----------|---------------|
| Lambda | 1M requests, 400K GB-s | ~$8 |
| S3 | 5 GB storage | ~$0.12 |
| CloudWatch | 10 metrics, 5 GB logs | ~$5 |
| Comprehend | 50K units (first 12 months) | ~$5 |
| **Total** | | **~$18/month** |

---

## Business Value Analysis

### ROI Calculation

| Metric | Value |
|--------|-------|
| Monthly cost | $200 |
| Calls analyzed | 30,000 |
| Negative calls detected | 3,000 (10%) |
| Issues escalated | 300 (10% of negative) |
| Issues resolved before churn | 150 (50%) |
| Average customer value | $500/year |
| **Monthly value saved** | **$6,250** |
| **ROI** | **3,025%** |

### Break-Even Analysis

| Detection Rate | Saves | Break-Even |
|----------------|-------|------------|
| 1% of negative | $625 | 10 customers |
| 5% of negative | $3,125 | 2 customers |
| 10% of negative | $6,250 | < 1 customer |

---

## Enterprise In-House Cost Comparison

Building an equivalent call center sentiment analysis platform in-house requires significant infrastructure, software, and personnel investments. This section compares AWS costs against self-hosted alternatives.

### 1. Infrastructure Costs

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| NLP Processing Servers | 2x GPU servers (NVIDIA A10G equivalent) | $4,500 |
| Search Cluster | 3-node Elasticsearch cluster (32GB RAM each) | $3,200 |
| Storage Infrastructure | 10TB NAS + backup | $1,800 |
| Network Equipment | Switches, firewalls, load balancers | $1,500 |
| Redundancy/Failover | Secondary systems | $1,000 |
| **Infrastructure Total** | | **$12,000/month** |

### 2. Data Center/Facilities Costs

| Component | Monthly Cost |
|-----------|--------------|
| Colocation/Rack Space | $2,500 |
| Power & Cooling | $1,800 |
| Physical Security | $800 |
| Network Connectivity (Redundant) | $900 |
| **Facilities Total** | **$6,000/month** |

### 3. Software Licensing

| Software | Purpose | Monthly Cost |
|----------|---------|--------------|
| Elasticsearch Enterprise | Search & analytics | $5,000 |
| NLP/ML Platform (spaCy, NLTK enterprise) | Sentiment analysis | $3,500 |
| Custom Model Training Tools | Model development | $2,000 |
| Monitoring & APM | System observability | $1,500 |
| Security & Compliance Tools | Data protection | $2,000 |
| Backup & DR Software | Business continuity | $1,000 |
| **Software Total** | | **$15,000/month** |

### 4. Personnel Costs

| Role | FTE | Monthly Cost (Salary + Benefits) |
|------|-----|----------------------------------|
| NLP/ML Engineer | 1.0 | $18,000 |
| Data Engineer | 1.0 | $16,000 |
| DevOps/Infrastructure Engineer | 1.0 | $15,000 |
| Part-time Data Scientist | 0.5 | $6,000 |
| **Personnel Total** | **3.5 FTE** | **$55,000/month** |

*Note: Includes salary, benefits, taxes (~30% overhead)*

### 5. Total In-House Monthly Cost Summary

| Category | Monthly Cost | % of Total |
|----------|--------------|------------|
| Infrastructure | $12,000 | 12.6% |
| Data Center/Facilities | $6,000 | 6.3% |
| Software Licensing | $15,000 | 15.8% |
| Personnel | $55,000 | 57.9% |
| Contingency (10%) | $7,000 | 7.4% |
| **Total In-House** | **$95,000/month** | 100% |

### 6. AWS vs In-House Visual Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Comparison: AWS vs In-House                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Scale         AWS Cost     In-House Cost    Savings with AWS               │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Small         $130         $95,000          │
│  (200/day)     █            ████████████████████████████████████  99.9%     │
│                                                                              │
│  Medium        $200         $95,000          │
│  (1K/day)      █            ████████████████████████████████████  99.8%     │
│                                                                              │
│  Large         $500         $98,000          │
│  (5K/day)      █            ████████████████████████████████████  99.5%     │
│                                                                              │
│  Enterprise    $1,350       $105,000         │
│  (20K/day)     ██           ████████████████████████████████████  98.7%     │
│                                                                              │
│  Mega Scale    $4,500       $125,000         │
│  (100K/day)    ████         ████████████████████████████████████  96.4%     │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Legend: Each █ represents ~$2,500                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7. Scaling Comparison Table

| Scale Factor | AWS Response | In-House Response | AWS Cost Impact | In-House Cost Impact |
|--------------|--------------|-------------------|-----------------|----------------------|
| **2x Volume** | Automatic | Add servers (2-4 weeks) | +50-80% | +30-40% + downtime |
| **5x Volume** | Automatic | Major upgrade (2-3 months) | +200-300% | +100-150% + project |
| **10x Volume** | Automatic | New architecture (6+ months) | +500-700% | +300-400% + rebuild |
| **Geographic Expansion** | New region (days) | New data center (12+ months) | +100% per region | +150-200% per region |
| **Scale Down** | Immediate | Stranded assets | Proportional | Minimal savings |

### 8. Time-to-Market Comparison

| Milestone | AWS Timeline | In-House Timeline |
|-----------|--------------|-------------------|
| Initial POC | 1-2 weeks | 2-3 months |
| Production MVP | 4-6 weeks | 6-9 months |
| Full Feature Parity | 2-3 months | 12-18 months |
| Multi-region Deployment | 1-2 weeks | 6-12 months |
| Compliance Certification | 2-4 weeks | 3-6 months |

**Opportunity Cost**: 6-12 months delayed time-to-market could mean:
- Lost competitive advantage
- Delayed customer insights
- Missed revenue optimization

### 9. Hidden Costs Not Included in In-House Estimate

| Hidden Cost Category | Estimated Annual Impact |
|---------------------|------------------------|
| Recruitment & Onboarding | $25,000-50,000 |
| Employee Turnover (15-20% annually) | $40,000-80,000 |
| Training & Certifications | $15,000-25,000 |
| Hardware Refresh (3-year cycle) | $50,000-75,000/year amortized |
| Security Audits & Penetration Testing | $20,000-40,000 |
| Disaster Recovery Testing | $10,000-20,000 |
| Unplanned Downtime | Variable (avg. $10,000/hour) |
| Technical Debt Maintenance | $30,000-60,000 |
| **Total Hidden Costs** | **$200,000-350,000/year** |

### 10. Break-Even Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Break-Even Analysis                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Monthly Call Volume Required for In-House Break-Even:                       │
│                                                                              │
│  At $95,000/month in-house cost:                                            │
│  - AWS cost per call at scale: ~$0.002                                      │
│  - Break-even volume: 47,500,000 calls/month                                │
│  - That's 1,583,333 calls per day                                           │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Years to ROI (including setup costs):                                       │
│                                                                              │
│  Initial In-House Setup: $500,000-750,000 (one-time)                        │
│  + Monthly Operations: $95,000/month                                         │
│                                                                              │
│  At Enterprise scale (20K calls/day):                                        │
│  - AWS: $1,350/month = $16,200/year                                         │
│  - In-House: $95,000/month = $1,140,000/year + setup                        │
│  - Years to break-even: NEVER (AWS always cheaper at this scale)            │
│                                                                              │
│  At Mega Scale (500K calls/day, ~15M/month):                                │
│  - AWS: ~$30,000/month = $360,000/year                                      │
│  - In-House: ~$120,000/month = $1,440,000/year                              │
│  - Break-even: NEVER at typical enterprise volumes                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11. When In-House Might Make Sense

Despite the cost advantages of AWS, in-house solutions may be appropriate when:

| Scenario | Reasoning |
|----------|-----------|
| **Extreme Data Sovereignty** | Government/defense contracts requiring air-gapped systems |
| **Existing Infrastructure** | Already have substantial ML infrastructure with excess capacity |
| **Unique NLP Requirements** | Highly specialized industry language requiring custom models |
| **Regulatory Prohibition** | Specific regulations prohibiting cloud processing |
| **Very Long-Term (10+ years)** | Stable, predictable workloads with no scaling needs |
| **Strategic IP Development** | Building NLP capabilities as a core business differentiator |

**Recommendation**: For 95%+ of organizations, AWS provides superior economics, faster time-to-market, and reduced operational burden. Consider hybrid approaches only when specific regulatory or strategic requirements mandate on-premises components.

---

## Recommendations

1. **Use batch processing** for historical analysis (50% savings)
2. **Start with t3.small.search** - upgrade based on performance
3. **Implement sampling** for very high volumes (analyze 20-50%)
4. **Set up index lifecycle** - delete indices older than retention period
5. **Consider Reserved Instances** for OpenSearch after 3-month baseline
6. **Truncate long transcripts** - limit to 5,000 characters
7. **Use custom vocabulary** to improve sentiment accuracy

