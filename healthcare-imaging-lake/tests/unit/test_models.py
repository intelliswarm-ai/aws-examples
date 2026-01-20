"""Unit tests for data models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.common.models import (
    AccessLevel,
    BodyPart,
    CatalogEntry,
    ClinicalRecord,
    ImageFormat,
    ImageMetadata,
    IngestionResult,
    Modality,
    QueryResult,
)


class TestImageMetadata:
    """Tests for ImageMetadata model."""

    def test_create_valid_image_metadata(self, sample_image_metadata):
        """Test creating valid image metadata."""
        assert sample_image_metadata.image_id is not None
        assert sample_image_metadata.modality == Modality.CT
        assert sample_image_metadata.body_part == BodyPart.CHEST
        assert "J18.9" in sample_image_metadata.condition_codes

    def test_image_metadata_auto_timestamps(self):
        """Test automatic timestamp generation."""
        metadata = ImageMetadata(
            study_id="STUDY-001",
            patient_id="PATIENT-001",
            modality=Modality.MRI,
            body_part=BodyPart.BRAIN,
            facility_id="FACILITY-001",
            acquisition_date=datetime.now(),
            s3_uri="s3://bucket/key",
            file_size_bytes=1000,
            image_format=ImageFormat.DICOM,
        )
        assert metadata.created_at is not None
        assert metadata.updated_at is not None

    def test_image_metadata_to_dict(self, sample_image_metadata):
        """Test converting image metadata to dictionary."""
        data = sample_image_metadata.to_dict()
        assert data["modality"] == "CT"
        assert data["body_part"] == "CHEST"
        assert isinstance(data["acquisition_date"], str)

    def test_image_metadata_to_parquet_dict(self, sample_image_metadata):
        """Test converting image metadata to Parquet-compatible dictionary."""
        data = sample_image_metadata.to_parquet_dict()
        assert "year" in data
        assert "month" in data
        assert data["year"] == 2024
        assert data["month"] == 1

    def test_image_metadata_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                study_id="STUDY-001",
                # Missing required fields
            )

    def test_image_metadata_modality_enum(self):
        """Test modality enum validation."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                study_id="STUDY-001",
                patient_id="PATIENT-001",
                modality="INVALID",  # Invalid modality
                body_part=BodyPart.BRAIN,
                facility_id="FACILITY-001",
                acquisition_date=datetime.now(),
                s3_uri="s3://bucket/key",
                file_size_bytes=1000,
                image_format=ImageFormat.DICOM,
            )


class TestClinicalRecord:
    """Tests for ClinicalRecord model."""

    def test_create_valid_clinical_record(self, sample_clinical_record):
        """Test creating valid clinical record."""
        assert sample_clinical_record.record_id is not None
        assert sample_clinical_record.diagnosis == "Pneumonia"
        assert "J18.9" in sample_clinical_record.condition_codes

    def test_clinical_record_to_dict(self, sample_clinical_record):
        """Test converting clinical record to dictionary."""
        data = sample_clinical_record.to_dict()
        assert data["diagnosis"] == "Pneumonia"
        assert isinstance(data["record_date"], str)

    def test_clinical_record_to_parquet_dict(self, sample_clinical_record):
        """Test converting clinical record to Parquet-compatible dictionary."""
        data = sample_clinical_record.to_parquet_dict()
        assert "year" in data
        assert "month" in data


class TestIngestionResult:
    """Tests for IngestionResult model."""

    def test_successful_ingestion_result(self):
        """Test creating successful ingestion result."""
        result = IngestionResult(
            image_id="test-image-id",
            success=True,
            s3_uri="s3://bucket/key",
            metadata_uri="s3://metadata/key",
        )
        assert result.success is True
        assert result.error_message is None

    def test_failed_ingestion_result(self):
        """Test creating failed ingestion result."""
        result = IngestionResult(
            image_id="test-image-id",
            success=False,
            error_message="Upload failed",
        )
        assert result.success is False
        assert result.error_message == "Upload failed"


class TestQueryResult:
    """Tests for QueryResult model."""

    def test_successful_query_result(self):
        """Test creating successful query result."""
        result = QueryResult(
            query_id="test-query-id",
            status="SUCCEEDED",
            result_location="s3://results/query.csv",
            row_count=100,
            data_scanned_bytes=1000000,
            execution_time_ms=5000,
        )
        assert result.status == "SUCCEEDED"
        assert result.row_count == 100

    def test_pending_query_result(self):
        """Test creating pending query result."""
        result = QueryResult(
            query_id="test-query-id",
            status="RUNNING",
        )
        assert result.status == "RUNNING"
        assert result.result_location is None


class TestCatalogEntry:
    """Tests for CatalogEntry model."""

    def test_create_catalog_entry(self):
        """Test creating catalog entry."""
        entry = CatalogEntry(
            database_name="healthcare_imaging",
            table_name="imaging_metadata",
            location="s3://metadata/imaging/",
            columns=[
                {"name": "image_id", "type": "string"},
                {"name": "modality", "type": "string"},
            ],
            partition_keys=[
                {"name": "year", "type": "int"},
                {"name": "month", "type": "int"},
            ],
        )
        assert entry.table_name == "imaging_metadata"
        assert len(entry.columns) == 2
        assert len(entry.partition_keys) == 2


class TestEnums:
    """Tests for enum values."""

    def test_modality_values(self):
        """Test Modality enum values."""
        assert Modality.CT.value == "CT"
        assert Modality.MRI.value == "MRI"
        assert Modality.XRAY.value == "XRAY"
        assert Modality.ULTRASOUND.value == "ULTRASOUND"

    def test_body_part_values(self):
        """Test BodyPart enum values."""
        assert BodyPart.HEAD.value == "HEAD"
        assert BodyPart.CHEST.value == "CHEST"
        assert BodyPart.ABDOMEN.value == "ABDOMEN"

    def test_image_format_values(self):
        """Test ImageFormat enum values."""
        assert ImageFormat.DICOM.value == "DICOM"
        assert ImageFormat.NIFTI.value == "NIFTI"
        assert ImageFormat.PNG.value == "PNG"

    def test_access_level_values(self):
        """Test AccessLevel enum values."""
        assert AccessLevel.FULL.value == "FULL"
        assert AccessLevel.RESEARCHER.value == "RESEARCHER"
        assert AccessLevel.ANALYST.value == "ANALYST"
