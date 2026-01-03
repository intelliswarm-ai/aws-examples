"""S3 Service for data lake operations.

This module provides a wrapper around S3 operations for reading and
writing data to the data lake.
"""

import json
from typing import Any

from aws_lambda_powertools import Logger

from ..common import S3Error
from ..common.clients import get_s3_client

logger = Logger()


class S3Service:
    """Service for S3 data lake operations."""

    def __init__(self, bucket: str, client: Any = None) -> None:
        """Initialize S3 service.

        Args:
            bucket: S3 bucket name
            client: boto3 S3 client (optional)
        """
        self.bucket = bucket
        self.client = client or get_s3_client()

    def put_json(self, key: str, data: dict[str, Any]) -> None:
        """Store JSON data to S3.

        Args:
            key: S3 object key
            data: Data to store as JSON

        Raises:
            S3Error: If put fails
        """
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            logger.debug("Object stored", bucket=self.bucket, key=key)

        except Exception as e:
            raise S3Error(
                message=f"Failed to put object: {e}",
                bucket=self.bucket,
                key=key,
            )

    def get_json(self, key: str) -> dict[str, Any]:
        """Get JSON data from S3.

        Args:
            key: S3 object key

        Returns:
            Parsed JSON data

        Raises:
            S3Error: If get fails
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)

        except self.client.exceptions.NoSuchKey:
            raise S3Error(
                message=f"Object not found: {key}",
                bucket=self.bucket,
                key=key,
            )

        except Exception as e:
            raise S3Error(
                message=f"Failed to get object: {e}",
                bucket=self.bucket,
                key=key,
            )

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Store binary data to S3.

        Args:
            key: S3 object key
            data: Binary data to store
            content_type: MIME type

        Raises:
            S3Error: If put fails
        """
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            logger.debug("Object stored", bucket=self.bucket, key=key)

        except Exception as e:
            raise S3Error(
                message=f"Failed to put object: {e}",
                bucket=self.bucket,
                key=key,
            )

    def get_bytes(self, key: str) -> bytes:
        """Get binary data from S3.

        Args:
            key: S3 object key

        Returns:
            Binary data

        Raises:
            S3Error: If get fails
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

        except self.client.exceptions.NoSuchKey:
            raise S3Error(
                message=f"Object not found: {key}",
                bucket=self.bucket,
                key=key,
            )

        except Exception as e:
            raise S3Error(
                message=f"Failed to get object: {e}",
                bucket=self.bucket,
                key=key,
            )

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list[str]:
        """List objects with prefix.

        Args:
            prefix: Key prefix to filter
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys
        """
        try:
            keys = []
            continuation_token = None

            while True:
                params: dict[str, Any] = {
                    "Bucket": self.bucket,
                    "Prefix": prefix,
                    "MaxKeys": min(max_keys - len(keys), 1000),
                }

                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = self.client.list_objects_v2(**params)

                for obj in response.get("Contents", []):
                    keys.append(obj["Key"])

                if len(keys) >= max_keys or not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

            return keys

        except Exception as e:
            logger.error("Failed to list objects", bucket=self.bucket, prefix=prefix, error=str(e))
            return []

    def delete_object(self, key: str) -> bool:
        """Delete an object.

        Args:
            key: S3 object key

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.debug("Object deleted", bucket=self.bucket, key=key)
            return True

        except Exception as e:
            logger.error("Failed to delete object", bucket=self.bucket, key=key, error=str(e))
            return False

    def copy_object(self, source_key: str, dest_key: str, dest_bucket: str | None = None) -> bool:
        """Copy an object.

        Args:
            source_key: Source object key
            dest_key: Destination object key
            dest_bucket: Destination bucket (default: same bucket)

        Returns:
            True if copied successfully
        """
        try:
            self.client.copy_object(
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Bucket=dest_bucket or self.bucket,
                Key=dest_key,
            )
            logger.debug("Object copied", source=source_key, dest=dest_key)
            return True

        except Exception as e:
            logger.error("Failed to copy object", source=source_key, dest=dest_key, error=str(e))
            return False

    def object_exists(self, key: str) -> bool:
        """Check if an object exists.

        Args:
            key: S3 object key

        Returns:
            True if object exists
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True

        except self.client.exceptions.ClientError:
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for an object.

        Args:
            key: S3 object key
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
