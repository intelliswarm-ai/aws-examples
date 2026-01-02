# AWS Lex Airline Chatbot - Cost Simulation

This document provides a detailed cost simulation for running the AWS Lex Airline Chatbot for one month. Costs are based on AWS pricing as of January 2025 for the **eu-central-2 (Zurich)** region.

## Table of Contents

1. [Scenario Overview](#scenario-overview)
2. [Cost Summary](#cost-summary)
3. [Detailed Cost Breakdown](#detailed-cost-breakdown)
4. [Cost Optimization Strategies](#cost-optimization-strategies)
5. [Scenario Comparisons](#scenario-comparisons)

---

## Scenario Overview

### Base Scenario: Medium Regional Airline

| Metric | Value |
|--------|-------|
| **Daily Conversations** | 500 |
| **Monthly Conversations** | 15,000 |
| **Avg Turns per Conversation** | 8 |
| **Monthly Requests (Text)** | 120,000 |
| **Voice Enabled** | No |
| **Bookings Created** | 2,000/month |
| **Check-Ins Processed** | 3,000/month |
| **Booking Modifications** | 500/month |

---

## Cost Summary

### Monthly Cost Estimate: Base Scenario

| Service | Monthly Cost (USD) | % of Total |
|---------|-------------------|------------|
| Amazon Lex V2 (Text) | $90.00 | 52.9% |
| AWS Lambda | $5.00 | 2.9% |
| Amazon DynamoDB | $25.00 | 14.7% |
| Amazon CloudWatch | $10.00 | 5.9% |
| API Gateway (Optional) | $15.00 | 8.8% |
| Other | $25.00 | 14.7% |
| **TOTAL** | **$170.00** | 100% |

```
┌────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Distribution                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Lex V2           ██████████████████████████░░░░░░░░  52.9%    │
│  DynamoDB         ███████░░░░░░░░░░░░░░░░░░░░░░░░░░░  14.7%    │
│  Other            ███████░░░░░░░░░░░░░░░░░░░░░░░░░░░  14.7%    │
│  API Gateway      ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.8%    │
│  CloudWatch       ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   5.9%    │
│  Lambda           █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.9%    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Detailed Cost Breakdown

### 1. Amazon Lex V2

#### Text Requests

| Item | Calculation | Cost |
|------|-------------|------|
| Text requests | 120,000 × $0.00075 | $90.00 |
| **Free tier** | -10,000 requests (12 months) | -$7.50 |
| **Total (after free tier)** | | **$82.50** |

#### Speech Requests (If Enabled)

| Item | Calculation | Cost |
|------|-------------|------|
| Speech requests | 120,000 × $0.004 | $480.00 |
| Speech synthesis | 120,000 × $0.004 | $480.00 |
| **Total Speech** | | **$960.00** |

> Text-only mode is significantly cheaper than voice.

#### Lex Pricing Summary

| Request Type | Price per Request |
|--------------|-------------------|
| Text | $0.00075 |
| Speech (input) | $0.004 |
| Speech synthesis | $0.004 |
| Streaming speech | $0.0065 |

**Lex Monthly Total: $90.00**

---

### 2. AWS Lambda (Fulfillment)

#### Function Invocations

| Function | Invocations/Month | Duration | Memory | Cost |
|----------|-------------------|----------|--------|------|
| Lex Fulfillment | 120,000 | 500 ms | 256 MB | $2.50 |
| Dialog Code Hook | 60,000 | 200 ms | 256 MB | $0.50 |
| Validation Hook | 60,000 | 100 ms | 128 MB | $0.12 |
| **Total** | | | | **$5.00** |

#### Cost Calculation

| Item | Calculation | Cost |
|------|-------------|------|
| Requests | 240,000 × $0.20/1M | $0.05 |
| Compute GB-seconds | | |
| - Fulfillment | 120,000 × 0.5s × 0.25 GB | 15,000 GB-s |
| - Dialog Hook | 60,000 × 0.2s × 0.25 GB | 3,000 GB-s |
| - Validation | 60,000 × 0.1s × 0.125 GB | 750 GB-s |
| Total GB-seconds | 18,750 GB-s | |
| Cost | 18,750 × $0.0000166667 | $0.31 |
| **After Free Tier** | | **$5.00** |

---

### 3. Amazon DynamoDB

#### Tables

| Table | Writes/Month | Reads/Month | Storage |
|-------|--------------|-------------|---------|
| Flights | 1,000 | 100,000 | 0.5 GB |
| Bookings | 5,500 | 50,000 | 1 GB |
| CheckIns | 3,000 | 20,000 | 0.3 GB |

#### On-Demand Costs

| Item | Calculation | Cost |
|------|-------------|------|
| Write requests | 9,500 × $1.25/1M | $0.01 |
| Read requests | 170,000 × $0.25/1M | $0.04 |
| Storage | 1.8 GB × $0.25/GB | $0.45 |
| **Subtotal** | | **$0.50** |

#### Additional Features

| Feature | Cost |
|---------|------|
| Point-in-time recovery | $0.36 |
| On-demand backup | $0.18 |
| GSI (3 indices) | $5.00 |
| **Subtotal** | **$5.54** |

#### Provisioned Capacity (Alternative)

For predictable traffic, provisioned capacity may be cheaper:

| Item | WCU/RCU | Cost |
|------|---------|------|
| Write capacity | 5 WCU | $2.37 |
| Read capacity | 25 RCU | $2.97 |
| **Total** | | **$5.34** |

**DynamoDB Monthly Total: $25.00** (with buffer for spikes)

---

### 4. Amazon CloudWatch

| Item | Calculation | Cost |
|------|-------------|------|
| Log ingestion | 10 GB × $0.50/GB | $5.00 |
| Log storage | 10 GB × $0.03/GB | $0.30 |
| Custom metrics | 15 × $0.30 | $4.50 |
| Alarms | 5 × $0.10 | $0.50 |
| **Free tier offset** | | -$2.30 |
| **Total** | | **$10.00** |

---

### 5. API Gateway (Optional - for Web Integration)

| Item | Calculation | Cost |
|------|-------------|------|
| HTTP API requests | 500,000 × $1.00/1M | $0.50 |
| REST API requests | 100,000 × $3.50/1M | $0.35 |
| WebSocket connections | 50,000 × $0.25/1M | $0.01 |
| **Total** | | **$15.00** |

> API Gateway is optional if using direct Lex integration.

---

## Voice vs Text Cost Comparison

### Monthly Cost by Channel

| Channel | Requests | Unit Price | Monthly Cost |
|---------|----------|------------|--------------|
| **Text Only** | 120,000 | $0.00075 | $90 |
| **Voice Only** | 120,000 | $0.008 | $960 |
| **Mixed (70/30)** | 84K text + 36K voice | - | $351 |

### Channel Strategy

| Scenario | Recommendation | Monthly Cost |
|----------|----------------|--------------|
| Cost-optimized | Text-only (web/app) | $170 |
| Customer preference | Mixed channels | $400-500 |
| Premium experience | Full voice | $1,100+ |

---

## Intent-Based Cost Analysis

### Cost per Intent

| Intent | Avg Turns | Requests/Op | Ops/Month | Cost |
|--------|-----------|-------------|-----------|------|
| BookFlight | 10 | 10 | 2,000 | $15.00 |
| UpdateBooking | 6 | 6 | 500 | $2.25 |
| CheckIn | 5 | 5 | 3,000 | $11.25 |
| FallbackIntent | 3 | 3 | 5,000 | $11.25 |
| **Total** | | | | **$39.75** |

### Fallback Intent Optimization

High fallback rates increase costs without value:

| Fallback Rate | Extra Cost/Month | Action |
|---------------|------------------|--------|
| 5% | $4.50 | Acceptable |
| 15% | $13.50 | Review training |
| 30% | $27.00 | Urgent training needed |

---

## Conversation Analytics

### Success Rate Impact

| Completion Rate | Conversations | Requests | Cost |
|-----------------|---------------|----------|------|
| 95% (excellent) | 15,000 | 120,000 | $90 |
| 80% (good) | 15,000 | 142,500 | $107 |
| 60% (poor) | 15,000 | 190,000 | $143 |

> Poor NLU training increases costs due to longer conversations.

### Conversation Length Analysis

| Avg Turns | Requests/Month | Lex Cost | Impact |
|-----------|----------------|----------|--------|
| 5 turns | 75,000 | $56 | -38% |
| 8 turns (base) | 120,000 | $90 | baseline |
| 12 turns | 180,000 | $135 | +50% |

---

## Cost Optimization Strategies

### 1. Lex Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Text-only | 90% vs voice | Disable speech |
| Better NLU training | 20-40% | Reduce fallbacks |
| Slot confirmation | 10-20% | Fewer re-prompts |
| Intent chaining | 15-25% | Combine related intents |

### 2. Lambda Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Right-size memory | 20-30% | 256 MB is often sufficient |
| Reduce duration | 15-25% | Optimize code |
| SnapStart | 30% cold start | For Java |
| ARM64 | 20% | Graviton2 |

### 3. DynamoDB Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Provisioned capacity | 30-50% | For predictable load |
| Reserved capacity | Up to 77% | 1-3 year commitment |
| TTL cleanup | Variable | Auto-delete old bookings |
| Sparse indices | Variable | Index only needed attributes |

### 4. Architecture Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Lex response cards | Fewer turns | Guide user choices |
| Quick replies | Fewer turns | Reduce typing errors |
| Context carryover | 20-30% | Maintain session state |

---

## Scenario Comparisons

| Scenario | Daily Conversations | Voice | Monthly Cost |
|----------|---------------------|-------|--------------|
| **Startup** | 100 | No | $45-60 |
| **Regional** (Base) | 500 | No | $150-200 |
| **National** | 2,000 | Mixed | $600-800 |
| **Enterprise** | 10,000 | Yes | $3,500-5,000 |

---

## Multi-Language Support

### Additional Language Costs

| Language | NLU Quality | Extra Training |
|----------|-------------|----------------|
| English (US/UK) | Excellent | None |
| Spanish | Excellent | None |
| French | Good | Minimal |
| German | Good | Minimal |
| Other | Variable | May need custom |

### Multi-Language Architecture

| Approach | Cost Impact | Notes |
|----------|-------------|-------|
| Single bot, multiple locales | +0% | Built-in Lex feature |
| Separate bots per language | +50-100% | More maintenance |
| Translation layer | +20-30% | Add Translate API |

---

## Annual Cost Projection

### With Growth

| Quarter | Daily Conversations | Monthly Cost | Quarterly |
|---------|---------------------|--------------|-----------|
| Q1 | 500 | $170 | $510 |
| Q2 | 750 | $230 | $690 |
| Q3 | 1,000 | $300 | $900 |
| Q4 | 1,500 | $420 | $1,260 |
| **Annual** | | | **$3,360** |

### With Voice Addition (Q3)

| Quarter | Channel | Monthly Cost | Quarterly |
|---------|---------|--------------|-----------|
| Q1-Q2 | Text | $200 | $1,200 |
| Q3-Q4 | Mixed (50/50) | $550 | $3,300 |
| **Annual** | | | **$4,500** |

---

## Free Tier Coverage

| Service | Free Tier | Monthly Value |
|---------|-----------|---------------|
| Lex V2 | 10,000 text, 5,000 speech (12 mo) | ~$10 |
| Lambda | 1M requests, 400K GB-s | ~$8 |
| DynamoDB | 25 GB, 25 WCU/RCU | ~$15 |
| CloudWatch | 10 metrics, 5 GB logs | ~$5 |
| **Total** | | **~$38/month** |

---

## ROI Analysis

### Chatbot vs Human Agent

| Metric | Human Agent | Lex Chatbot |
|--------|-------------|-------------|
| Cost per conversation | $5-15 | $0.01 |
| Availability | 8-16 hours | 24/7 |
| Languages | 1-2 | Many |
| Scalability | Linear cost | Near-zero marginal |
| Response time | 2-5 minutes | Instant |

### Monthly Savings Calculation

| Conversations | Human Cost | Chatbot Cost | Savings |
|---------------|------------|--------------|---------|
| 5,000 | $25,000-75,000 | $60 | 99%+ |
| 15,000 | $75,000-225,000 | $170 | 99%+ |
| 50,000 | $250,000-750,000 | $500 | 99%+ |

### Break-Even Analysis

| Investment | Human FTE Equivalent | Payback |
|------------|---------------------|---------|
| $10,000 (development) | 0.5 FTE | 1-2 months |
| $170/month (operation) | 0.01 FTE | Immediate |

---

## Compliance Considerations

### PCI-DSS (Payment Data)

| Requirement | Implementation | Cost Impact |
|-------------|----------------|-------------|
| Slot obfuscation | Built-in | $0 |
| Conversation logs | Encrypted | +$5/month |
| Audit trail | CloudTrail | +$2/month |

### GDPR

| Requirement | Implementation | Cost Impact |
|-------------|----------------|-------------|
| Data deletion | DynamoDB TTL | $0 |
| Consent tracking | Custom slot | +$0 |
| Right to export | Lambda function | +$1/month |

---

## Enterprise In-House Cost Comparison

Building a conversational AI chatbot platform in-house requires significant investment in infrastructure, software, and personnel. This section compares the costs of AWS Lex against building and maintaining an equivalent in-house solution.

### 1. Infrastructure Costs

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| NLU Servers | 4x GPU-enabled servers (NVIDIA T4) | $4,500 |
| API Servers | 3x High-CPU instances (load balanced) | $2,000 |
| Database Cluster | PostgreSQL HA cluster (3 nodes) | $1,800 |
| Redis Cache | Clustered cache for session management | $800 |
| Load Balancers | HA pair with SSL termination | $500 |
| Network/Bandwidth | 10 TB egress + inter-server | $400 |
| **Infrastructure Total** | | **$10,000** |

### 2. Data Center / Facilities Costs

| Component | Description | Monthly Cost |
|-----------|-------------|--------------|
| Colocation / Rack Space | 2 racks in Tier III data center | $2,500 |
| Power & Cooling | 20kW allocation | $1,200 |
| Network Connectivity | Redundant fiber connections | $800 |
| Physical Security | 24/7 access control, monitoring | $300 |
| Disaster Recovery Site | Secondary site allocation | $200 |
| **Facilities Total** | | **$5,000** |

> Note: Cloud-hosted in-house solutions would replace data center costs with IaaS costs, typically $8,000-12,000/month for equivalent compute.

### 3. Software Licensing Costs

| Software | License Type | Monthly Cost |
|----------|-------------|--------------|
| Rasa Enterprise | Per-bot licensing (3 bots) | $4,500 |
| Dialogflow CX Enterprise | 50,000 requests included | $3,000 |
| NLU/NLP Libraries | SpaCy, Hugging Face Enterprise | $1,500 |
| Database Licenses | PostgreSQL Enterprise support | $800 |
| Monitoring Tools | Datadog, PagerDuty | $1,200 |
| Security Tools | WAF, SIEM, vulnerability scanning | $1,000 |
| **Software Total** | | **$12,000** |

### 4. Personnel Costs

| Role | FTE | Annual Salary | Monthly Cost |
|------|-----|---------------|--------------|
| NLP/ML Engineer | 1.0 | $180,000 | $15,000 |
| Backend Developer | 1.0 | $150,000 | $12,500 |
| Conversation Designer | 0.5 | $120,000 | $5,000 |
| DevOps/SRE Engineer | 0.5 | $160,000 | $6,667 |
| QA Engineer | 0.5 | $110,000 | $4,583 |
| Project Manager (partial) | 0.25 | $140,000 | $2,917 |
| Benefits & Overhead (35%) | - | - | $8,333 |
| **Personnel Total** | **3.75 FTE** | | **$55,000** |

> Personnel costs include base salary plus 35% for benefits, taxes, equipment, and overhead.

### 5. Total In-House Monthly Cost Summary

| Category | Monthly Cost | % of Total |
|----------|--------------|------------|
| Infrastructure | $10,000 | 11.8% |
| Data Center / Facilities | $5,000 | 5.9% |
| Software Licensing | $12,000 | 14.1% |
| Personnel | $55,000 | 64.7% |
| Contingency (5%) | $4,100 | 4.8% |
| **TOTAL IN-HOUSE** | **$86,100** | 100% |

### 6. AWS Lex vs In-House Cost Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│            Monthly Cost Comparison: AWS Lex vs In-House Solution            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AWS Lex (Base)     █ $170                                                  │
│                     |                                                       │
│  AWS Lex (Voice)    ████ $1,100                                             │
│                     |                                                       │
│  AWS Lex (Enterpr)  █████████████ $5,000                                    │
│                     |                                                       │
│  In-House           ████████████████████████████████████████████ $86,100    │
│                     |                                                       │
│                     └───────┬───────┬───────┬───────┬───────┬───────┬──────│
│                             $0    $20K    $40K    $60K    $80K   $100K      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Cost Savings with AWS Lex:                                                 │
│                                                                             │
│  ┌────────────────┬─────────────┬─────────────┬────────────────────────┐   │
│  │ Scenario       │ AWS Lex     │ In-House    │ Annual Savings         │   │
│  ├────────────────┼─────────────┼─────────────┼────────────────────────┤   │
│  │ Startup        │ $60/mo      │ $86,100/mo  │ $1,032,480 (99.9%)     │   │
│  │ Regional       │ $170/mo     │ $86,100/mo  │ $1,031,160 (99.8%)     │   │
│  │ Enterprise     │ $5,000/mo   │ $86,100/mo  │ $973,200 (94.2%)       │   │
│  └────────────────┴─────────────┴─────────────┴────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7. Time-to-Market Comparison

| Milestone | AWS Lex | In-House |
|-----------|---------|----------|
| Initial prototype | 1-2 days | 2-4 weeks |
| Basic NLU training | 1 week | 1-2 months |
| Production-ready MVP | 2-4 weeks | 4-6 months |
| Multi-language support | 1-2 days | 2-3 months |
| Voice channel integration | 1 day | 2-4 months |
| Full enterprise deployment | 2-3 months | 8-12 months |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Time-to-Production Comparison                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AWS Lex MVP      ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  2-4 weeks           │
│                                                                             │
│  In-House MVP     ████████████████████████░░░░░░░░░░░  4-6 months          │
│                                                                             │
│  AWS Enterprise   ████████████░░░░░░░░░░░░░░░░░░░░░░░  2-3 months          │
│                                                                             │
│  In-House Enterpr ████████████████████████████████████  8-12 months        │
│                                                                             │
│                   └────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬─────│
│                        1m   2m   3m   4m   5m   6m   7m   8m   9m  10m 12m │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8. Multi-Channel Integration Complexity

| Channel | AWS Lex | In-House |
|---------|---------|----------|
| **Web Chat** | Built-in widget, 1-2 hours | Custom development, 2-4 weeks |
| **Mobile App** | SDK available, 1-2 days | Custom API integration, 4-6 weeks |
| **Voice (IVR)** | Amazon Connect, 1 day | Twilio/Genesys integration, 2-3 months |
| **SMS** | Amazon Pinpoint, 1 day | Twilio integration, 2-4 weeks |
| **Messaging Apps** | Pre-built connectors, 1-2 days | Custom OAuth/webhooks, 1-2 months |
| **Contact Center** | Native AWS integration | Complex CTI development, 3-6 months |

| Integration Aspect | AWS Lex Complexity | In-House Complexity |
|-------------------|-------------------|---------------------|
| Channel consistency | Automatic | Requires custom orchestration |
| Session management | Built-in | Custom state machine |
| Context handoff | Native | Complex middleware |
| Analytics | CloudWatch integrated | Custom data pipeline |
| A/B testing | Built-in | Custom implementation |

### 9. When In-House Might Make Sense

Despite the significant cost advantage of AWS Lex, in-house development may be justified in specific scenarios:

#### Scenarios Favoring In-House

| Scenario | Reason | Considerations |
|----------|--------|----------------|
| **Extreme customization** | Proprietary NLU models for specialized domains | Consider Lex + SageMaker hybrid first |
| **Data sovereignty** | Strict on-premise data requirements | Evaluate AWS GovCloud or Outposts |
| **Existing ML team** | Significant sunk cost in NLP expertise | Hybrid approach may leverage both |
| **Competitive advantage** | Conversational AI is core differentiator | Long-term strategic investment |
| **Volume exceeding 10M+/month** | Scale economics shift at very high volume | Break-even analysis required |

#### Decision Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Build vs Buy Decision Matrix                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                          Strategic Importance                               │
│                     Low                         High                        │
│                      │                           │                          │
│         ┌────────────┼───────────────────────────┼────────────┐             │
│         │            │                           │            │             │
│    High │   HYBRID   │       IN-HOUSE            │            │             │
│         │   Consider │       Consider if:        │            │             │
│  Custom │   Lex +    │       - Core business     │            │             │
│   Needs │   SageMaker│       - 10M+ requests/mo  │            │             │
│         │            │       - ML team exists    │            │             │
│         ├────────────┼───────────────────────────┤            │             │
│         │            │                           │            │             │
│    Low  │  AWS LEX   │       AWS LEX             │            │             │
│         │  Clear     │       with custom         │            │             │
│         │  winner    │       Lambda hooks        │            │             │
│         │            │                           │            │             │
│         └────────────┴───────────────────────────┴────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Cost Break-Even Analysis

For in-house to match AWS Lex cost efficiency:

| Monthly Requests | AWS Lex Cost | In-House Cost | Break-Even? |
|------------------|--------------|---------------|-------------|
| 100,000 | $75 | $86,100 | No (1,148x more expensive) |
| 1,000,000 | $750 | $86,100 | No (115x more expensive) |
| 10,000,000 | $7,500 | $86,100 | No (11.5x more expensive) |
| 50,000,000 | $37,500 | $86,100 | No (2.3x more expensive) |
| 100,000,000+ | $75,000 | $86,100 | Approaching parity |

> In-house solutions only become cost-competitive at extreme scale (100M+ requests/month), and even then, the time-to-market and maintenance overhead favor managed services for most organizations.

---

## Recommendations

1. **Start with text-only** - Voice adds 10x cost
2. **Invest in NLU training** - Reduce fallback rate to <10%
3. **Use response cards** - Reduce conversation turns
4. **Monitor conversation metrics** - Track success rate and turns
5. **Consider multi-language early** - Lex handles it natively
6. **Use session attributes** - Reduce re-prompting
7. **Implement context carryover** - Smoother conversations

