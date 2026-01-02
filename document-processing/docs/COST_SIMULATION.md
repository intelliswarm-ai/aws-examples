# AWS ML Document Processing - Cost Simulation

This document provides a detailed cost simulation for running the Intelligent Document Processing Platform for one month. Costs are based on AWS pricing as of January 2025 for the **eu-central-2 (Zurich)** region.

## Table of Contents

1. [Scenario Overview](#scenario-overview)
2. [Cost Summary](#cost-summary)
3. [Detailed Cost Breakdown](#detailed-cost-breakdown)
4. [Cost Optimization Strategies](#cost-optimization-strategies)
5. [Scenario Comparisons](#scenario-comparisons)

---

## Scenario Overview

### Base Scenario: Medium-Volume Document Processing

| Metric | Value |
|--------|-------|
| **Documents Processed** | 5,000/month |
| **Avg Document Pages** | 10 pages |
| **Audio Files (Transcribe)** | 500/month (avg 5 min) |
| **Images Analyzed** | 2,000/month |
| **Bedrock Requests** | 10,000/month |
| **SageMaker Inference** | 5,000/month |

---

## Cost Summary

### Monthly Cost Estimate: Base Scenario

| Service | Monthly Cost (USD) | % of Total |
|---------|-------------------|------------|
| Amazon Textract | $75.00 | 25.8% |
| Amazon Transcribe | $30.00 | 10.3% |
| Amazon Comprehend | $25.00 | 8.6% |
| Amazon Rekognition | $10.00 | 3.4% |
| Amazon Bedrock | $100.00 | 34.4% |
| Amazon SageMaker | $25.00 | 8.6% |
| AWS Lambda | $3.00 | 1.0% |
| AWS Step Functions | $5.00 | 1.7% |
| Amazon S3 | $5.00 | 1.7% |
| CloudWatch | $6.00 | 2.1% |
| Other (KMS, etc.) | $6.00 | 2.1% |
| **TOTAL** | **$290.00** | 100% |

```
┌────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Distribution                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bedrock         █████████████████░░░░░░░░░░░░░░░░░░  34.4%    │
│  Textract        █████████████░░░░░░░░░░░░░░░░░░░░░░  25.8%    │
│  Transcribe      █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10.3%    │
│  Comprehend      ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.6%    │
│  SageMaker       ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.6%    │
│  Rekognition     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   3.4%    │
│  Other           ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   6.6%    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Detailed Cost Breakdown

### 1. Amazon Textract

#### Document Analysis

| Feature | Volume | Unit Price | Cost |
|---------|--------|------------|------|
| Detect Text (pages) | 50,000 | $1.50/1000 | $75.00 |
| Analyze Document (forms) | 10,000 | $50/1000 | $500.00 |
| Analyze Document (tables) | 5,000 | $15/1000 | $75.00 |

**Using Detect Text Only (Base Scenario): $75.00**

> For forms/tables extraction, costs increase significantly.

---

### 2. Amazon Transcribe

| Item | Calculation | Cost |
|------|-------------|------|
| Audio duration | 500 files × 5 min = 2,500 min | |
| Standard transcription | 2,500 × $0.024/min | $60.00 |
| **With batch discount** | 50% for batch jobs | **$30.00** |

---

### 3. Amazon Comprehend

| Feature | Volume | Unit Price | Cost |
|---------|--------|------------|------|
| Sentiment analysis | 50,000 units | $0.0001/unit | $5.00 |
| Entity recognition | 50,000 units | $0.0001/unit | $5.00 |
| Key phrase extraction | 50,000 units | $0.0001/unit | $5.00 |
| Language detection | 50,000 units | $0.0001/unit | $5.00 |
| Custom classification | 5,000 units | $0.0005/unit | $2.50 |
| **Total** | | | **$25.00** |

> 1 unit = 100 characters (3 units per page avg)

---

### 4. Amazon Rekognition

| Feature | Volume | Unit Price | Cost |
|---------|--------|------------|------|
| Label detection | 2,000 images | $1.00/1000 | $2.00 |
| Text in image | 2,000 images | $1.00/1000 | $2.00 |
| Face detection | 1,000 images | $1.00/1000 | $1.00 |
| Content moderation | 2,000 images | $1.00/1000 | $2.00 |
| **Total** | | | **$10.00** |

---

### 5. Amazon Bedrock (Claude 3 Sonnet)

| Operation | Volume | Token Estimate | Cost |
|-----------|--------|----------------|------|
| Document summarization | 5,000 | 2,000 input + 500 output | |
| Q&A extraction | 5,000 | 1,500 input + 300 output | |
| Input tokens | | 17.5M tokens | $52.50 |
| Output tokens | | 4M tokens | $60.00 |
| **Total** | | | **$100.00** |

#### Bedrock Pricing (Claude 3 Sonnet)

| Token Type | Price per 1M tokens |
|------------|---------------------|
| Input | $3.00 |
| Output | $15.00 |

---

### 6. Amazon SageMaker

#### Serverless Inference

| Item | Calculation | Cost |
|------|-------------|------|
| Inference requests | 5,000 | |
| Compute (GB-seconds) | 5,000 × 0.5s × 2 GB | 5,000 GB-s |
| Cost | 5,000 × $0.0000800 | $0.40 |
| Provisioned concurrency | 1 unit × 720 hrs | $20.00 |
| **Total** | | **$25.00** |

---

### 7. AWS Lambda

| Function | Invocations | Duration | Cost |
|----------|-------------|----------|------|
| Document Processor | 5,000 | 2s × 1GB | $0.83 |
| Orchestrator | 15,000 | 0.5s × 512MB | $0.31 |
| Result Handler | 20,000 | 0.2s × 256MB | $0.17 |
| **Total** | | | **$3.00** |

---

### 8. AWS Step Functions

| Item | Calculation | Cost |
|------|-------------|------|
| Workflow executions | 5,000/month | |
| State transitions | 5,000 × 20 states | 100,000 |
| Cost | 100,000 × $0.025/1000 | **$5.00** |

---

### 9. Amazon S3

| Item | Size | Cost |
|------|------|------|
| Document storage | 50 GB | $1.15 |
| Processed results | 10 GB | $0.23 |
| Model artifacts | 5 GB | $0.12 |
| PUT/GET requests | 500,000 | $2.50 |
| **Total** | | **$5.00** |

---

## Cost Optimization Strategies

### 1. Textract Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Use DetectText for simple docs | 70% | vs AnalyzeDocument |
| Batch processing | 10-20% | Lower per-page cost |
| Pre-filter pages | Variable | Skip blank pages |

### 2. Bedrock Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Use Haiku for simple tasks | 90% | $0.25/$1.25 per 1M tokens |
| Prompt caching | 50-80% | Reuse common prefixes |
| Reduce output length | Linear | Shorter summaries |

### 3. SageMaker Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Serverless for low volume | Variable | Pay per request |
| Spot instances for training | 70% | Interruptible |
| Multi-model endpoints | 50%+ | Share infrastructure |

---

## Scenario Comparisons

| Scenario | Documents/Month | Monthly Cost |
|----------|-----------------|--------------|
| **Small** | 500 | $50-80 |
| **Medium** (Base) | 5,000 | $250-350 |
| **Large** | 25,000 | $1,000-1,500 |
| **Enterprise** | 100,000 | $4,000-6,000 |

---

## Cost by Document Type

| Document Type | Services Used | Cost/Doc |
|---------------|---------------|----------|
| Simple PDF (text only) | Textract + Comprehend | $0.02 |
| Scanned document | Textract + Comprehend + Rekognition | $0.05 |
| Audio file | Transcribe + Comprehend + Bedrock | $0.15 |
| Complex document (forms) | Textract (forms) + Bedrock | $0.12 |

---

## Annual Cost Projection

| Quarter | Documents | Quarterly Cost |
|---------|-----------|----------------|
| Q1 | 15,000 | $870 |
| Q2 | 20,000 | $1,160 |
| Q3 | 25,000 | $1,450 |
| Q4 | 30,000 | $1,740 |
| **Annual** | 90,000 | **$5,220** |

---

## Enterprise In-House Cost Comparison

Building and maintaining an in-house document processing solution with equivalent ML capabilities requires significant capital and operational investment. This section provides a detailed comparison between AWS managed services and an enterprise in-house alternative.

### 1. Infrastructure Costs

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| ML Training Servers | 2x NVIDIA A100 GPU servers | $6,000 |
| GPU Inference Cluster | 4x NVIDIA T4 nodes | $4,000 |
| High-Performance Storage | 100TB NVMe SAN | $2,500 |
| Network Infrastructure | 10Gbps backbone, switches | $1,500 |
| Backup Systems | Redundant storage, DR site | $1,000 |
| **Infrastructure Total** | | **$15,000** |

---

### 2. Data Center/Facilities Costs

| Component | Description | Monthly Cost |
|-----------|-------------|--------------|
| Rack Space | 4 racks @ colocation facility | $3,200 |
| Power & Cooling | High-density compute cooling | $2,800 |
| Physical Security | 24/7 access control, monitoring | $800 |
| Internet Connectivity | Dual ISP, 10Gbps dedicated | $1,200 |
| **Facilities Total** | | **$8,000** |

---

### 3. Software Licensing Costs

| Software Category | Products | Monthly Cost |
|-------------------|----------|--------------|
| ML Frameworks (Enterprise) | TensorFlow Enterprise, PyTorch | $2,500 |
| OCR Software | ABBYY FineReader Server, OmniPage | $3,500 |
| Document Processing Suite | Kofax, IRIS, enterprise connectors | $2,000 |
| Database Licenses | PostgreSQL Enterprise, Redis Enterprise | $1,000 |
| Monitoring & Security | Datadog, Splunk, security tools | $1,000 |
| **Software Total** | | **$10,000** |

---

### 4. Personnel Costs

| Role | FTE Count | Monthly Salary | Monthly Cost |
|------|-----------|----------------|--------------|
| Senior ML Engineer | 1.5 | $18,000 | $27,000 |
| Data Scientist | 1.0 | $15,000 | $15,000 |
| DevOps/MLOps Engineer | 1.0 | $14,000 | $14,000 |
| System Administrator | 0.5 | $10,000 | $5,000 |
| Benefits & Overhead | 4 FTE | ~30% | $4,000 |
| **Personnel Total** | **4 FTE** | | **$65,000** |

> Note: Salaries include fully-loaded costs (benefits, taxes, equipment)

---

### 5. Total In-House Monthly Cost Summary

| Category | Monthly Cost | % of Total |
|----------|--------------|------------|
| Infrastructure | $15,000 | 15.3% |
| Data Center/Facilities | $8,000 | 8.2% |
| Software Licensing | $10,000 | 10.2% |
| Personnel | $65,000 | 66.3% |
| **TOTAL IN-HOUSE** | **$98,000** | 100% |

---

### 6. AWS vs In-House Visual Comparison

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Monthly Cost Comparison: AWS vs In-House               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  AWS Managed Services                                                      │
│  ├─ $290/month                                                             │
│  │                                                                         │
│  █ ← AWS ($290)                                                            │
│                                                                            │
│  ════════════════════════════════════════════════════════════════════════  │
│                                                                            │
│  In-House Solution                                                         │
│  ├─ $98,000/month                                                          │
│  │                                                                         │
│  ████████████████████████████████████████████████████████████████████████  │
│  ████████████████████████████████████████████████████████████████████████  │
│  ████████████████████████████████████████████████████████████████████████  │
│  ████████████████████████████████████████████████████████████████████████  │
│  ██████████████████████████████████████████████████████████ ← In-House    │
│                                                             ($98,000)      │
│                                                                            │
│  Cost Multiplier: In-House is ~338x MORE EXPENSIVE than AWS               │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                        In-House Cost Distribution                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Personnel        ████████████████████████████████████░░░░░░░░  66.3%     │
│  Infrastructure   ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  15.3%     │
│  Software         █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10.2%     │
│  Facilities       ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.2%     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### 7. Scaling Comparison

| Workload | AWS Cost | In-House Cost | AWS Advantage |
|----------|----------|---------------|---------------|
| 500 docs/month | $50-80 | $98,000 | 1,225x cheaper |
| 5,000 docs/month | $290 | $98,000 | 338x cheaper |
| 25,000 docs/month | $1,250 | $105,000 | 84x cheaper |
| 100,000 docs/month | $5,000 | $125,000 | 25x cheaper |
| 500,000 docs/month | $20,000 | $175,000 | 8.75x cheaper |
| 1,000,000 docs/month | $35,000 | $250,000 | 7.1x cheaper |

> In-House costs increase with additional infrastructure and personnel at scale

| Scaling Factor | AWS | In-House |
|----------------|-----|----------|
| Time to scale up | Minutes | 3-6 months |
| Time to scale down | Immediate | Fixed costs remain |
| Minimum commitment | None | ~$98,000/month |
| Geographic expansion | 1 click | New data center required |

---

### 8. Time-to-Market Comparison

| Phase | AWS Implementation | In-House Implementation |
|-------|-------------------|------------------------|
| Infrastructure Setup | 1-2 days | 3-6 months |
| ML Model Development | 2-4 weeks | 6-12 months |
| Integration & Testing | 1-2 weeks | 2-4 months |
| Production Deployment | 1 day | 2-4 weeks |
| **Total Time-to-Market** | **1-2 months** | **12-18 months** |

| Metric | AWS | In-House |
|--------|-----|----------|
| Opportunity cost (delayed revenue) | Minimal | $500K-2M+ |
| Risk of project failure | Low | Medium-High |
| Ongoing maintenance overhead | Low | High |

---

### 9. Hidden Costs (Not Included Above)

| Hidden Cost Category | Estimated Annual Impact |
|----------------------|------------------------|
| Recruitment & hiring costs | $50,000-100,000 |
| Employee turnover (avg 20%) | $75,000-150,000 |
| Training & certification | $20,000-40,000 |
| Hardware refresh (3-year cycle) | $60,000-120,000 |
| Security audits & compliance | $50,000-100,000 |
| Downtime & incident response | $25,000-75,000 |
| Technical debt accumulation | Variable |
| Model retraining & updates | $30,000-60,000 |
| **Total Hidden Costs** | **$310,000-645,000/year** |

> These costs add ~$25,000-$55,000/month to the in-house total

---

### 10. Break-Even Analysis

```
Break-Even Point Calculation:
─────────────────────────────────────────────────────────────────────────────

Monthly Fixed Cost Difference: $98,000 (In-House) - $290 (AWS) = $97,710

At what volume does In-House become cheaper?
├─ AWS cost per document: ~$0.058 (at base scenario)
├─ In-House marginal cost per document: ~$0.01 (compute only)
├─ Savings per document with In-House: ~$0.048
│
└─ Break-even volume = $97,710 / $0.048 = ~2,035,625 documents/month

Annual Break-Even: ~24.4 million documents/year

Note: This assumes:
  - No additional infrastructure scaling costs
  - No personnel additions required
  - 100% system utilization
  - Zero downtime
```

| Scenario | Monthly Volume | Annual Volume | Recommendation |
|----------|----------------|---------------|----------------|
| Below break-even | < 2M docs | < 24M docs | **Use AWS** |
| Near break-even | 2-3M docs | 24-36M docs | Hybrid approach |
| Above break-even | > 3M docs | > 36M docs | Consider in-house |

---

### 11. When In-House Might Make Sense

Despite the significant cost advantage of AWS, in-house solutions may be appropriate in specific scenarios:

| Scenario | Justification |
|----------|---------------|
| **Extreme Volume** | Processing 3M+ documents/month consistently |
| **Regulatory Requirements** | Data sovereignty laws prohibiting cloud usage |
| **Air-Gapped Environments** | Military, classified, or isolated networks |
| **Existing Infrastructure** | Already operating ML data centers with spare capacity |
| **Unique Model Requirements** | Highly specialized models not available on AWS |
| **Long-Term Strategic Investment** | 10+ year commitment with predictable high volume |

#### Decision Matrix

| Factor | Weight | AWS Score | In-House Score |
|--------|--------|-----------|----------------|
| Cost efficiency | 25% | 9/10 | 3/10 |
| Time-to-market | 20% | 10/10 | 3/10 |
| Scalability | 20% | 10/10 | 5/10 |
| Maintenance overhead | 15% | 9/10 | 4/10 |
| Data control | 10% | 7/10 | 10/10 |
| Customization | 10% | 7/10 | 9/10 |
| **Weighted Total** | 100% | **8.85** | **4.55** |

> **Recommendation**: For 95%+ of organizations, AWS managed services provide superior value, faster deployment, and lower total cost of ownership.

---

## Recommendations

1. **Use Claude 3 Haiku** for simple summarization tasks (10x cheaper)
2. **Batch Textract jobs** for cost efficiency
3. **Pre-filter documents** to skip irrelevant pages
4. **Cache common prompts** in Bedrock
5. **Use Comprehend batch APIs** for high-volume analysis
6. **Consider reserved capacity** for predictable workloads
