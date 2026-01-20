"""Pytest configuration and fixtures for Healthcare Imaging Data Lake."""

from datetime import datetime
from typing import Any, Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from moto import mock_aws

from src.common.config import Settings
from src.common.models import (
    AccessLevel,
    BodyPart,
    ClinicalRecord,
    ImageFormat,
    ImageMetadata,
    Modality,
)


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        aws_region="us-east-1",
        images_bucket="test-images-bucket",
        metadata_bucket="test-metadata-bucket",
        results_bucket="test-results-bucket",
        kms_key_id="test-kms-key-id",
        glue_database="test_healthcare_imaging",
        glue_crawler_name="test-crawler",
        athena_workgroup="test-workgroup",
        enable_lakeformation=True,
        log_level="DEBUG",
    )


@pytest.fixture
def sample_image_metadata() -> ImageMetadata:
    """Create sample image metadata."""
    return ImageMetadata(
        image_id=str(uuid4()),
        study_id=f"STUDY-{uuid4().hex[:8].upper()}",
        series_id=f"SERIES-{uuid4().hex[:8].upper()}",
        patient_id="HASH_PATIENT_001",
        modality=Modality.CT,
        body_part=BodyPart.CHEST,
        facility_id="FACILITY_001",
        acquisition_date=datetime(2024, 1, 15, 10, 30, 0),
        s3_uri="s3://test-images-bucket/images/facility=FACILITY_001/modality=CT/2024/01/15/test.dcm",
        file_size_bytes=52428800,
        image_format=ImageFormat.DICOM,
        condition_codes=["J18.9", "R06.0"],
        dicom_tags={
            "Manufacturer": "TestMfg",
            "InstitutionName": "Test Hospital",
            "StudyDescription": "CT Chest",
        },
    )


@pytest.fixture
def sample_clinical_record() -> ClinicalRecord:
    """Create sample clinical record."""
    return ClinicalRecord(
        record_id=str(uuid4()),
        patient_id="HASH_PATIENT_001",
        study_id=f"STUDY-{uuid4().hex[:8].upper()}",
        diagnosis="Pneumonia",
        condition_codes=["J18.9"],
        physician_id="PHYSICIAN_001",
        facility_id="FACILITY_001",
        record_date=datetime(2024, 1, 15),
        notes_summary="Patient presents with respiratory symptoms",
    )


@pytest.fixture
def mock_s3_client() -> Generator[MagicMock, None, None]:
    """Mock S3 client."""
    with mock_aws():
        import boto3

        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-images-bucket")
        client.create_bucket(Bucket="test-metadata-bucket")
        client.create_bucket(Bucket="test-results-bucket")
        yield client


@pytest.fixture
def mock_kms_client() -> Generator[MagicMock, None, None]:
    """Mock KMS client."""
    with mock_aws():
        import boto3

        client = boto3.client("kms", region_name="us-east-1")
        key = client.create_key(Description="Test key")
        yield client


@pytest.fixture
def mock_glue_client() -> Generator[MagicMock, None, None]:
    """Mock Glue client."""
    with mock_aws():
        import boto3

        client = boto3.client("glue", region_name="us-east-1")
        client.create_database(
            DatabaseInput={
                "Name": "test_healthcare_imaging",
                "Description": "Test healthcare imaging database",
            }
        )
        yield client


@pytest.fixture
def mock_athena_client() -> Generator[MagicMock, None, None]:
    """Mock Athena client."""
    with mock_aws():
        import boto3

        client = boto3.client("athena", region_name="us-east-1")
        yield client


@pytest.fixture
def mock_lakeformation_client() -> Generator[MagicMock, None, None]:
    """Mock Lake Formation client."""
    with patch("boto3.client") as mock_client:
        mock_lf = MagicMock()
        mock_client.return_value = mock_lf
        yield mock_lf


@pytest.fixture
def api_gateway_event() -> dict[str, Any]:
    """Create sample API Gateway event."""
    return {
        "httpMethod": "GET",
        "path": "/images",
        "pathParameters": None,
        "queryStringParameters": None,
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
        },
        "body": None,
        "requestContext": {
            "requestId": str(uuid4()),
            "stage": "dev",
            "identity": {"sourceIp": "127.0.0.1"},
        },
    }


@pytest.fixture
def s3_event() -> dict[str, Any]:
    """Create sample S3 event for image upload."""
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-images-bucket"},
                    "object": {
                        "key": "raw/facility=FACILITY_001/modality=CT/2024/01/15/test.dcm",
                        "size": 52428800,
                    },
                },
            }
        ]
    }


@pytest.fixture
def lambda_context() -> MagicMock:
    """Create mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = str(uuid4())
    context.get_remaining_time_in_millis.return_value = 30000
    return context
