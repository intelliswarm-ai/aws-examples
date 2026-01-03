"""Feature Engineering Spark Job.

This job reads raw transactions from S3, computes ML features,
and writes feature vectors to the features zone in the data lake.

Usage:
    spark-submit \
        --master yarn \
        --deploy-mode cluster \
        feature_engineering.py \
        --data-bucket my-data-bucket \
        --date 2024-01-15 \
        --execution-mode FULL
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add parent directory to path for imports
sys.path.insert(0, "/opt/spark/jobs")

from utils.feature_utils import FeatureEngineer, RAW_TRANSACTION_SCHEMA, get_feature_names
from utils.spark_utils import (
    configure_logging,
    get_data_lake_paths,
    get_env_config,
    get_spark_session,
    read_parquet,
    write_parquet,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Feature Engineering Job")
    parser.add_argument(
        "--data-bucket",
        required=True,
        help="S3 bucket for data lake",
    )
    parser.add_argument(
        "--date",
        required=False,
        help="Processing date (YYYY-MM-DD), defaults to today",
    )
    parser.add_argument(
        "--execution-mode",
        choices=["FULL", "INCREMENTAL"],
        default="FULL",
        help="Execution mode",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Days of historical data for feature computation",
    )
    return parser.parse_args()


def load_raw_transactions(
    spark: SparkSession,
    data_bucket: str,
    date: str,
    lookback_days: int,
) -> "DataFrame":
    """Load raw transactions from S3.

    Args:
        spark: SparkSession
        data_bucket: Data lake bucket
        date: Processing date
        lookback_days: Days of history to load

    Returns:
        DataFrame with raw transactions
    """
    from datetime import timedelta

    # Calculate date range
    end_date = datetime.strptime(date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=lookback_days)

    # Generate paths for date range
    paths = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        path = f"s3a://{data_bucket}/raw/transactions/date={date_str}"
        paths.append(path)
        current += timedelta(days=1)

    logger.info(
        "Loading transactions from %s to %s (%d paths)",
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        len(paths),
    )

    # Read with schema
    df = spark.read.format("parquet").schema(RAW_TRANSACTION_SCHEMA)

    # Try to load data, handle missing paths
    loaded_dfs = []
    for path in paths:
        try:
            path_df = df.load(path)
            if path_df.count() > 0:
                loaded_dfs.append(path_df)
        except Exception as e:
            logger.warning("Path not found or empty: %s - %s", path, str(e))

    if not loaded_dfs:
        logger.warning("No data found in date range")
        return spark.createDataFrame([], RAW_TRANSACTION_SCHEMA)

    # Union all DataFrames
    result = loaded_dfs[0]
    for df in loaded_dfs[1:]:
        result = result.union(df)

    transaction_count = result.count()
    logger.info("Loaded %d transactions", transaction_count)

    return result


def run_feature_engineering(
    spark: SparkSession,
    raw_df: "DataFrame",
    target_date: str,
) -> "DataFrame":
    """Run feature engineering pipeline.

    Args:
        spark: SparkSession
        raw_df: Raw transactions DataFrame
        target_date: Date to generate features for

    Returns:
        DataFrame with feature vectors
    """
    logger.info("Starting feature engineering for date: %s", target_date)

    # Filter to only target date for output (but use historical for features)
    target_df = raw_df.filter(F.col("date") == target_date)

    if target_df.count() == 0:
        logger.warning("No transactions for target date: %s", target_date)
        return spark.createDataFrame([], schema=None)

    # Run feature engineering on full dataset (for historical features)
    feature_engineer = FeatureEngineer(raw_df)
    features_df = (
        feature_engineer
        .add_temporal_features()
        .add_velocity_features()
        .add_statistical_features()
        .add_distance_features()
        .add_behavioral_features()
        .add_categorical_encoding()
        .build()
    )

    # Filter to only target date
    target_features = features_df.filter(F.col("date") == target_date)

    # Fill null values for distance features
    target_features = target_features.fillna({
        "distance_from_last": 0.0,
        "time_since_last": 0.0,
    })

    feature_count = target_features.count()
    logger.info("Generated %d feature vectors", feature_count)

    return target_features


def save_features(
    features_df: "DataFrame",
    data_bucket: str,
    date: str,
) -> dict:
    """Save feature vectors to S3.

    Args:
        features_df: Feature vectors DataFrame
        data_bucket: Data lake bucket
        date: Processing date

    Returns:
        Job statistics
    """
    output_path = f"s3a://{data_bucket}/features/date={date}"

    # Write with coalesce for optimal file sizes
    features_df.coalesce(10).write.mode("overwrite").format("parquet").save(output_path)

    count = features_df.count()
    logger.info("Saved %d features to %s", count, output_path)

    return {
        "feature_count": count,
        "output_path": output_path,
    }


def save_job_metadata(
    spark: SparkSession,
    data_bucket: str,
    date: str,
    stats: dict,
) -> None:
    """Save job metadata to S3.

    Args:
        spark: SparkSession
        data_bucket: Data lake bucket
        date: Processing date
        stats: Job statistics
    """
    metadata = {
        "job_name": "feature_engineering",
        "execution_date": date,
        "completed_at": datetime.utcnow().isoformat(),
        "feature_names": get_feature_names(),
        **stats,
    }

    metadata_path = f"s3a://{data_bucket}/metadata/feature_engineering/date={date}/metadata.json"

    # Write metadata using Spark
    metadata_df = spark.createDataFrame([{"metadata": json.dumps(metadata)}])
    metadata_df.coalesce(1).write.mode("overwrite").text(metadata_path)

    logger.info("Job metadata saved to %s", metadata_path)


def main() -> int:
    """Main entry point."""
    configure_logging()
    args = parse_args()

    # Get date
    processing_date = args.date or datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(
        "Starting Feature Engineering Job - Date: %s, Mode: %s",
        processing_date,
        args.execution_mode,
    )

    try:
        # Initialize Spark
        spark = get_spark_session(
            app_name=f"FeatureEngineering-{processing_date}",
            config={
                "spark.sql.shuffle.partitions": "200",
                "spark.default.parallelism": "200",
            },
        )

        # Load raw transactions
        raw_df = load_raw_transactions(
            spark=spark,
            data_bucket=args.data_bucket,
            date=processing_date,
            lookback_days=args.lookback_days,
        )

        if raw_df.count() == 0:
            logger.warning("No transactions to process")
            return 0

        # Run feature engineering
        features_df = run_feature_engineering(
            spark=spark,
            raw_df=raw_df,
            target_date=processing_date,
        )

        # Save features
        stats = save_features(
            features_df=features_df,
            data_bucket=args.data_bucket,
            date=processing_date,
        )

        # Save metadata
        save_job_metadata(
            spark=spark,
            data_bucket=args.data_bucket,
            date=processing_date,
            stats=stats,
        )

        logger.info("Feature Engineering Job completed successfully")
        return 0

    except Exception as e:
        logger.error("Feature Engineering Job failed: %s", str(e), exc_info=True)
        return 1

    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
