# Cost Simulation: Healthcare Imaging Data Lake

## Overview

Cost estimates for a healthcare imaging data lake storing 10 million medical images with associated clinical metadata. All estimates use AWS us-east-1 pricing as of January 2025.

## Assumptions

| Parameter | Value | Notes |
|-----------|-------|-------|
| Total images | 10,000,000 | Mix of CT, MRI, X-Ray |
| Average image size | 50 MB | DICOM format |
| Metadata records | 10,000,000 | 1:1 with images |
| Clinical records | 5,000,000 | Multiple images per study |
| Daily new images | 10,000 | ~3.6M/year growth |
| Monthly queries | 10,000 | ML training + exploration |
| Active users | 50 | ML engineers + researchers |

## Storage Costs

### S3 Storage

| Bucket | Size | Storage Class | Monthly Cost |
|--------|------|---------------|--------------|
| Images (current year) | 200 TB | S3 Standard | $4,716.00 |
| Images (1-3 years) | 300 TB | S3 Standard-IA | $3,840.00 |
| Images (3+ years) | 100 TB | S3 Glacier IR | $400.00 |
| Metadata (Parquet) | 50 GB | S3 Standard | $1.15 |
| Query results | 100 GB | S3 Standard | $2.30 |
| **Subtotal** | **~600 TB** | | **$8,959.45** |

### S3 Request Costs

| Operation | Monthly Volume | Unit Cost | Monthly Cost |
|-----------|----------------|-----------|--------------|
| PUT (ingestion) | 300,000 | $0.005/1000 | $1.50 |
| GET (queries) | 5,000,000 | $0.0004/1000 | $2.00 |
| LIST (crawlers) | 100,000 | $0.005/1000 | $0.50 |
| **Subtotal** | | | **$4.00** |

## Compute Costs

### Lambda Functions

| Function | Invocations/month | Duration | Memory | Monthly Cost |
|----------|-------------------|----------|--------|--------------|
| Ingestion Handler | 300,000 | 2,000 ms | 512 MB | $3.00 |
| Catalog Handler | 10,000 | 500 ms | 256 MB | $0.05 |
| Query Handler | 50,000 | 3,000 ms | 512 MB | $2.25 |
| API Handler | 100,000 | 200 ms | 256 MB | $0.13 |
| **Subtotal** | | | | **$5.43** |

### Glue

| Resource | Usage | Unit Cost | Monthly Cost |
|----------|-------|-----------|--------------|
| Crawlers (2 DPU) | 30 hours/month | $0.44/DPU-hour | $26.40 |
| Data Catalog | 1M objects | Free (first 1M) | $0.00 |
| **Subtotal** | | | **$26.40** |

## Analytics Costs

### Athena

| Metric | Value | Unit Cost | Monthly Cost |
|--------|-------|-----------|--------------|
| Data scanned | 50 TB/month | $5.00/TB | $250.00 |
| **Subtotal** | | | **$250.00** |

**Note**: Parquet format + partitioning reduces scanned data by ~90% vs raw JSON.

### Lake Formation

| Resource | Usage | Cost |
|----------|-------|------|
| Data filtering | Included | $0.00 |
| Governance | Included | $0.00 |
| **Subtotal** | | **$0.00** |

## Security & Encryption

### KMS

| Operation | Monthly Volume | Unit Cost | Monthly Cost |
|-----------|----------------|-----------|--------------|
| Symmetric key | 1 key | $1.00/month | $1.00 |
| Encrypt requests | 300,000 | $0.03/10,000 | $0.90 |
| Decrypt requests | 5,000,000 | $0.03/10,000 | $15.00 |
| GenerateDataKey | 300,000 | $0.03/10,000 | $0.90 |
| **Subtotal** | | | **$17.80** |

## Monitoring & Logging

### CloudWatch

| Resource | Volume | Unit Cost | Monthly Cost |
|----------|--------|-----------|--------------|
| Logs ingestion | 50 GB | $0.50/GB | $25.00 |
| Logs storage | 100 GB | $0.03/GB | $3.00 |
| Metrics | 100 custom | $0.30/metric | $30.00 |
| Alarms | 20 | $0.10/alarm | $2.00 |
| Dashboards | 3 | $3.00/dashboard | $9.00 |
| **Subtotal** | | | **$69.00** |

### CloudTrail

| Resource | Volume | Unit Cost | Monthly Cost |
|----------|--------|-----------|--------------|
| Management events | Included | Free | $0.00 |
| Data events (S3) | 10M events | $0.10/100K | $10.00 |
| **Subtotal** | | | **$10.00** |

## Networking

### Data Transfer

| Transfer Type | Volume | Unit Cost | Monthly Cost |
|---------------|--------|-----------|--------------|
| S3 → Lambda (same region) | 1 TB | Free | $0.00 |
| S3 → Internet (query results) | 100 GB | $0.09/GB | $9.00 |
| VPC endpoints | 3 endpoints | $0.01/GB + $7.30/endpoint | $30.00 |
| **Subtotal** | | | **$39.00** |

## Monthly Cost Summary

| Category | Monthly Cost | % of Total |
|----------|--------------|------------|
| S3 Storage | $8,959.45 | 94.6% |
| S3 Requests | $4.00 | 0.0% |
| Lambda | $5.43 | 0.1% |
| Glue | $26.40 | 0.3% |
| Athena | $250.00 | 2.6% |
| KMS | $17.80 | 0.2% |
| CloudWatch | $69.00 | 0.7% |
| CloudTrail | $10.00 | 0.1% |
| Networking | $39.00 | 0.4% |
| **Total** | **$9,381.08** | **100%** |

## Annual Cost Projection

| Year | Storage Growth | Annual Cost |
|------|----------------|-------------|
| Year 1 | Base (600 TB) | $112,573 |
| Year 2 | +150 TB | $130,573 |
| Year 3 | +150 TB | $148,573 |

## Cost Optimization Strategies

### 1. S3 Lifecycle Policies (Savings: ~30%)

```
Current monthly: $8,959
Optimized monthly: $6,271
Annual savings: $32,256
```

**Implementation:**
- Move images older than 1 year to S3-IA
- Move images older than 3 years to Glacier IR
- Enable Intelligent-Tiering for metadata

### 2. Athena Query Optimization (Savings: ~50%)

```
Current monthly: $250
Optimized monthly: $125
Annual savings: $1,500
```

**Implementation:**
- Partition by year/month/day + modality
- Use Parquet with Snappy compression
- Create workgroup with bytes scanned limits
- Implement result caching

### 3. Reserved Capacity

| Service | Commitment | Discount |
|---------|------------|----------|
| S3 Storage | 1-year | 30% |
| Lambda | Savings Plans | 17% |

### 4. Right-Sizing

- Lambda memory: Profile actual usage, reduce if possible
- Glue DPUs: Use 2 DPU for small catalogs
- CloudWatch logs: Reduce retention to 30 days

## Cost Comparison: Alternative Architectures

| Architecture | Monthly Cost | Notes |
|--------------|--------------|-------|
| **Current (Lake Formation)** | $9,381 | Full governance |
| S3 + Athena only | $9,200 | No fine-grained access |
| Redshift Serverless | $12,500 | Better for frequent queries |
| RDS + S3 | $11,000 | Hybrid approach |
| Snowflake | $15,000 | Third-party |

## Cost Alerts Configuration

| Alert | Threshold | Action |
|-------|-----------|--------|
| Monthly budget | $10,000 | Email notification |
| Daily anomaly | +50% | SNS alert |
| Athena query cost | $50/query | Block query |
| S3 storage growth | +10 TB/month | Review retention |

## Break-Even Analysis

### Build vs Buy

| Factor | Build (This Solution) | Buy (Vendor PACS) |
|--------|----------------------|-------------------|
| Monthly cost | $9,381 | $15,000-25,000 |
| Setup cost | $50,000 | $100,000+ |
| Customization | Full | Limited |
| Compliance | Self-managed | Vendor-managed |
| Scalability | Unlimited | Per contract |

**Break-even**: ~6-12 months vs vendor solutions

## Recommendations

1. **Start with lifecycle policies**: Immediate 30% storage savings
2. **Implement query optimization**: Reduces Athena costs by 50%
3. **Monitor with budgets**: Set alerts at $10K/month
4. **Consider reserved capacity**: After 6 months of stable usage
5. **Review monthly**: Storage growth vs query patterns

## Pricing References

- [S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [Athena Pricing](https://aws.amazon.com/athena/pricing/)
- [Glue Pricing](https://aws.amazon.com/glue/pricing/)
- [KMS Pricing](https://aws.amazon.com/kms/pricing/)
- [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)
