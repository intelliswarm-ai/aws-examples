# AWS SMS Marketing Platform - Cost Simulation

This document provides a detailed cost simulation for running the SMS Marketing Campaign Platform for one month. Costs are based on AWS pricing as of January 2025 for the **eu-central-2 (Zurich)** region.

## Table of Contents

1. [Scenario Overview](#scenario-overview)
2. [Cost Summary](#cost-summary)
3. [Detailed Cost Breakdown](#detailed-cost-breakdown)
4. [Cost Optimization Strategies](#cost-optimization-strategies)
5. [Scenario Comparisons](#scenario-comparisons)

---

## Scenario Overview

### Base Scenario: Medium-Volume SMS Marketing

| Metric | Value |
|--------|-------|
| **Subscriber Base** | 50,000 subscribers |
| **Campaigns/Month** | 4 campaigns |
| **SMS Sent/Campaign** | 50,000 |
| **Total SMS Sent** | 200,000/month |
| **Response Rate** | 5% (10,000 responses) |
| **Opt-out Rate** | 1% (2,000 opt-outs) |
| **Data Retention** | 365 days |

---

## Cost Summary

### Monthly Cost Estimate: Base Scenario

| Service | Monthly Cost (USD) | % of Total |
|---------|-------------------|------------|
| Amazon Pinpoint (SMS) | $1,290.00 | 87.8% |
| Amazon Kinesis | $25.00 | 1.7% |
| AWS Lambda | $5.00 | 0.3% |
| Amazon DynamoDB | $35.00 | 2.4% |
| Amazon S3 | $3.00 | 0.2% |
| Amazon SNS | $2.00 | 0.1% |
| CloudWatch | $10.00 | 0.7% |
| Other | $100.00 | 6.8% |
| **TOTAL** | **$1,470.00** | 100% |

```
┌────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Distribution                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pinpoint SMS    ████████████████████████████████████  87.8%    │
│  Other           ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   6.8%    │
│  DynamoDB        █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.4%    │
│  Kinesis         █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   1.7%    │
│  CloudWatch      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0.7%    │
│  Lambda/S3/SNS   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0.6%    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Detailed Cost Breakdown

### 1. Amazon Pinpoint (SMS)

#### Outbound SMS

| Destination | Volume | Price/SMS | Cost |
|-------------|--------|-----------|------|
| US | 100,000 | $0.00645 | $645.00 |
| UK | 50,000 | $0.0350 | $1,750.00 |
| Germany | 30,000 | $0.0725 | $2,175.00 |
| Canada | 20,000 | $0.00645 | $129.00 |

**Base Scenario (US only): $1,290.00**

> International SMS costs significantly more. EU destinations are 5-10x US prices.

#### Inbound SMS (Responses)

| Item | Calculation | Cost |
|------|-------------|------|
| Long code rental | 1 × $1.00/month | $1.00 |
| Inbound messages | 10,000 × $0.0075 | $75.00 |
| **Total Inbound** | | **$76.00** |

#### Phone Number Costs

| Type | Monthly Rental | Use Case |
|------|----------------|----------|
| Long code | $1.00 | Low volume, 2-way |
| Toll-free | $2.00 | Higher throughput |
| Short code | $1,000+ | High volume, branding |

---

### 2. Amazon Kinesis (365-Day Retention)

#### Extended Retention Stream

| Item | Calculation | Cost |
|------|-------------|------|
| Shard hours | 2 shards × 720 hours | 1,440 |
| Shard cost | 1,440 × $0.015/hour | $21.60 |
| Extended retention | 2 shards × 720 × $0.02/hour | $28.80 |
| PUT payload units | 220K × $0.014/1M | $0.00 |
| **Total (24h retention)** | | **$22.00** |
| **Total (365-day retention)** | | **$51.00** |

> Using 24-hour retention with S3 archival: **$25.00**

---

### 3. AWS Lambda

| Function | Invocations | Duration | Cost |
|----------|-------------|----------|------|
| Response Handler | 10,000 | 200 ms | $0.21 |
| Analytics Processor | 220,000 | 100 ms | $0.92 |
| Archive Handler | 10,000 | 150 ms | $0.13 |
| Campaign Sender | 4 | 30s | $0.01 |
| **Total** | | | **$5.00** |

---

### 4. Amazon DynamoDB

#### Tables

| Table | Writes/Month | Reads/Month | Storage |
|-------|--------------|-------------|---------|
| Subscribers | 52,000 | 500,000 | 5 GB |
| Campaigns | 100 | 10,000 | 0.1 GB |
| Responses | 10,000 | 50,000 | 2 GB |
| Analytics | 200,000 | 100,000 | 3 GB |

#### Costs

| Item | Calculation | Cost |
|------|-------------|------|
| Write requests | 262K × $1.25/1M | $0.33 |
| Read requests | 660K × $0.25/1M | $0.17 |
| Storage | 10 GB × $0.25/GB | $2.50 |
| TTL (365-day auto-delete) | Enabled | $0.00 |
| **Total** | | **$35.00** |

---

### 5. Amazon S3 (Compliance Archive)

| Item | Calculation | Cost |
|------|-------------|------|
| Storage (365 days) | 50 GB × $0.023/GB | $1.15 |
| IA transition (30+ days) | 30 GB × $0.0125/GB | $0.38 |
| Glacier (90+ days) | 20 GB × $0.004/GB | $0.08 |
| Requests | 50,000 × $0.005/1K | $0.25 |
| **Total** | | **$3.00** |

---

### 6. Amazon SNS (Opt-out Alerts)

| Item | Calculation | Cost |
|------|-------------|------|
| Publish (opt-outs) | 2,000 × $0.50/1M | $0.00 |
| Email notifications | 2,000 × $0.00 | $0.00 |
| Lambda deliveries | 10,000 × $0.00 | $0.00 |
| **Total** | | **$2.00** |

---

## SMS Cost by Country

### Price Comparison (per SMS)

| Country | Price | 200K SMS Cost |
|---------|-------|---------------|
| US | $0.00645 | $1,290 |
| Canada | $0.00645 | $1,290 |
| UK | $0.0350 | $7,000 |
| Germany | $0.0725 | $14,500 |
| France | $0.0650 | $13,000 |
| Australia | $0.0475 | $9,500 |
| India | $0.0025 | $500 |

> **Critical**: International SMS costs dominate the budget. Target US/Canada for cost efficiency.

---

## Campaign ROI Analysis

### Cost Per Conversion

| Metric | Value |
|--------|-------|
| SMS sent | 200,000 |
| SMS cost | $1,290 |
| Response rate | 5% |
| Conversion rate | 10% of responses |
| Conversions | 1,000 |
| **Cost per conversion** | **$1.29** |

### Break-Even Analysis

| Product Value | Conversions Needed | Break-Even Rate |
|---------------|-------------------|-----------------|
| $10 | 129 | 0.065% |
| $50 | 26 | 0.013% |
| $100 | 13 | 0.007% |

---

## Cost Optimization Strategies

### 1. SMS Cost Reduction

| Strategy | Savings | Notes |
|----------|---------|-------|
| Target US/Canada only | 80%+ | vs international |
| Use toll-free numbers | 50% | vs short codes |
| Segment subscribers | 20-40% | Send relevant only |
| A/B test messages | 10-20% | Improve conversion |

### 2. Throughput Optimization

| Number Type | Throughput | Best For |
|-------------|------------|----------|
| Long code | 1 SMS/sec | Low volume |
| Toll-free | 3 SMS/sec | Medium volume |
| Short code | 100 SMS/sec | High volume |
| 10DLC | 10 SMS/sec | US promotional |

### 3. Compliance Cost Savings

| Strategy | Savings | Notes |
|----------|---------|-------|
| S3 lifecycle policies | 60%+ | Glacier for old data |
| Kinesis 24h retention | 50% | Archive to S3 instead |
| DynamoDB TTL | 30% | Auto-delete old records |

---

## Scenario Comparisons

| Scenario | Subscribers | SMS/Month | Monthly Cost |
|----------|-------------|-----------|--------------|
| **Startup** | 5,000 | 20,000 | $180-250 |
| **Growth** (Base) | 50,000 | 200,000 | $1,400-1,600 |
| **Scale** | 200,000 | 800,000 | $5,500-6,500 |
| **Enterprise** | 1,000,000 | 4,000,000 | $27,000-32,000 |

---

## International Campaign Cost

### Example: Global Campaign (100K SMS each market)

| Market | SMS Cost | Infrastructure | Total |
|--------|----------|----------------|-------|
| US | $645 | $50 | $695 |
| UK | $3,500 | $50 | $3,550 |
| Germany | $7,250 | $50 | $7,300 |
| France | $6,500 | $50 | $6,550 |
| **Total** | | | **$18,095** |

---

## Annual Cost Projection

| Quarter | Campaigns | SMS Volume | Quarterly Cost |
|---------|-----------|------------|----------------|
| Q1 | 12 | 600K | $4,400 |
| Q2 | 16 | 800K | $5,800 |
| Q3 | 16 | 800K | $5,800 |
| Q4 | 20 | 1M | $7,250 |
| **Annual** | 64 | 3.2M | **$23,250** |

---

## Compliance Considerations

### TCPA/GDPR Compliance Costs

| Requirement | Implementation | Monthly Cost |
|-------------|----------------|--------------|
| Opt-out handling | Lambda + DynamoDB | Included |
| Consent tracking | DynamoDB | Included |
| Data retention (365 days) | S3 + Glacier | $3 |
| Audit logging | CloudTrail | $5 |
| **Total Compliance** | | **$8** |

---

## Enterprise In-House Cost Comparison

Building an equivalent SMS marketing platform in-house requires significant investment across multiple categories. This comparison helps enterprises evaluate the build-vs-buy decision.

### 1. Infrastructure Costs

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Messaging servers (HA pair) | $3,500 | 2x dedicated servers, load balanced |
| Message queue cluster | $2,500 | RabbitMQ/Kafka 3-node cluster |
| Database servers (primary + replica) | $2,800 | PostgreSQL HA with replication |
| Load balancers | $800 | Hardware or cloud-based |
| Monitoring infrastructure | $400 | Prometheus, Grafana stack |
| **Infrastructure Subtotal** | **$10,000** | |

### 2. Data Center/Facilities Costs

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Rack space/colocation | $2,000 | 2-3 racks in Tier 3 DC |
| Power and cooling | $1,500 | Redundant power, HVAC |
| Network connectivity | $1,000 | Redundant ISP, BGP |
| Physical security | $500 | Badge access, monitoring |
| **Facilities Subtotal** | **$5,000** | |

### 3. Software Licensing

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Messaging gateway software | $3,500 | Enterprise SMPP gateway |
| Analytics/BI platform | $2,000 | Tableau/Looker or equivalent |
| Database licenses | $1,500 | Enterprise PostgreSQL support |
| Monitoring/APM tools | $800 | DataDog, New Relic, etc. |
| Security software | $200 | WAF, IDS/IPS licenses |
| **Software Subtotal** | **$8,000** | |

### 4. SMS Aggregator Costs

| Provider | Per-SMS Cost | Notes |
|----------|--------------|-------|
| Twilio | $0.0079 | US outbound |
| Plivo | $0.0055 | US outbound |
| Bandwidth | $0.004 | Wholesale rates |
| Direct carrier | $0.003-0.005 | Volume agreements |

> **Note**: SMS aggregator costs are comparable to AWS Pinpoint rates (~$0.00645/SMS for US). The per-message costs remain similar whether using AWS or building in-house. For 200K messages: ~$1,200-1,600/month regardless of approach.

### 5. Personnel Costs

| Role | FTE | Monthly Cost | Responsibilities |
|------|-----|--------------|------------------|
| Senior Backend Developer | 1.0 | $15,000 | Platform development, API design |
| DevOps/Infrastructure Engineer | 1.0 | $14,000 | Deployment, monitoring, scaling |
| Operations/Support Specialist | 1.0 | $12,000 | 24/7 support, incident response |
| Security (part-time) | 0.25 | $4,000 | Security audits, compliance |
| **Personnel Subtotal** | **3.25 FTE** | **$45,000** | |

> Personnel costs include salary, benefits, and overhead (typically 1.3-1.5x base salary).

### 6. Compliance Costs

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| TCPA compliance management | $2,000 | Legal review, do-not-call lists |
| Carrier registration fees | $1,500 | 10DLC campaign registration |
| Security audits/penetration testing | $800 | Amortized annual cost |
| Compliance officer (part-time) | $700 | GDPR, CCPA oversight |
| **Compliance Subtotal** | **$5,000** | |

### Total In-House Monthly Cost Summary

| Category | Monthly Cost |
|----------|--------------|
| Infrastructure | $10,000 |
| Data Center/Facilities | $5,000 |
| Software Licensing | $8,000 |
| SMS Aggregator (200K SMS) | $1,300 |
| Personnel (3+ FTE) | $45,000 |
| Compliance | $5,000 |
| Contingency/Miscellaneous | $5,700 |
| **TOTAL IN-HOUSE** | **$80,000/month** |

### AWS vs In-House Cost Comparison

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Comparison (200K SMS/month)                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  AWS Pinpoint Solution                                                        │
│  ████ $1,470/month                                                            │
│                                                                               │
│  In-House Solution                                                            │
│  ████████████████████████████████████████████████████████ $80,000/month       │
│                                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Cost Breakdown Comparison:                                                   │
│                                                                               │
│  AWS Solution:                          In-House Solution:                    │
│  ┌─────────────────────────┐            ┌─────────────────────────┐          │
│  │ SMS/Pinpoint   $1,290   │            │ Infrastructure $10,000  │          │
│  │ Infrastructure   $180   │            │ Personnel      $45,000  │          │
│  │ Total          $1,470   │            │ Software        $8,000  │          │
│  └─────────────────────────┘            │ Facilities      $5,000  │          │
│                                         │ Compliance      $5,000  │          │
│                                         │ SMS/Aggregator  $1,300  │          │
│                                         │ Other           $5,700  │          │
│                                         │ Total         $80,000   │          │
│                                         └─────────────────────────┘          │
│                                                                               │
│  AWS is 54x more cost-effective for this volume                               │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Time-to-Market Comparison

| Phase | AWS Solution | In-House Solution |
|-------|--------------|-------------------|
| Initial setup | 1-2 days | 3-6 months |
| Basic SMS sending | 1 hour | 2-4 weeks |
| Analytics dashboard | 1 day | 4-8 weeks |
| Compliance features | Included | 4-6 weeks |
| Scaling to 1M SMS | Minutes | 2-4 weeks |
| **Total Time-to-Market** | **1-2 weeks** | **6-12 months** |

> **Key Insight**: AWS reduces time-to-market by 90%+, allowing businesses to start generating revenue immediately while in-house teams are still building infrastructure.

### When In-House Might Make Sense

Despite the cost advantages of AWS, building in-house may be justified when:

| Scenario | Justification |
|----------|---------------|
| **Extreme volume (50M+ SMS/month)** | Per-SMS costs dominate; wholesale carrier deals become viable |
| **Existing infrastructure** | Sunk costs in data centers, staff already in place |
| **Regulatory requirements** | Some industries require on-premise data processing |
| **Strategic differentiation** | Messaging is core IP, not commodity infrastructure |
| **Multi-channel consolidation** | Building unified platform across SMS, voice, email, push |

#### Break-Even Analysis

| Monthly Volume | AWS Cost | In-House Cost | Winner |
|----------------|----------|---------------|--------|
| 200K SMS | $1,470 | $80,000 | AWS (54x cheaper) |
| 1M SMS | $6,500 | $82,000 | AWS (12x cheaper) |
| 5M SMS | $32,500 | $90,000 | AWS (3x cheaper) |
| 10M SMS | $65,000 | $100,000 | AWS (1.5x cheaper) |
| 50M+ SMS | $320,000 | $150,000 | In-House (2x cheaper) |

> **Recommendation**: For most enterprises sending under 10M SMS/month, AWS provides superior economics and faster time-to-market. Consider in-house only at extreme scale with dedicated carrier relationships.

---

## Recommendations

1. **Focus on US/Canada** - 10x cheaper than EU destinations
2. **Use 10DLC for US** - Better deliverability, lower cost
3. **Segment campaigns** - Only message engaged subscribers
4. **Archive to S3** - Use 24h Kinesis retention + S3 for compliance
5. **Monitor opt-out rates** - High opt-outs waste money
6. **A/B test message content** - Improve conversion rates
7. **Consider short codes** - For high-volume campaigns (ROI justifies $1K/month)
