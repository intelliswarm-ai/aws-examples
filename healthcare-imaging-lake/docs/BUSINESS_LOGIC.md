# Business Logic: Healthcare Imaging Data Lake

## Executive Summary

This document describes the business logic for a HIPAA-compliant healthcare imaging data lake designed to organize patient medical imaging data and clinical records for training diagnostic ML models.

## Use Case

### Problem Statement

A healthcare ML team needs to:
1. **Organize** 10+ million patient medical images with associated clinical records
2. **Comply** with HIPAA requirements for PHI protection
3. **Query** across multi-modal data (images and structured clinical data)
4. **Extract** subsets for specific medical conditions for ML training

### Solution Overview

| Requirement | AWS Solution |
|-------------|--------------|
| Secure image storage | S3 with SSE-KMS (customer-managed keys) |
| Unified metadata | Glue Data Catalog with crawlers |
| HIPAA access control | Lake Formation row/cell-level security |
| Multi-modal queries | Athena SQL across images + clinical data |
| Subset extraction | Filtered queries by condition codes |

## Data Model

### Image Metadata Schema

```
imaging_metadata
├── image_id (string, PK)           # UUID for the image
├── study_id (string)               # DICOM Study Instance UID
├── series_id (string)              # DICOM Series Instance UID
├── patient_id (string, PHI)        # Encrypted patient reference
├── modality (string)               # CT, MRI, XRAY, ULTRASOUND, etc.
├── body_part (string)              # CHEST, HEAD, ABDOMEN, etc.
├── laterality (string)             # LEFT, RIGHT, BILATERAL
├── facility_id (string)            # Healthcare facility identifier
├── acquisition_date (timestamp)    # When the image was acquired
├── s3_uri (string)                 # S3 location of the image
├── file_size_bytes (bigint)        # Image file size
├── image_format (string)           # DICOM, PNG, JPEG
├── pixel_spacing (array<double>)   # Pixel spacing in mm
├── slice_thickness (double)        # For CT/MRI slice thickness
├── rows (int)                      # Image height in pixels
├── columns (int)                   # Image width in pixels
├── bits_allocated (int)            # Bits per pixel
├── dicom_tags (map<string,string>) # Additional DICOM metadata
├── condition_codes (array<string>) # ICD-10 codes from clinical linkage
├── created_at (timestamp)          # Record creation timestamp
└── partition columns:
    ├── year (string)
    ├── month (string)
    └── day (string)
```

### Clinical Records Schema

```
clinical_records
├── record_id (string, PK)          # UUID for the record
├── patient_id (string, PHI)        # Encrypted patient reference
├── study_id (string)               # Links to imaging_metadata
├── encounter_id (string)           # Hospital encounter ID
├── diagnosis (string, PHI)         # Primary diagnosis text
├── condition_codes (array<string>) # ICD-10 diagnosis codes
├── procedure_codes (array<string>) # CPT procedure codes
├── physician_id (string)           # Treating physician
├── facility_id (string)            # Healthcare facility
├── record_date (timestamp)         # Date of clinical record
├── notes_summary (string, PHI)     # De-identified notes summary
├── age_at_study (int)              # Patient age (de-identified)
├── sex (string)                    # Patient sex
├── created_at (timestamp)          # Record creation timestamp
└── partition columns:
    ├── year (string)
    ├── month (string)
    └── day (string)
```

## Data Flow

### 1. Image Ingestion Flow

```
Source System → API Gateway → Ingestion Lambda → S3 (SSE-KMS)
                                    │
                                    └──→ Metadata → S3 (Parquet)
                                              │
                                              └──→ Glue Crawler → Catalog
```

**Steps:**
1. Healthcare system uploads DICOM image via presigned URL
2. Ingestion Lambda extracts DICOM metadata
3. Image stored in S3 with SSE-KMS encryption
4. Metadata written as Parquet to metadata bucket
5. Glue Crawler updates Data Catalog

### 2. Clinical Record Ingestion

```
EHR System → API Gateway → Ingestion Lambda → S3 (Parquet)
                                                    │
                                                    └──→ Glue Crawler → Catalog
```

**Steps:**
1. EHR system sends clinical records batch
2. Lambda validates and de-identifies sensitive fields
3. Records stored as Parquet with partition columns
4. Crawler updates catalog with new partitions

### 3. Query Flow (ML Subset Extraction)

```
ML Engineer → API Gateway → Query Lambda → Lake Formation
                                               │
                                               ├──→ Permission Check
                                               │
                                               └──→ Athena → S3 Results
```

**Steps:**
1. ML engineer submits query via API
2. Lake Formation validates row/cell-level permissions
3. Athena executes query against partitioned data
4. Results written to encrypted S3 bucket
5. Presigned URL returned for secure download

## Access Control Matrix

### Lake Formation Permissions

| Role | imaging_metadata | clinical_records | Filter |
|------|------------------|------------------|--------|
| Data Admin | ALL | ALL | None |
| ML Engineer | SELECT | SELECT | `facility_id IN (allowed)` |
| Researcher | SELECT (limited columns) | SELECT (limited columns) | `facility_id = 'research_facility'` |
| Auditor | SELECT | SELECT | Read-only, audit trail |

### Column-Level Security

| Column | Data Admin | ML Engineer | Researcher |
|--------|------------|-------------|------------|
| patient_id | Visible | Masked | Masked |
| diagnosis | Visible | Visible | Masked |
| notes_summary | Visible | Masked | Hidden |
| condition_codes | Visible | Visible | Visible |
| s3_uri | Visible | Visible | Hidden |

### Row-Level Filtering

```sql
-- ML Engineer filter (example)
CREATE ROW ACCESS POLICY ml_engineer_policy
ON imaging_metadata
FOR SELECT
TO 'arn:aws:iam::ACCOUNT:role/MLEngineerRole'
USING (facility_id IN ('FACILITY_A', 'FACILITY_B'))
```

## Business Rules

### Ingestion Rules

1. **Image Validation**
   - DICOM files must have valid Study/Series/SOP Instance UIDs
   - Minimum required DICOM tags: Modality, Patient ID, Study Date
   - Maximum file size: 2 GB per image

2. **Metadata Enrichment**
   - Extract standard DICOM tags automatically
   - Link to clinical records via study_id
   - Populate condition_codes from clinical linkage

3. **De-identification**
   - Patient names removed from DICOM metadata
   - Dates shifted within +/- 365 days (configurable)
   - Free-text notes summarized and de-identified

### Query Rules

1. **Query Limits**
   - Maximum bytes scanned: 100 GB per query
   - Query timeout: 300 seconds
   - Result set limit: 1 million rows

2. **Subset Extraction**
   - ML training subsets must include condition_codes
   - Minimum cohort size: 100 images per condition
   - Balanced sampling recommended for rare conditions

3. **Audit Requirements**
   - All queries logged to CloudTrail
   - PHI access triggers audit event
   - Monthly access reports required

## Common Query Patterns

### 1. Find Images by Condition

```sql
SELECT
    image_id,
    s3_uri,
    modality,
    body_part,
    condition_codes
FROM imaging_metadata
WHERE ARRAY_CONTAINS(condition_codes, 'J18.9')  -- Pneumonia
  AND modality = 'CT'
  AND body_part = 'CHEST'
  AND acquisition_date >= DATE '2024-01-01'
```

### 2. Join Images with Clinical Data

```sql
SELECT
    i.image_id,
    i.s3_uri,
    i.modality,
    c.diagnosis,
    c.condition_codes
FROM imaging_metadata i
JOIN clinical_records c
    ON i.study_id = c.study_id
WHERE c.condition_codes IS NOT NULL
  AND CARDINALITY(c.condition_codes) > 0
```

### 3. Aggregate Statistics by Modality

```sql
SELECT
    modality,
    body_part,
    COUNT(*) as image_count,
    COUNT(DISTINCT patient_id) as patient_count,
    SUM(file_size_bytes) / (1024*1024*1024) as total_gb
FROM imaging_metadata
WHERE year = '2024'
GROUP BY modality, body_part
ORDER BY image_count DESC
```

### 4. ML Training Cohort Extraction

```sql
-- Extract balanced cohort for pneumonia vs normal chest CTs
WITH pneumonia AS (
    SELECT image_id, s3_uri, 'pneumonia' as label
    FROM imaging_metadata
    WHERE ARRAY_CONTAINS(condition_codes, 'J18.9')
      AND modality = 'CT'
      AND body_part = 'CHEST'
    LIMIT 5000
),
normal AS (
    SELECT image_id, s3_uri, 'normal' as label
    FROM imaging_metadata
    WHERE NOT ARRAY_CONTAINS(condition_codes, 'J18.9')
      AND modality = 'CT'
      AND body_part = 'CHEST'
      AND condition_codes = ARRAY[]
    LIMIT 5000
)
SELECT * FROM pneumonia
UNION ALL
SELECT * FROM normal
```

## Error Handling

### Ingestion Errors

| Error | Code | Action |
|-------|------|--------|
| Invalid DICOM | `INVALID_DICOM` | Reject, notify sender |
| Missing required tags | `MISSING_TAGS` | Reject, return missing list |
| Duplicate image_id | `DUPLICATE` | Skip, log warning |
| KMS encryption failure | `ENCRYPTION_ERROR` | Retry 3x, then DLQ |
| S3 write failure | `STORAGE_ERROR` | Retry 3x, then DLQ |

### Query Errors

| Error | Code | Action |
|-------|------|--------|
| Permission denied | `ACCESS_DENIED` | Return 403, log audit event |
| Query timeout | `TIMEOUT` | Cancel query, suggest optimization |
| Bytes limit exceeded | `LIMIT_EXCEEDED` | Cancel query, suggest partitioning |
| Invalid SQL | `INVALID_QUERY` | Return 400 with error details |

## Compliance Considerations

### HIPAA Technical Safeguards

| Safeguard | Implementation |
|-----------|----------------|
| Access Control | Lake Formation row/cell-level security |
| Audit Controls | CloudTrail, CloudWatch Logs, S3 access logs |
| Integrity | S3 Object Lock (optional), versioning |
| Transmission Security | HTTPS only, VPC endpoints |
| Encryption | SSE-KMS with customer-managed keys |

### Data Retention

| Data Type | Retention | Storage Class |
|-----------|-----------|---------------|
| Images (active) | Indefinite | S3 Standard |
| Images (archived) | 7 years | S3 Glacier |
| Metadata | 7 years | S3 Standard |
| Query results | 30 days | S3 Standard, TTL |
| Audit logs | 7 years | S3 Glacier |

## Performance Optimization

### Partitioning Strategy

- **Time-based**: year/month/day for temporal queries
- **Modality-based**: CT, MRI, XRAY for type filtering
- **Facility-based**: For multi-tenant access patterns

### Query Optimization Tips

1. Always filter by partition columns first
2. Use LIMIT for exploratory queries
3. Select only required columns
4. Use approximate functions for large aggregations
5. Consider materialized views for common queries

## Monitoring Metrics

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Ingestion rate | < 100/min | Warning |
| Ingestion errors | > 1% | Critical |
| Query latency (p95) | > 30s | Warning |
| Bytes scanned/query | > 50 GB | Warning |
| Access denied events | > 10/hour | Critical |
| KMS key usage | > 10,000/day | Warning |
