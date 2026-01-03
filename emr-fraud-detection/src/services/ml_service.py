"""ML Service for model management.

This module provides utilities for loading and managing ML models
used in fraud detection.
"""

import json
from typing import Any

from aws_lambda_powertools import Logger

from ..common import ModelMetrics, ModelNotFoundError, settings
from ..common.clients import get_s3_client

logger = Logger()


class MLService:
    """Service for ML model management."""

    def __init__(self, client: Any = None) -> None:
        """Initialize ML service.

        Args:
            client: boto3 S3 client (optional)
        """
        self.client = client or get_s3_client()
        self.models_bucket = settings.models_bucket

    def get_model_path(self, version: str | None = None) -> str:
        """Get S3 path for a model version.

        Args:
            version: Model version (default: settings.model_version)

        Returns:
            S3 path to model
        """
        version = version or settings.model_version
        return f"s3://{self.models_bucket}/models/{version}"

    def get_model_metadata(self, version: str | None = None) -> dict[str, Any]:
        """Get model metadata.

        Args:
            version: Model version

        Returns:
            Model metadata dictionary

        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        version = version or settings.model_version
        key = f"models/{version}/metadata.json"

        try:
            response = self.client.get_object(
                Bucket=self.models_bucket,
                Key=key,
            )
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)

        except self.client.exceptions.NoSuchKey:
            raise ModelNotFoundError(version, f"s3://{self.models_bucket}/{key}")

        except Exception as e:
            logger.error("Failed to get model metadata", version=version, error=str(e))
            raise

    def get_model_metrics(self, version: str | None = None) -> ModelMetrics:
        """Get model performance metrics.

        Args:
            version: Model version

        Returns:
            ModelMetrics object

        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        version = version or settings.model_version
        key = f"models/{version}/metrics.json"

        try:
            response = self.client.get_object(
                Bucket=self.models_bucket,
                Key=key,
            )
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)
            return ModelMetrics(**data)

        except self.client.exceptions.NoSuchKey:
            raise ModelNotFoundError(version, f"s3://{self.models_bucket}/{key}")

        except Exception as e:
            logger.error("Failed to get model metrics", version=version, error=str(e))
            raise

    def save_model_metrics(self, metrics: ModelMetrics) -> None:
        """Save model performance metrics.

        Args:
            metrics: ModelMetrics object to save
        """
        key = f"models/{metrics.model_version}/metrics.json"

        try:
            self.client.put_object(
                Bucket=self.models_bucket,
                Key=key,
                Body=json.dumps(metrics.model_dump(mode="json"), default=str).encode("utf-8"),
                ContentType="application/json",
            )
            logger.info("Model metrics saved", version=metrics.model_version)

        except Exception as e:
            logger.error("Failed to save model metrics", version=metrics.model_version, error=str(e))
            raise

    def list_model_versions(self) -> list[str]:
        """List available model versions.

        Returns:
            List of version strings
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.models_bucket,
                Prefix="models/",
                Delimiter="/",
            )

            versions = []
            for prefix in response.get("CommonPrefixes", []):
                version = prefix["Prefix"].rstrip("/").split("/")[-1]
                if version.startswith("v"):
                    versions.append(version)

            return sorted(versions, reverse=True)

        except Exception as e:
            logger.error("Failed to list model versions", error=str(e))
            return []

    def model_exists(self, version: str | None = None) -> bool:
        """Check if a model version exists.

        Args:
            version: Model version

        Returns:
            True if model exists
        """
        version = version or settings.model_version
        key = f"models/{version}/model.tar.gz"

        try:
            self.client.head_object(Bucket=self.models_bucket, Key=key)
            return True

        except self.client.exceptions.ClientError:
            # Try alternative model format
            alt_key = f"models/{version}/model"
            try:
                response = self.client.list_objects_v2(
                    Bucket=self.models_bucket,
                    Prefix=alt_key,
                    MaxKeys=1,
                )
                return len(response.get("Contents", [])) > 0

            except Exception:
                return False

    def get_latest_version(self) -> str:
        """Get the latest model version.

        Returns:
            Latest version string

        Raises:
            ModelNotFoundError: If no models exist
        """
        versions = self.list_model_versions()
        if not versions:
            raise ModelNotFoundError("latest", "No models found")

        return versions[0]

    def get_feature_names(self, version: str | None = None) -> list[str]:
        """Get feature names used by the model.

        Args:
            version: Model version

        Returns:
            List of feature names
        """
        metadata = self.get_model_metadata(version)
        return metadata.get("feature_names", [])

    def get_thresholds(self, version: str | None = None) -> dict[str, float]:
        """Get classification thresholds for a model.

        Args:
            version: Model version

        Returns:
            Dictionary with fraud_threshold and suspicious_threshold
        """
        try:
            metadata = self.get_model_metadata(version)
            return {
                "fraud_threshold": metadata.get("fraud_threshold", settings.fraud_threshold),
                "suspicious_threshold": metadata.get("suspicious_threshold", settings.suspicious_threshold),
            }

        except ModelNotFoundError:
            return {
                "fraud_threshold": settings.fraud_threshold,
                "suspicious_threshold": settings.suspicious_threshold,
            }
