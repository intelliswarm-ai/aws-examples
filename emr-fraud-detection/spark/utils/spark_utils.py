"""Spark session utilities.

This module provides utilities for creating and managing Spark sessions
in the EMR environment.
"""

import logging
import os
from typing import Any

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


class SparkSessionManager:
    """Manager for Spark session lifecycle."""

    _instance: SparkSession | None = None

    @classmethod
    def get_or_create(
        cls,
        app_name: str = "FraudDetection",
        config: dict[str, Any] | None = None,
    ) -> SparkSession:
        """Get or create a Spark session.

        Args:
            app_name: Application name
            config: Additional Spark configuration

        Returns:
            SparkSession instance
        """
        if cls._instance is not None:
            return cls._instance

        builder = SparkSession.builder.appName(app_name)

        # Default configurations for fraud detection workload
        default_config = {
            "spark.sql.shuffle.partitions": "200",
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
            "spark.sql.parquet.compression.codec": "snappy",
            "spark.sql.sources.partitionOverwriteMode": "dynamic",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.aws.credentials.provider": (
                "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
            ),
        }

        # Merge with provided config
        if config:
            default_config.update(config)

        for key, value in default_config.items():
            builder = builder.config(key, value)

        # Enable Hive support for table operations
        builder = builder.enableHiveSupport()

        cls._instance = builder.getOrCreate()
        logger.info("Spark session created: %s", app_name)

        return cls._instance

    @classmethod
    def stop(cls) -> None:
        """Stop the current Spark session."""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None
            logger.info("Spark session stopped")


def get_spark_session(
    app_name: str = "FraudDetection",
    config: dict[str, Any] | None = None,
) -> SparkSession:
    """Convenience function to get Spark session.

    Args:
        app_name: Application name
        config: Additional Spark configuration

    Returns:
        SparkSession instance
    """
    return SparkSessionManager.get_or_create(app_name, config)


def get_s3_path(bucket: str, prefix: str) -> str:
    """Construct S3 path.

    Args:
        bucket: S3 bucket name
        prefix: Object prefix/path

    Returns:
        Full S3 path
    """
    return f"s3a://{bucket}/{prefix.lstrip('/')}"


def get_data_lake_paths(
    data_bucket: str,
    models_bucket: str | None = None,
    date: str | None = None,
) -> dict[str, str]:
    """Get standard data lake paths.

    Args:
        data_bucket: Data lake bucket name
        models_bucket: Models bucket name (defaults to data_bucket)
        date: Date partition (YYYY-MM-DD format)

    Returns:
        Dictionary of path names to S3 paths
    """
    models_bucket = models_bucket or data_bucket
    date_partition = f"date={date}" if date else "*"

    return {
        "raw_transactions": get_s3_path(data_bucket, f"raw/transactions/{date_partition}"),
        "features": get_s3_path(data_bucket, f"features/{date_partition}"),
        "predictions": get_s3_path(data_bucket, f"predictions/{date_partition}"),
        "models": get_s3_path(models_bucket, "models"),
        "checkpoints": get_s3_path(data_bucket, "checkpoints"),
    }


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for Spark jobs.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Reduce Spark logging verbosity
    spark_logger = logging.getLogger("py4j")
    spark_logger.setLevel(logging.WARNING)


def get_env_config() -> dict[str, str]:
    """Get configuration from environment variables.

    Returns:
        Configuration dictionary
    """
    return {
        "data_bucket": os.environ.get("DATA_BUCKET", ""),
        "models_bucket": os.environ.get("MODELS_BUCKET", ""),
        "model_version": os.environ.get("MODEL_VERSION", "v1.0"),
        "fraud_threshold": os.environ.get("FRAUD_THRESHOLD", "0.7"),
        "suspicious_threshold": os.environ.get("SUSPICIOUS_THRESHOLD", "0.4"),
        "execution_date": os.environ.get("EXECUTION_DATE", ""),
        "execution_mode": os.environ.get("EXECUTION_MODE", "FULL"),
        "kinesis_stream": os.environ.get("KINESIS_STREAM_NAME", ""),
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
    }


def write_parquet(
    df: Any,
    path: str,
    mode: str = "overwrite",
    partition_by: list[str] | None = None,
) -> None:
    """Write DataFrame to Parquet with standard options.

    Args:
        df: Spark DataFrame
        path: Output S3 path
        mode: Write mode (overwrite, append)
        partition_by: Partition columns
    """
    writer = df.write.mode(mode).format("parquet")

    if partition_by:
        writer = writer.partitionBy(*partition_by)

    writer.save(path)
    logger.info("Data written to: %s", path)


def read_parquet(
    spark: SparkSession,
    path: str,
    schema: Any | None = None,
) -> Any:
    """Read Parquet data from S3.

    Args:
        spark: SparkSession
        path: S3 path (supports wildcards)
        schema: Optional schema

    Returns:
        Spark DataFrame
    """
    reader = spark.read.format("parquet")

    if schema:
        reader = reader.schema(schema)

    df = reader.load(path)
    logger.info("Data loaded from: %s (count: %d)", path, df.count())
    return df
