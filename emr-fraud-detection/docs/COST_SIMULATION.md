# Cost Simulation - EMR Spark Fraud Detection Pipeline

This document provides cost estimates and optimization strategies for the fraud detection pipeline.

## Cost Summary

### Monthly Cost Estimate (Production)

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| EMR (Batch Pipeline) | $850 | 2hr/day transient cluster |
| EMR (Streaming) | $1,200 | Always-on small cluster |
| Kinesis Data Streams | $450 | 2 shards, 1M records/day |
| Lambda | $150 | 5 functions, moderate traffic |
| S3 | $200 | 500GB data lake |
| DynamoDB | $100 | On-demand, ~10M items |
| API Gateway | $50 | 1M API calls |
| Step Functions | $25 | 30 executions/month |
| CloudWatch | $75 | Logs, metrics, dashboard |
| VPC/NAT Gateway | $100 | NAT Gateway + data transfer |
| SNS | $10 | Alert notifications |
| **Total** | **~$3,210/month** | |

### Cost by Environment

| Environment | Monthly Cost | Description |
|-------------|-------------|-------------|
| Development | ~$500 | Minimal resources, on-demand |
| Staging | ~$1,200 | Production-like, reduced scale |
| Production | ~$3,200 | Full scale, high availability |

## Detailed Cost Breakdown

### Amazon EMR

#### Batch Processing Cluster (Transient)

**Configuration:**
- 1 x m5.xlarge Master (On-Demand): $0.192/hr
- 2 x m5.xlarge Core (Spot): ~$0.058/hr each
- 2 x m5.xlarge Task (Spot): ~$0.058/hr each

**Daily Run (2 hours):**
```
Master:  $0.192 x 2 hrs = $0.38
Core:    $0.058 x 2 x 2 hrs = $0.23
Task:    $0.058 x 2 x 2 hrs = $0.23
EMR Fee: ~$0.15
Daily Total: ~$0.99
Monthly (30 days): ~$30
```

**Weekly Full Training (4 hours):**
```
Training cluster (larger): ~$5/run
Monthly (4 runs): ~$20
```

#### Streaming Cluster (Always-On)

**Configuration:**
- 1 x m5.xlarge Master (On-Demand)
- 2 x m5.large Core (Spot)

**Monthly Cost:**
```
Master:  $0.192 x 730 hrs = $140
Core:    $0.048 x 2 x 730 hrs = $70
EMR Fee: ~$50
Monthly Total: ~$260
```

**Note:** Production may require larger instances depending on throughput requirements.

### Amazon Kinesis Data Streams

**Configuration:**
- 2 shards (1 MB/s write, 2 MB/s read each)
- 24-hour retention

**Monthly Cost:**
```
Shard Hours: 2 shards x 730 hrs x $0.015 = $22
PUT Payload Units: 1M records x 25KB avg / 25KB = 1M units x $0.014/M = $14
Extended Retention: $0 (24 hrs included)
Monthly Total: ~$36
```

**At Scale (10M transactions/day):**
```
Shards needed: 10 (1M records/shard/day)
Monthly: ~$180
```

### AWS Lambda

**5 Functions:**

| Function | Invocations/month | Duration | Memory | Cost |
|----------|------------------|----------|--------|------|
| Ingestion | 1M | 200ms | 256MB | $8 |
| Stream Processor | 10K | 500ms | 512MB | $3 |
| Orchestration | 1K | 300ms | 256MB | $0.10 |
| Alert Handler | 50K | 100ms | 256MB | $1 |
| Query Handler | 100K | 200ms | 256MB | $4 |

**Monthly Total: ~$16**

### Amazon S3

**Storage Breakdown:**

| Zone | Data Size | Storage Class | Monthly Cost |
|------|-----------|---------------|--------------|
| Raw | 200 GB | Standard | $4.60 |
| Features | 100 GB | Intelligent-Tiering | $2.30 |
| Models | 10 GB | Standard | $0.23 |
| Predictions | 150 GB | Standard | $3.45 |
| Logs | 50 GB | Standard | $1.15 |

**Data Transfer:**
```
PUT/GET requests: ~$5
Transfer to EMR: ~$10 (within region)
Monthly Total: ~$27
```

### Amazon DynamoDB

**On-Demand Mode:**

| Table | Items | Avg Size | RCU/month | WCU/month | Cost |
|-------|-------|----------|-----------|-----------|------|
| Alerts | 500K | 1KB | 5M | 500K | $8 |
| Predictions | 10M | 500B | 10M | 10M | $35 |
| Executions | 1K | 2KB | 10K | 1K | $0.10 |

**Storage:**
```
Total: ~5 GB x $0.25 = $1.25
Monthly Total: ~$45
```

### API Gateway

**REST API:**
```
1M requests x $3.50/M = $3.50
Data transfer: ~$1
Monthly Total: ~$5
```

### Step Functions

**Standard Workflows:**
```
30 executions/month
Average 10 state transitions each
300 transitions x $0.025/1000 = $0.008
Monthly Total: ~$1
```

### CloudWatch

| Component | Monthly Cost |
|-----------|-------------|
| Logs (50 GB ingested) | $25 |
| Logs storage (100 GB) | $3 |
| Metrics (100 custom) | $30 |
| Dashboard (1) | $3 |
| Alarms (10) | $1 |
| **Total** | **~$62** |

## Cost Optimization Strategies

### 1. EMR Optimization

**Use Spot Instances:**
- 50-70% cost savings on task nodes
- Configure spot bidding at 50% of on-demand price
- Use instance fleets for reliability

**Right-size Clusters:**
- Start small, scale based on metrics
- Use auto-scaling for streaming cluster
- Terminate idle clusters aggressively

**Transient vs. Persistent:**
- Batch: Always use transient clusters
- Streaming: Use persistent but right-sized

### 2. Storage Optimization

**S3 Lifecycle Policies:**
```yaml
Rules:
  - Transition to Intelligent-Tiering: 30 days
  - Transition to Glacier: 90 days
  - Delete old versions: 30 days
```

**Compression:**
- Use Parquet format (70% smaller than JSON)
- Enable Snappy compression
- Partition by date for efficient queries

### 3. Kinesis Optimization

**Right-size Shards:**
- Monitor `WriteProvisionedThroughputExceeded`
- Use Kinesis Data Streams on-demand mode for variable traffic

**Batch Records:**
- Use PutRecords API (up to 500 records)
- Aggregate small records client-side

### 4. Lambda Optimization

**Memory Tuning:**
- Profile functions to find optimal memory
- Higher memory = faster execution = lower cost

**Provisioned Concurrency:**
- For consistent latency requirements
- Cost-effective for high-traffic functions

### 5. DynamoDB Optimization

**On-Demand vs. Provisioned:**
- On-demand: Variable, unpredictable traffic
- Provisioned: Consistent traffic patterns

**TTL:**
- Enable TTL for predictions (90 days)
- Auto-delete old data, reduce storage

## Cost Comparison: Cloud vs. On-Premises

### Equivalent On-Premises Infrastructure

| Component | On-Prem Equivalent | Annual Cost |
|-----------|-------------------|-------------|
| EMR Cluster | 6-node Hadoop cluster | $150,000 |
| Storage | 10TB SAN + backup | $50,000 |
| Networking | Load balancers, switches | $20,000 |
| Data Center | Power, cooling, space | $30,000 |
| Operations | 2 FTE engineers | $300,000 |
| **Total** | | **$550,000/year** |

### AWS Annual Cost

```
$3,200/month x 12 = $38,400/year
```

**Savings: ~93%** (plus elasticity, managed services, no capital expenditure)

## Scaling Considerations

### 10x Scale (10M transactions/day)

| Component | Current | 10x Scale |
|-----------|---------|-----------|
| EMR Batch | $50 | $200 |
| EMR Streaming | $260 | $800 |
| Kinesis | $36 | $300 |
| Lambda | $16 | $100 |
| S3 | $27 | $200 |
| DynamoDB | $45 | $400 |
| Other | $100 | $200 |
| **Total** | **$534** | **$2,200** |

### 100x Scale (100M transactions/day)

Consider:
- EMR Serverless for auto-scaling
- Kinesis Data Firehose for simplified delivery
- DynamoDB with DAX caching
- Reserved capacity for predictable workloads

**Estimated Monthly Cost: $15,000-$20,000**

## Reserved Capacity Savings

### 1-Year Reserved Instances

| Service | On-Demand | Reserved | Savings |
|---------|-----------|----------|---------|
| EMR (streaming) | $260 | $180 | 31% |
| RDS (if used) | $150 | $95 | 37% |

### Savings Plans

- Compute Savings Plans: Up to 66% on Lambda, Fargate
- EC2 Instance Savings Plans: Up to 72% on EMR

## Monitoring Costs

### AWS Cost Explorer Tags

```
Tags:
  - Project: fraud-detection
  - Environment: dev/staging/prod
  - Component: emr/lambda/s3/dynamo
```

### Budget Alerts

```
Monthly Budget: $4,000
Alerts at: 50%, 80%, 100%
Notification: SNS -> Email/Slack
```
