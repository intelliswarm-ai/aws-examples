# Healthcare Imaging Data Lake

A HIPAA-compliant healthcare imaging data lake for organizing patient medical imaging data and clinical records for ML model training. This solution enables multi-modal queries across images and structured data, with fine-grained access control for subset extraction based on specific medical conditions.

## Architecture Overview

```
                                    +------------------+
                                    |   API Gateway    |
                                    +--------+---------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v--------+      +--------v--------+      +--------v--------+
           |   Ingestion     |      |    Catalog      |      |     Query       |
           |    Lambda       |      |    Lambda       |      |    Lambda       |
           +--------+--------+      +--------+--------+      +--------+--------+
                    |                        |                        |
                    v                        v                        v
           +--------+--------+      +--------+--------+      +--------+--------+
           |       S3        |      |  Glue Catalog   |      |     Athena      |
           | (SSE-KMS)       |      |   + Crawlers    |      |   Workgroup     |
           +--------+--------+      +--------+--------+      +--------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                             |
                                    +--------v--------+
                                    | Lake Formation  |
                                    | (Row/Cell-Level |
                                    |    Security)    |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    |      KMS        |
                                    | (Customer Key)  |
                                    +-----------------+
```

## Use Case

A healthcare ML team needs to organize patient medical imaging data and associated clinical records for training diagnostic models. The solution addresses:

- **HIPAA Compliance**: Server-side encryption using customer-managed KMS keys
- **Multi-Modal Queries**: Unified metadata management for images and clinical records via Glue Data Catalog
- **Subset Extraction**: Lake Formation fine-grained access control with row and cell-level security
- **Scale**: Designed for 10+ million images with metadata

## Key AWS Services

| Service | Purpose |
|---------|---------|
| **S3** | Image storage with SSE-KMS encryption |
| **KMS** | Customer-managed encryption keys for HIPAA compliance |
| **Glue Data Catalog** | Unified metadata for images and clinical records |
| **Glue Crawlers** | Auto-discover schemas for new data |
| **Lake Formation** | Fine-grained access control (row/cell-level security) |
| **Athena** | SQL queries for multi-modal data and subset extraction |
| **Lambda** | Serverless handlers for ingestion, catalog, and query operations |
| **CloudWatch** | Monitoring, logging, and audit trails |

## HIPAA Compliance Features

### Encryption at Rest
- All S3 buckets use SSE-KMS with customer-managed keys
- Automatic key rotation enabled
- KMS key policies restrict access to authorized principals

### Fine-Grained Access Control
- **Row-Level Security**: Filter data by facility, physician, or patient cohort
- **Cell-Level Security**: Mask or hide PHI columns (patient_id, notes)
- **Column-Level Permissions**: Restrict access to sensitive metadata fields

### Audit Logging
- CloudWatch Logs encrypted with KMS
- S3 access logging enabled
- CloudTrail integration for API activity tracking

## Data Partitioning Strategy

```
s3://imaging-bucket/
├── images/
│   └── facility={facility_id}/
│       └── modality={CT|MRI|XRAY|ULTRASOUND}/
│           └── year={yyyy}/
│               └── month={mm}/
│                   └── day={dd}/
│                       └── {study_id}_{image_id}.dcm
└── metadata/
    └── year={yyyy}/
        └── month={mm}/
            └── day={dd}/
                └── metadata_{timestamp}.parquet
```

## Project Structure

```
healthcare-imaging-lake/
├── src/
│   ├── common/          # Shared code (config, models, exceptions)
│   ├── handlers/        # Lambda handlers (API, ingestion, catalog, query)
│   └── services/        # Business logic (S3, KMS, Glue, Lake Formation, Athena)
├── glue/                # Glue ETL jobs
├── terraform/           # Terraform modules
├── cloudformation/      # CloudFormation nested stacks
├── sam/                 # SAM templates
├── scripts/             # Deployment scripts
├── tests/               # Unit and integration tests
└── docs/                # Documentation
```

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.12+
- Terraform 1.5+ (for Terraform deployment)
- AWS SAM CLI (for SAM deployment)

### Deployment Options

#### Option 1: Terraform (Recommended)

```bash
cd healthcare-imaging-lake

# Build Lambda packages
./scripts/build.sh

# Deploy infrastructure
./scripts/deploy.sh
```

#### Option 2: AWS SAM

```bash
cd healthcare-imaging-lake

# Build and deploy
./scripts/build-sam.sh
./scripts/deploy-sam.sh
```

#### Option 3: CloudFormation

```bash
cd healthcare-imaging-lake/cloudformation

# Deploy nested stacks
./deploy-cfn.sh
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest` | Ingest image metadata |
| POST | `/ingest/batch` | Batch ingest multiple records |
| GET | `/catalog/tables` | List catalog tables |
| POST | `/catalog/crawl` | Trigger Glue crawler |
| POST | `/query` | Execute Athena query |
| GET | `/query/{id}` | Get query status |
| GET | `/query/{id}/results` | Get query results |

## Example Queries

### Find all CT scans for a specific condition

```sql
SELECT
    i.image_id,
    i.study_id,
    i.s3_uri,
    c.diagnosis
FROM imaging_metadata i
JOIN clinical_records c ON i.study_id = c.study_id
WHERE i.modality = 'CT'
  AND ARRAY_CONTAINS(c.condition_codes, 'J18.9')  -- Pneumonia
  AND i.acquisition_date >= DATE '2024-01-01'
```

### Extract subset for ML training

```sql
SELECT
    i.image_id,
    i.s3_uri,
    i.modality,
    i.body_part,
    c.condition_codes
FROM imaging_metadata i
JOIN clinical_records c ON i.study_id = c.study_id
WHERE i.modality IN ('CT', 'MRI')
  AND i.body_part = 'CHEST'
  AND c.condition_codes IS NOT NULL
LIMIT 10000
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `IMAGES_BUCKET` | S3 bucket for images | - |
| `METADATA_BUCKET` | S3 bucket for metadata | - |
| `RESULTS_BUCKET` | S3 bucket for query results | - |
| `KMS_KEY_ID` | Customer-managed KMS key ID | - |
| `GLUE_DATABASE` | Glue database name | `healthcare_imaging` |
| `ATHENA_WORKGROUP` | Athena workgroup | `healthcare_analytics` |

## Security Considerations

1. **Network Isolation**: Deploy Lambda functions in VPC with VPC endpoints for AWS services
2. **IAM Least Privilege**: Use permission boundaries and role-based access
3. **Data Classification**: Tag resources with sensitivity levels
4. **Encryption in Transit**: All API calls over HTTPS
5. **Access Logging**: Enable CloudTrail and S3 access logs

## Cost Optimization

- **S3 Intelligent-Tiering**: Automatic cost optimization for infrequently accessed images
- **Athena Query Limits**: Workgroup with bytes scanned limits
- **Glue Crawler Scheduling**: Run crawlers only when new data arrives
- **Lambda Provisioned Concurrency**: Reserved for predictable workloads

## References

- [Lake Formation Data Filtering](https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html)
- [Glue Encryption at Rest](https://docs.aws.amazon.com/glue/latest/dg/encryption-at-rest.html)
- [HIPAA on AWS](https://aws.amazon.com/compliance/hipaa-compliance/)
- [AWS Well-Architected Healthcare Lens](https://docs.aws.amazon.com/wellarchitected/latest/healthcare-industry-lens/welcome.html)

## License

This project is provided as a reference implementation. Review and adapt according to your specific compliance requirements.
