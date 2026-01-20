"""Ingestion handler for healthcare imaging data lake."""

import json
from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from src.common.config import settings
from src.common.exceptions import IngestionError
from src.common.models import (
    ClinicalRecord,
    ImageMetadata,
    IngestionResult,
    PartitionSpec,
)
from src.services import get_kms_service, get_s3_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle image and clinical record ingestion.

    Supports multiple event sources:
    - API Gateway: Direct ingestion requests
    - S3: New image uploads
    - Direct invocation: Batch processing

    Args:
        event: Lambda event.
        context: Lambda context.

    Returns:
        Response with ingestion results.
    """
    event_type = _get_event_type(event)
    logger.info("Processing ingestion event", extra={"event_type": event_type})

    try:
        if event_type == "api_gateway":
            return _handle_api_request(event)
        elif event_type == "s3":
            return _handle_s3_event(event)
        else:
            return _handle_direct_invocation(event)

    except IngestionError as e:
        logger.error(f"Ingestion error: {e}")
        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
        return _error_response(400, str(e), e.error_code)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
        return _error_response(500, "Internal server error", "INTERNAL_ERROR")


def _get_event_type(event: dict[str, Any]) -> str:
    """Determine event source type."""
    if "httpMethod" in event or "requestContext" in event:
        return "api_gateway"
    elif "Records" in event:
        records = event["Records"]
        if records and "s3" in records[0]:
            return "s3"
    return "direct"


def _handle_api_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle API Gateway ingestion request."""
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    record_type = body.get("type", "imaging")
    records = body.get("records", [])

    if not records:
        return _error_response(400, "No records provided", "MISSING_RECORDS")

    if record_type == "imaging":
        result = _ingest_imaging_metadata(records)
    elif record_type == "clinical":
        result = _ingest_clinical_records(records)
    else:
        return _error_response(400, f"Unknown record type: {record_type}", "INVALID_TYPE")

    metrics.add_metric(
        name="RecordsIngested",
        unit=MetricUnit.Count,
        value=result.records_processed,
    )

    return _api_response(
        200 if result.success else 207,
        result.model_dump(mode="json"),
    )


def _handle_s3_event(event: dict[str, Any]) -> dict[str, Any]:
    """Handle S3 event for new image uploads."""
    results = []

    for record in event["Records"]:
        s3_info = record["s3"]
        bucket = s3_info["bucket"]["name"]
        key = s3_info["object"]["key"]
        size = s3_info["object"]["size"]

        logger.info("Processing S3 upload", extra={"bucket": bucket, "key": key})

        # Extract metadata from S3 object metadata
        s3_service = get_s3_service()
        try:
            # Create basic metadata from S3 event
            # In production, this would extract DICOM metadata
            metadata = _create_metadata_from_s3(bucket, key, size)
            result = _ingest_imaging_metadata([metadata.model_dump()])
            results.append(result.model_dump(mode="json"))

        except Exception as e:
            logger.error(f"Failed to process S3 object: {e}")
            results.append(
                IngestionResult(
                    success=False,
                    records_failed=1,
                    errors=[str(e)],
                ).model_dump(mode="json")
            )

    return {"statusCode": 200, "body": json.dumps({"results": results})}


def _handle_direct_invocation(event: dict[str, Any]) -> dict[str, Any]:
    """Handle direct Lambda invocation."""
    record_type = event.get("type", "imaging")
    records = event.get("records", [])

    if record_type == "imaging":
        result = _ingest_imaging_metadata(records)
    elif record_type == "clinical":
        result = _ingest_clinical_records(records)
    else:
        result = IngestionResult(
            success=False,
            errors=[f"Unknown record type: {record_type}"],
        )

    return result.model_dump(mode="json")


def _ingest_imaging_metadata(records: list[dict[str, Any]]) -> IngestionResult:
    """Ingest imaging metadata records."""
    s3_service = get_s3_service()
    kms_service = get_kms_service()

    validated_records: list[ImageMetadata] = []
    errors: list[str] = []

    for i, record in enumerate(records):
        try:
            # Encrypt patient_id if not already encrypted
            if "patient_id" in record and not record.get("_encrypted"):
                record["patient_id"] = kms_service.encrypt_patient_id(
                    record["patient_id"],
                    record.get("facility_id", "default"),
                )

            metadata = ImageMetadata(**record)
            validated_records.append(metadata)

        except ValidationError as e:
            errors.append(f"Record {i}: {e}")
            logger.warning(f"Validation error for record {i}: {e}")

    if not validated_records:
        return IngestionResult(
            success=False,
            records_failed=len(records),
            errors=errors,
        )

    # Group by partition for efficient writing
    partitioned: dict[str, list[ImageMetadata]] = {}
    for record in validated_records:
        partition_key = record.partition.path
        if partition_key not in partitioned:
            partitioned[partition_key] = []
        partitioned[partition_key].append(record)

    # Write each partition batch
    total_processed = 0
    for partition_path, batch in partitioned.items():
        partition = batch[0].partition
        result = s3_service.write_metadata_batch(batch, partition, "imaging")
        if result.success:
            total_processed += result.records_processed
        else:
            errors.extend(result.errors)

    return IngestionResult(
        success=len(errors) == 0,
        records_processed=total_processed,
        records_failed=len(records) - total_processed,
        errors=errors,
    )


def _ingest_clinical_records(records: list[dict[str, Any]]) -> IngestionResult:
    """Ingest clinical records."""
    s3_service = get_s3_service()
    kms_service = get_kms_service()

    validated_records: list[ClinicalRecord] = []
    errors: list[str] = []

    for i, record in enumerate(records):
        try:
            # Encrypt patient_id if not already encrypted
            if "patient_id" in record and not record.get("_encrypted"):
                record["patient_id"] = kms_service.encrypt_patient_id(
                    record["patient_id"],
                    record.get("facility_id", "default"),
                )

            clinical = ClinicalRecord(**record)
            validated_records.append(clinical)

        except ValidationError as e:
            errors.append(f"Record {i}: {e}")

    if not validated_records:
        return IngestionResult(
            success=False,
            records_failed=len(records),
            errors=errors,
        )

    # Group by partition
    partitioned: dict[str, list[ClinicalRecord]] = {}
    for record in validated_records:
        partition_key = record.partition.path
        if partition_key not in partitioned:
            partitioned[partition_key] = []
        partitioned[partition_key].append(record)

    # Write each partition batch
    total_processed = 0
    for partition_path, batch in partitioned.items():
        partition = batch[0].partition
        result = s3_service.write_metadata_batch(batch, partition, "clinical")
        if result.success:
            total_processed += result.records_processed
        else:
            errors.extend(result.errors)

    return IngestionResult(
        success=len(errors) == 0,
        records_processed=total_processed,
        records_failed=len(records) - total_processed,
        errors=errors,
    )


def _create_metadata_from_s3(bucket: str, key: str, size: int) -> ImageMetadata:
    """Create ImageMetadata from S3 object info.

    In production, this would parse DICOM metadata.
    """
    # Parse partition info from key
    # Expected: images/facility={id}/modality={mod}/year={y}/month={m}/day={d}/{study}_{image}.dcm
    parts = key.split("/")

    facility_id = "unknown"
    modality = "OTHER"
    year = datetime.utcnow().strftime("%Y")
    month = datetime.utcnow().strftime("%m")
    day = datetime.utcnow().strftime("%d")

    for part in parts:
        if part.startswith("facility="):
            facility_id = part.split("=")[1]
        elif part.startswith("modality="):
            modality = part.split("=")[1]
        elif part.startswith("year="):
            year = part.split("=")[1]
        elif part.startswith("month="):
            month = part.split("=")[1]
        elif part.startswith("day="):
            day = part.split("=")[1]

    # Extract filename parts
    filename = parts[-1] if parts else "unknown_unknown.dcm"
    name_parts = filename.replace(".dcm", "").split("_")
    study_id = name_parts[0] if len(name_parts) > 0 else "unknown"
    image_id = name_parts[1] if len(name_parts) > 1 else "unknown"

    return ImageMetadata(
        image_id=image_id,
        study_id=study_id,
        patient_id="pending_extraction",  # Would be extracted from DICOM
        modality=modality,
        body_part="OTHER",  # Would be extracted from DICOM
        facility_id=facility_id,
        acquisition_date=datetime(int(year), int(month), int(day)),
        s3_uri=f"s3://{bucket}/{key}",
        file_size_bytes=size,
    )


def _api_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
) -> dict[str, Any]:
    """Create error response."""
    return _api_response(
        status_code,
        {"error": message, "error_code": error_code},
    )
