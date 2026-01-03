"""AWS service client factories for EMR Spark Fraud Detection Pipeline.

This module provides centralized creation of boto3 clients with optimized
configurations for performance and reliability.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from .config import settings


def _get_base_config() -> Config:
    """Get base boto3 configuration with optimized settings."""
    return Config(
        region_name=settings.aws_region,
        retries={
            "max_attempts": 5,
            "mode": "adaptive",
        },
        connect_timeout=5,
        read_timeout=60,
        max_pool_connections=25,
    )


def _get_high_throughput_config() -> Config:
    """Get boto3 configuration optimized for high-throughput operations."""
    return Config(
        region_name=settings.aws_region,
        retries={
            "max_attempts": 10,
            "mode": "adaptive",
        },
        connect_timeout=5,
        read_timeout=30,
        max_pool_connections=50,
    )


def _get_long_running_config() -> Config:
    """Get boto3 configuration for long-running operations like EMR."""
    return Config(
        region_name=settings.aws_region,
        retries={
            "max_attempts": 3,
            "mode": "standard",
        },
        connect_timeout=10,
        read_timeout=300,
        max_pool_connections=10,
    )


@lru_cache
def get_kinesis_client() -> Any:
    """Get Kinesis client optimized for high-throughput streaming.

    Returns:
        boto3 Kinesis client with adaptive retry and connection pooling.
    """
    return boto3.client("kinesis", config=_get_high_throughput_config())


@lru_cache
def get_s3_client() -> Any:
    """Get S3 client for data lake operations.

    Returns:
        boto3 S3 client with standard configuration.
    """
    return boto3.client("s3", config=_get_base_config())


@lru_cache
def get_s3_resource() -> Any:
    """Get S3 resource for high-level operations.

    Returns:
        boto3 S3 resource.
    """
    return boto3.resource("s3", config=_get_base_config())


@lru_cache
def get_dynamodb_client() -> Any:
    """Get DynamoDB client for table operations.

    Returns:
        boto3 DynamoDB client with adaptive retry.
    """
    return boto3.client("dynamodb", config=_get_high_throughput_config())


@lru_cache
def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource for high-level table operations.

    Returns:
        boto3 DynamoDB resource.
    """
    return boto3.resource("dynamodb", config=_get_high_throughput_config())


@lru_cache
def get_emr_client() -> Any:
    """Get EMR client for cluster management.

    Returns:
        boto3 EMR client with long-running operation configuration.
    """
    return boto3.client("emr", config=_get_long_running_config())


@lru_cache
def get_sns_client() -> Any:
    """Get SNS client for notifications.

    Returns:
        boto3 SNS client with standard configuration.
    """
    return boto3.client("sns", config=_get_base_config())


@lru_cache
def get_sfn_client() -> Any:
    """Get Step Functions client for workflow orchestration.

    Returns:
        boto3 Step Functions client with long-running configuration.
    """
    return boto3.client("stepfunctions", config=_get_long_running_config())


@lru_cache
def get_cloudwatch_client() -> Any:
    """Get CloudWatch client for metrics and logging.

    Returns:
        boto3 CloudWatch client with standard configuration.
    """
    return boto3.client("cloudwatch", config=_get_base_config())


@lru_cache
def get_logs_client() -> Any:
    """Get CloudWatch Logs client.

    Returns:
        boto3 CloudWatch Logs client.
    """
    return boto3.client("logs", config=_get_base_config())


@lru_cache
def get_sts_client() -> Any:
    """Get STS client for identity operations.

    Returns:
        boto3 STS client.
    """
    return boto3.client("sts", config=_get_base_config())


@lru_cache
def get_secretsmanager_client() -> Any:
    """Get Secrets Manager client.

    Returns:
        boto3 Secrets Manager client.
    """
    return boto3.client("secretsmanager", config=_get_base_config())


def get_account_id() -> str:
    """Get the current AWS account ID.

    Returns:
        The AWS account ID string.
    """
    if settings.aws_account_id:
        return settings.aws_account_id
    sts = get_sts_client()
    return sts.get_caller_identity()["Account"]


def clear_client_cache() -> None:
    """Clear all cached clients.

    Useful for testing or when credentials change.
    """
    get_kinesis_client.cache_clear()
    get_s3_client.cache_clear()
    get_s3_resource.cache_clear()
    get_dynamodb_client.cache_clear()
    get_dynamodb_resource.cache_clear()
    get_emr_client.cache_clear()
    get_sns_client.cache_clear()
    get_sfn_client.cache_clear()
    get_cloudwatch_client.cache_clear()
    get_logs_client.cache_clear()
    get_sts_client.cache_clear()
    get_secretsmanager_client.cache_clear()


class AWSClientFactory:
    """Factory class for creating AWS clients with custom configurations.

    Use this class when you need clients with non-default configurations,
    such as cross-region operations or custom timeouts.
    """

    def __init__(
        self,
        region_name: str | None = None,
        max_retries: int = 5,
        connect_timeout: int = 5,
        read_timeout: int = 60,
    ) -> None:
        """Initialize the client factory.

        Args:
            region_name: AWS region (defaults to settings.aws_region)
            max_retries: Maximum retry attempts
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
        """
        self.config = Config(
            region_name=region_name or settings.aws_region,
            retries={
                "max_attempts": max_retries,
                "mode": "adaptive",
            },
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    def get_client(self, service_name: str) -> Any:
        """Get a boto3 client for the specified service.

        Args:
            service_name: AWS service name (e.g., 's3', 'dynamodb')

        Returns:
            boto3 client for the service.
        """
        return boto3.client(service_name, config=self.config)

    def get_resource(self, service_name: str) -> Any:
        """Get a boto3 resource for the specified service.

        Args:
            service_name: AWS service name (e.g., 's3', 'dynamodb')

        Returns:
            boto3 resource for the service.
        """
        return boto3.resource(service_name, config=self.config)
