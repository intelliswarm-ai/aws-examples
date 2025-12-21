# AWS Kinesis - Real-Time GPS Tracking System

A real-time GPS tracking system for delivery trucks using Amazon Kinesis Data Streams.

## Use Case

A company plans to launch an application that tracks the GPS coordinates of delivery trucks in the country. The coordinates are transmitted from each delivery truck every five seconds. The system must be able to process coordinates from multiple consumers in real-time. The aggregated data will be analyzed in a separate reporting application.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  ┌─────────────┐    ┌─────────────────────────────────────┐                    │
│  │ Truck GPS   │    │         Kinesis Data Stream          │                    │
│  │ Simulator   │───▶│  (gps-coordinates-stream)            │                    │
│  │ (Lambda)    │    │  - 4 shards for high throughput      │                    │
│  └─────────────┘    │  - 24hr retention                    │                    │
│                     └───────────────┬─────────────────────┘                    │
│                                     │                                          │
│           ┌─────────────────────────┼─────────────────────────┐                │
│           │                         │                         │                │
│           ▼                         ▼                         ▼                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Real-Time       │    │ Geofence        │    │ Archive         │            │
│  │ Dashboard       │    │ Alert           │    │ Processor       │            │
│  │ Consumer        │    │ Consumer        │    │ Consumer        │            │
│  │ (Lambda)        │    │ (Lambda)        │    │ (Lambda)        │            │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘            │
│           │                      │                      │                      │
│           ▼                      ▼                      ▼                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ DynamoDB        │    │ SNS             │    │ S3              │            │
│  │ (latest pos)    │    │ (alerts)        │    │ (historical)    │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                                          │                     │
│                                                          ▼                     │
│                                                 ┌─────────────────┐            │
│                                                 │ Athena          │            │
│                                                 │ (analytics)     │            │
│                                                 └─────────────────┘            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. GPS Data Producer (Simulator)
- **Lambda Function**: Simulates GPS data from multiple trucks
- **EventBridge Rule**: Triggers every minute to generate batch of coordinates
- **Data Format**: JSON with truck_id, latitude, longitude, speed, heading, timestamp

### 2. Kinesis Data Stream
- **Stream Name**: `gps-coordinates-stream`
- **Shard Count**: 4 (scalable based on throughput needs)
- **Retention**: 24 hours (configurable up to 365 days)
- **Partition Key**: truck_id (ensures ordered processing per truck)

### 3. Real-Time Dashboard Consumer
- **Lambda Function**: Processes coordinates for live dashboard
- **DynamoDB Table**: Stores latest position per truck
- **Use Case**: Fleet management dashboard showing current truck locations

### 4. Geofence Alert Consumer
- **Lambda Function**: Checks if trucks enter/exit defined geofences
- **SNS Topic**: Publishes alerts for geofence violations
- **Use Case**: Notify when trucks deviate from expected routes

### 5. Archive Consumer
- **Lambda Function**: Archives all GPS data for historical analysis
- **S3 Bucket**: Stores data in Parquet format partitioned by date
- **Use Case**: Historical analytics, route optimization, compliance

## Technology Stack

- **Language**: Python 3.12
- **Infrastructure**: Terraform
- **AWS Services**:
  - Amazon Kinesis Data Streams
  - AWS Lambda
  - Amazon DynamoDB
  - Amazon S3
  - Amazon SNS
  - Amazon EventBridge
  - Amazon CloudWatch
  - AWS X-Ray

## Project Structure

```
aws-kinesis/
├── src/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   ├── models.py           # Pydantic data models
│   │   ├── clients.py          # AWS client initialization
│   │   └── exceptions.py       # Custom exceptions
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── gps_producer.py     # GPS data simulator
│   │   ├── dashboard_consumer.py   # Real-time dashboard processor
│   │   ├── geofence_consumer.py    # Geofence alert processor
│   │   └── archive_consumer.py     # S3 archival processor
│   └── services/
│       ├── __init__.py
│       ├── kinesis_service.py  # Kinesis operations
│       ├── geofence_service.py # Geofence calculations
│       └── aggregation_service.py  # Data aggregation
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars
│   └── modules/
│       ├── kinesis/
│       ├── lambda/
│       ├── dynamodb/
│       ├── s3/
│       ├── cloudwatch/
│       └── iam/
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── build.sh
│   ├── deploy.sh
│   └── test.sh
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Prerequisites

- Python 3.12+
- Terraform 1.5+
- AWS CLI configured with appropriate credentials
- Make (optional, for using Makefile)

## Quick Start

### 1. Install Dependencies

```bash
cd aws-kinesis
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

### 3. Run Tests

```bash
./scripts/test.sh
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STREAM_NAME` | Kinesis stream name | `gps-coordinates-stream` |
| `DYNAMODB_TABLE` | DynamoDB table for latest positions | `truck-positions` |
| `S3_BUCKET` | S3 bucket for archived data | `gps-archive-{account_id}` |
| `SNS_TOPIC_ARN` | SNS topic for geofence alerts | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Geofence Configuration

Geofences are defined in DynamoDB with the following structure:

```json
{
  "geofence_id": "warehouse-001",
  "name": "Main Warehouse",
  "type": "circle",
  "center": {"latitude": 47.3769, "longitude": 8.5417},
  "radius_meters": 500,
  "alert_on": "exit"
}
```

## Data Models

### GPS Coordinate Record

```json
{
  "truck_id": "TRK-001",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "latitude": 47.3769,
  "longitude": 8.5417,
  "speed_kmh": 45.5,
  "heading": 180,
  "altitude_m": 408,
  "accuracy_m": 5,
  "fuel_level_pct": 75,
  "engine_status": "running"
}
```

### Aggregated Statistics (per truck, per hour)

```json
{
  "truck_id": "TRK-001",
  "hour": "2024-01-15T10:00:00Z",
  "total_distance_km": 42.5,
  "average_speed_kmh": 38.2,
  "max_speed_kmh": 85,
  "idle_time_minutes": 12,
  "coordinates_count": 720
}
```

## Scaling Considerations

### Kinesis Shards
- Each shard: 1 MB/sec ingress, 2 MB/sec egress
- 1000 records/sec per shard
- Scale shards based on truck count and data frequency

### Capacity Planning
- 1000 trucks × 1 record/5 sec = 200 records/sec
- Average record size: 500 bytes
- Throughput: ~100 KB/sec
- Recommended: 2 shards (with headroom: 4 shards)

## Monitoring

CloudWatch dashboards include:
- Stream throughput (incoming/outgoing bytes)
- Iterator age (consumer lag)
- Success/failure rates per consumer
- DynamoDB read/write capacity
- Lambda invocations and errors

## Cost Optimization

- Use Enhanced Fan-Out only for consumers requiring sub-200ms latency
- Set appropriate shard count based on actual throughput
- Use S3 Intelligent-Tiering for archived data
- Consider Kinesis Data Firehose for simplified archival

## License

This project is licensed under the MIT License.
