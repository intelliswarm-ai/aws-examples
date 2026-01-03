# Business Logic - Fraud Detection Pipeline

This document describes the business logic and ML approach used in the EMR Spark Fraud Detection Pipeline.

## Overview

The fraud detection system processes financial transactions in near real-time, computing ML features and scoring each transaction for fraud probability. Transactions exceeding defined thresholds trigger alerts for investigation.

## Transaction Processing Flow

### 1. Transaction Ingestion

Transactions arrive via API Gateway with the following structure:

```json
{
  "transaction_id": "tx-12345",
  "account_id": "ACC123456789",
  "merchant_id": "MERCHANT001",
  "transaction_type": "PURCHASE",
  "channel": "ONLINE",
  "amount": "150.50",
  "currency": "USD",
  "timestamp": "2024-01-15T14:30:00Z",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "country": "US",
    "city": "New York"
  },
  "device_info": {
    "device_id": "device-123",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### 2. Feature Engineering

The system computes several categories of features:

#### Temporal Features
- `hour_of_day`: Hour when transaction occurred (0-23)
- `day_of_week`: Day of week (1-7)
- `is_weekend`: Binary flag for weekend transactions

#### Velocity Features
- `tx_count_1h`: Number of transactions in the last hour
- `tx_count_24h`: Number of transactions in the last 24 hours
- `tx_amount_1h`: Total amount transacted in the last hour
- `tx_amount_24h`: Total amount transacted in the last 24 hours

#### Statistical Features
- `avg_amount_30d`: Average transaction amount over 30 days
- `std_amount_30d`: Standard deviation of amounts over 30 days
- `amount_zscore`: Z-score of current amount relative to history

#### Distance Features
- `distance_from_last`: Kilometers from last transaction location
- `time_since_last`: Hours since last transaction

#### Behavioral Features
- `is_new_merchant`: First transaction with this merchant
- `is_new_device`: First transaction from this device
- `is_high_risk_country`: Transaction from high-risk geography

#### Categorical Encoding
- `channel_encoded`: Numeric encoding of transaction channel
- `tx_type_encoded`: Numeric encoding of transaction type

### 3. Fraud Classification

The ML model outputs a **fraud score** between 0.0 and 1.0:

| Score Range | Classification | Action |
|-------------|---------------|--------|
| >= 0.7 | **FRAUDULENT** | Block transaction, create HIGH alert |
| 0.4 - 0.7 | **SUSPICIOUS** | Flag for review, create MEDIUM alert |
| < 0.4 | **LEGITIMATE** | Allow transaction, no alert |

### 4. Risk Factors

The system identifies specific risk factors that contributed to the fraud score:

| Risk Factor | Condition |
|-------------|-----------|
| `HIGH_AMOUNT` | Amount Z-score > 2.0 |
| `HIGH_VELOCITY` | > 5 transactions in 1 hour |
| `NEW_MERCHANT` | First-time merchant |
| `NEW_DEVICE` | First-time device |
| `HIGH_RISK_LOCATION` | Transaction from high-risk country |
| `IMPOSSIBLE_TRAVEL` | > 100km travel in < 1 hour |
| `ODD_HOURS` | Transaction before 6 AM or after 10 PM |

## ML Model

### Algorithm: Random Forest Classifier

- **Ensemble**: 100 decision trees
- **Max Depth**: 10 levels
- **Features**: 18 engineered features
- **Target**: Binary (fraud = 1, legitimate = 0)

### Model Training

Training occurs on labeled historical data:

1. Load 30 days of feature vectors
2. Split 80/20 for train/test
3. Train Random Forest with cross-validation
4. Evaluate on test set (AUC, Precision, Recall, F1)
5. Save model and metrics to S3

### Model Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| AUC | > 0.95 | Area under ROC curve |
| Precision | > 0.90 | Minimize false positives |
| Recall | > 0.85 | Catch most fraud |
| F1 Score | > 0.87 | Balanced performance |

### Model Versioning

Models are versioned in S3:
```
s3://models-bucket/models/
├── v1.0/
│   ├── model/              # Spark ML model files
│   ├── metadata.json       # Feature names, thresholds
│   └── metrics.json        # Training metrics
├── v1.1/
└── latest -> v1.1
```

## Alert Management

### Alert Lifecycle

1. **Created**: Alert generated from fraud detection
2. **Pending**: Awaiting analyst review
3. **Acknowledged**: Analyst has reviewed
4. **Resolved**: Investigation complete

### Alert Structure

```json
{
  "alert_id": "alert-12345",
  "transaction_id": "tx-12345",
  "account_id": "ACC123456789",
  "fraud_score": 0.85,
  "severity": "HIGH",
  "alert_type": "FRAUD_DETECTED",
  "risk_factors": ["HIGH_AMOUNT", "NEW_MERCHANT"],
  "message": "High-risk transaction detected",
  "recommended_action": "Block transaction and contact customer",
  "created_at": "2024-01-15T14:30:00Z",
  "acknowledged": false
}
```

### Notification Rules

| Severity | Notification Channel | SLA |
|----------|---------------------|-----|
| HIGH | SNS (Email/SMS) | Immediate |
| MEDIUM | SNS (Email) | 15 minutes |
| LOW | Dashboard only | 1 hour |

## Pipeline Execution Modes

### FULL Mode
- Feature engineering
- Model training (if scheduled)
- Batch scoring
- Alert generation

### SCORING_ONLY Mode
- Skip feature engineering (use existing)
- Load existing model
- Batch scoring only
- For quick re-scoring with new thresholds

### TRAINING Mode
- Feature engineering
- Model training
- Skip scoring
- For scheduled model retraining

## Data Retention

| Data Type | Retention | Storage Class |
|-----------|-----------|---------------|
| Raw transactions | 90 days | S3 Standard |
| Feature vectors | 30 days | S3 Intelligent-Tiering |
| Predictions | 1 year | S3 Glacier after 90 days |
| Alerts | 2 years | DynamoDB |
| Models | Indefinite | S3 Standard |

## Business Rules

### Threshold Adjustments

Thresholds can be adjusted based on:
- **Time of day**: Lower thresholds during high-fraud hours
- **Account type**: Higher thresholds for trusted accounts
- **Merchant category**: Custom thresholds by merchant type
- **Geographic region**: Regional risk adjustments

### Exemptions

Certain transactions may bypass fraud scoring:
- Pre-approved recurring payments
- Internal transfers within same institution
- Transactions below minimum threshold ($1)
- Whitelisted merchant-account pairs

## Metrics and KPIs

### Operational Metrics
- Transactions processed per minute
- Average scoring latency
- Alert generation rate
- False positive rate

### Business Metrics
- Fraud detection rate
- Fraud loss prevention ($)
- Customer friction score
- Alert-to-investigation ratio
