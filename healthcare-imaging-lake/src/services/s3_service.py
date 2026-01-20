"""S3 service for healthcare imaging data lake with SSE-KMS encryption."""

import json
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import settings
from src.common.exceptions import EncryptionError, StorageError
from src.common.models import (
    ClinicalRecord,
    ImageMetadata,
    IngestionResult,
    PartitionSpec,
    S3Location,
)

logger = Logger()


class S3Service:
    """Service for S3 operations with SSE-KMS encryption."""

    def __init__(
        self,
        images_bucket: str | None = None,
        metadata_bucket: str | None = None,
        results_bucket: str | None = None,
        kms_key_id: str | None = None,
    ) -> None:
        """Initialize S3 service.

        Args:
            images_bucket: S3 bucket for storing images.
            metadata_bucket: S3 bucket for storing metadata.
            results_bucket: S3 bucket for query results.
            kms_key_id: KMS key ID for encryption.
        """
        self.images_bucket = images_bucket or settings.images_bucket
        self.metadata_bucket = metadata_bucket or settings.metadata_bucket
        self.results_bucket = results_bucket or settings.results_bucket
        self.kms_key_id = kms_key_id or settings.kms_key_id

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )
        self.client = boto3.client("s3", config=config, region_name=settings.aws_region)

    def write_image(
        self,
        image_data: bytes,
        metadata: ImageMetadata,
    ) -> str:
        """Write image to S3 with SSE-KMS encryption.

        Args:
            image_data: Binary image data.
            metadata: Image metadata.

        Returns:
            S3 URI of the stored image.

        Raises:
            StorageError: If upload fails.
            EncryptionError: If KMS encryption fails.
        """
        partition = metadata.partition
        s3_key = f"images/{partition.path}/{metadata.study_id}_{metadata.image_id}.dcm"

        try:
            self.client.put_object(
                Bucket=self.images_bucket,
                Key=s3_key,
                Body=image_data,
                ContentType="application/dicom",
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self.kms_key_id,
                Metadata={
                    "image-id": metadata.image_id,
                    "study-id": metadata.study_id,
                    "modality": metadata.modality.value,
                    "body-part": metadata.body_part.value,
                    "facility-id": metadata.facility_id,
                },
            )
            logger.info(
                "Image uploaded successfully",
                extra={"image_id": metadata.image_id, "s3_key": s3_key},
            )
            return f"s3://{self.images_bucket}/{s3_key}"

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ("KMSKeyNotFound", "KMSKeyDisabled", "KMSKeyInvalidState"):
                raise EncryptionError(
                    f"KMS encryption failed: {e}",
                    key_id=self.kms_key_id,
                    operation="encrypt",
                ) from e
            raise StorageError(
                f"Failed to upload image: {e}",
                bucket=self.images_bucket,
                key=s3_key,
                operation="put_object",
            ) from e

    def write_metadata_batch(
        self,
        records: list[ImageMetadata] | list[ClinicalRecord],
        partition: PartitionSpec,
        record_type: str = "imaging",
    ) -> IngestionResult:
        """Write metadata records as NDJSON to S3.

        Args:
            records: List of metadata records.
            partition: Partition specification.
            record_type: Type of records ('imaging' or 'clinical').

        Returns:
            IngestionResult with details of the operation.
        """
        if not records:
            return IngestionResult(
                success=True,
                records_processed=0,
                partition=partition,
            )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        prefix = "metadata" if record_type == "imaging" else "clinical"
        s3_key = f"{prefix}/{partition.path}/{record_type}_{timestamp}.json"

        # Convert to NDJSON
        lines = [record.model_dump_json() for record in records]
        content = "\n".join(lines)

        try:
            self.client.put_object(
                Bucket=self.metadata_bucket,
                Key=s3_key,
                Body=content.encode("utf-8"),
                ContentType="application/x-ndjson",
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self.kms_key_id,
            )

            s3_location = f"s3://{self.metadata_bucket}/{s3_key}"
            logger.info(
                "Metadata batch uploaded",
                extra={
                    "record_count": len(records),
                    "record_type": record_type,
                    "s3_location": s3_location,
                },
            )

            return IngestionResult(
                success=True,
                records_processed=len(records),
                s3_location=s3_location,
                partition=partition,
            )

        except ClientError as e:
            logger.error(f"Failed to write metadata batch: {e}")
            return IngestionResult(
                success=False,
                records_failed=len(records),
                errors=[str(e)],
                partition=partition,
            )

    def generate_presigned_url(
        self,
        key: str,
        bucket: str | None = None,
        expiration: int = 3600,
        method: str = "get_object",
    ) -> str:
        """Generate presigned URL for S3 object.

        Args:
            key: S3 object key.
            bucket: S3 bucket name (defaults to images bucket).
            expiration: URL expiration in seconds.
            method: HTTP method ('get_object' or 'put_object').

        Returns:
            Presigned URL string.
        """
        bucket = bucket or self.images_bucket
        return self.client.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration,
        )

    def generate_upload_url(
        self,
        metadata: ImageMetadata,
        expiration: int = 3600,
    ) -> tuple[str, str]:
        """Generate presigned URL for image upload.

        Args:
            metadata: Image metadata.
            expiration: URL expiration in seconds.

        Returns:
            Tuple of (presigned_url, s3_key).
        """
        partition = metadata.partition
        s3_key = f"images/{partition.path}/{metadata.study_id}_{metadata.image_id}.dcm"

        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.images_bucket,
                "Key": s3_key,
                "ContentType": "application/dicom",
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": self.kms_key_id,
            },
            ExpiresIn=expiration,
        )
        return url, s3_key

    def list_objects(
        self,
        prefix: str,
        bucket: str | None = None,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """List objects in S3 bucket with prefix.

        Args:
            prefix: S3 key prefix.
            bucket: S3 bucket name.
            max_keys: Maximum number of keys to return.

        Returns:
            List of object metadata dictionaries.
        """
        bucket = bucket or self.metadata_bucket
        objects: list[dict[str, Any]] = []
        paginator = self.client.get_paginator("list_objects_v2")

        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
            PaginationConfig={"MaxItems": max_keys},
        ):
            for obj in page.get("Contents", []):
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )

        return objects

    def get_object(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bytes:
        """Get object from S3.

        Args:
            key: S3 object key.
            bucket: S3 bucket name.

        Returns:
            Object body as bytes.

        Raises:
            StorageError: If object retrieval fails.
        """
        bucket = bucket or self.images_bucket
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            raise StorageError(
                f"Failed to get object: {e}",
                bucket=bucket,
                key=key,
                operation="get_object",
            ) from e

    def read_json_lines(
        self,
        key: str,
        bucket: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read NDJSON file from S3.

        Args:
            key: S3 object key.
            bucket: S3 bucket name.

        Returns:
            List of parsed JSON objects.
        """
        bucket = bucket or self.metadata_bucket
        content = self.get_object(key, bucket).decode("utf-8")
        return [json.loads(line) for line in content.strip().split("\n") if line]

    def get_partition_sizes(
        self,
        prefix: str,
        bucket: str | None = None,
    ) -> dict[str, int]:
        """Get total size per partition.

        Args:
            prefix: S3 key prefix.
            bucket: S3 bucket name.

        Returns:
            Dictionary mapping partition paths to total sizes.
        """
        bucket = bucket or self.metadata_bucket
        partition_sizes: dict[str, int] = {}

        for obj in self.list_objects(prefix, bucket, max_keys=10000):
            key = obj["key"]
            size = obj["size"]

            # Extract partition path (e.g., year=2024/month=01/day=15)
            parts = key.split("/")
            partition_parts = [p for p in parts if "=" in p]
            partition_path = "/".join(partition_parts)

            if partition_path:
                partition_sizes[partition_path] = (
                    partition_sizes.get(partition_path, 0) + size
                )

        return partition_sizes

    def get_s3_location(self, prefix: str, bucket: str | None = None) -> S3Location:
        """Get S3Location object for a prefix.

        Args:
            prefix: S3 key prefix.
            bucket: S3 bucket name.

        Returns:
            S3Location object.
        """
        bucket = bucket or self.metadata_bucket
        return S3Location(
            bucket=bucket,
            prefix=prefix,
            region=settings.aws_region,
        )

    def delete_object(self, key: str, bucket: str | None = None) -> None:
        """Delete object from S3.

        Args:
            key: S3 object key.
            bucket: S3 bucket name.

        Raises:
            StorageError: If deletion fails.
        """
        bucket = bucket or self.images_bucket
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info("Object deleted", extra={"bucket": bucket, "key": key})
        except ClientError as e:
            raise StorageError(
                f"Failed to delete object: {e}",
                bucket=bucket,
                key=key,
                operation="delete_object",
            ) from e
