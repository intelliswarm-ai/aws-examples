"""Batch Scoring Spark Job.

This job scores transactions in batch mode using the trained
fraud detection model. Results are written to S3 and DynamoDB.

Usage:
    spark-submit \
        --master yarn \
        --deploy-mode cluster \
        batch_scoring.py \
        --data-bucket my-data-bucket \
        --models-bucket my-models-bucket \
        --model-version v1.0 \
        --date 2024-01-15
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal

import boto3
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

sys.path.insert(0, "/opt/spark/jobs")

from utils.feature_utils import get_feature_names
from utils.spark_utils import configure_logging, get_spark_session

logger = logging.getLogger(__name__)

# Thresholds
FRAUD_THRESHOLD = 0.7
SUSPICIOUS_THRESHOLD = 0.4


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Batch Scoring Job")
    parser.add_argument(
        "--data-bucket",
        required=True,
        help="S3 bucket for feature data",
    )
    parser.add_argument(
        "--models-bucket",
        required=True,
        help="S3 bucket for model artifacts",
    )
    parser.add_argument(
        "--model-version",
        required=True,
        help="Model version to use",
    )
    parser.add_argument(
        "--date",
        required=False,
        help="Processing date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--fraud-threshold",
        type=float,
        default=FRAUD_THRESHOLD,
        help="Threshold for fraud classification",
    )
    parser.add_argument(
        "--suspicious-threshold",
        type=float,
        default=SUSPICIOUS_THRESHOLD,
        help="Threshold for suspicious classification",
    )
    parser.add_argument(
        "--alerts-table",
        default="fraud-alerts",
        help="DynamoDB table for alerts",
    )
    parser.add_argument(
        "--predictions-table",
        default="fraud-predictions",
        help="DynamoDB table for predictions",
    )
    return parser.parse_args()


def load_features(
    spark: SparkSession,
    data_bucket: str,
    date: str,
) -> "DataFrame":
    """Load feature vectors for scoring.

    Args:
        spark: SparkSession
        data_bucket: Data lake bucket
        date: Processing date

    Returns:
        DataFrame with features
    """
    features_path = f"s3a://{data_bucket}/features/date={date}"

    try:
        df = spark.read.parquet(features_path)
        count = df.count()
        logger.info("Loaded %d feature vectors from %s", count, features_path)
        return df

    except Exception as e:
        logger.error("Failed to load features: %s", str(e))
        raise


def load_model(
    models_bucket: str,
    model_version: str,
) -> PipelineModel:
    """Load trained model from S3.

    Args:
        models_bucket: Models bucket
        model_version: Model version

    Returns:
        Loaded PipelineModel
    """
    model_path = f"s3a://{models_bucket}/models/{model_version}/model"

    try:
        model = PipelineModel.load(model_path)
        logger.info("Model loaded from %s", model_path)
        return model

    except Exception as e:
        logger.error("Failed to load model: %s", str(e))
        raise


def score_transactions(
    model: PipelineModel,
    features_df: "DataFrame",
    fraud_threshold: float,
    suspicious_threshold: float,
) -> "DataFrame":
    """Score transactions using the model.

    Args:
        model: Trained model
        features_df: Feature vectors
        fraud_threshold: Fraud classification threshold
        suspicious_threshold: Suspicious classification threshold

    Returns:
        DataFrame with predictions
    """
    # Fill nulls in feature columns
    feature_columns = get_feature_names()
    features_df = features_df.na.fill(0.0, feature_columns)

    # Make predictions
    predictions = model.transform(features_df)

    # Extract fraud probability from probability vector
    # Probability vector is [prob_class_0, prob_class_1]
    extract_fraud_prob = F.udf(lambda v: float(v[1]) if v is not None else 0.0, DoubleType())

    predictions = predictions.withColumn(
        "fraud_score",
        extract_fraud_prob(F.col("rf_probability")),
    )

    # Classify based on thresholds
    predictions = predictions.withColumn(
        "fraud_status",
        F.when(F.col("fraud_score") >= fraud_threshold, "FRAUDULENT")
        .when(F.col("fraud_score") >= suspicious_threshold, "SUSPICIOUS")
        .otherwise("LEGITIMATE"),
    )

    # Calculate confidence (distance from threshold)
    predictions = predictions.withColumn(
        "confidence",
        F.when(
            F.col("fraud_status") == "FRAUDULENT",
            F.col("fraud_score"),
        ).when(
            F.col("fraud_status") == "LEGITIMATE",
            1.0 - F.col("fraud_score"),
        ).otherwise(
            F.abs(F.col("fraud_score") - suspicious_threshold) / (fraud_threshold - suspicious_threshold),
        ),
    )

    # Generate prediction ID
    predictions = predictions.withColumn(
        "prediction_id",
        F.concat(F.lit("pred-"), F.col("transaction_id"), F.lit("-"), F.unix_timestamp()),
    )

    # Add processed timestamp
    predictions = predictions.withColumn(
        "processed_at",
        F.current_timestamp(),
    )

    total = predictions.count()
    fraud_count = predictions.filter(F.col("fraud_status") == "FRAUDULENT").count()
    suspicious_count = predictions.filter(F.col("fraud_status") == "SUSPICIOUS").count()

    logger.info(
        "Scored %d transactions: %d fraud (%.2f%%), %d suspicious (%.2f%%)",
        total,
        fraud_count,
        fraud_count / total * 100 if total > 0 else 0,
        suspicious_count,
        suspicious_count / total * 100 if total > 0 else 0,
    )

    return predictions


def identify_risk_factors(predictions: "DataFrame") -> "DataFrame":
    """Add risk factors based on feature values.

    Args:
        predictions: Predictions DataFrame

    Returns:
        DataFrame with risk factors
    """
    # Define risk factor conditions
    risk_factors = F.array(
        F.when(F.col("amount_zscore") > 2.0, F.lit("HIGH_AMOUNT")).otherwise(F.lit(None)),
        F.when(F.col("tx_count_1h") > 5, F.lit("HIGH_VELOCITY")).otherwise(F.lit(None)),
        F.when(F.col("is_new_merchant") == 1, F.lit("NEW_MERCHANT")).otherwise(F.lit(None)),
        F.when(F.col("is_new_device") == 1, F.lit("NEW_DEVICE")).otherwise(F.lit(None)),
        F.when(F.col("is_high_risk_country") == 1, F.lit("HIGH_RISK_LOCATION")).otherwise(F.lit(None)),
        F.when(
            (F.col("distance_from_last") > 100) & (F.col("time_since_last") < 1),
            F.lit("IMPOSSIBLE_TRAVEL"),
        ).otherwise(F.lit(None)),
        F.when(F.col("is_weekend") == 1, F.lit("WEEKEND_TX")).otherwise(F.lit(None)),
        F.when(
            (F.col("hour_of_day") < 6) | (F.col("hour_of_day") > 22),
            F.lit("ODD_HOURS"),
        ).otherwise(F.lit(None)),
    )

    # Filter out nulls from array
    predictions = predictions.withColumn(
        "risk_factors",
        F.expr("filter(risk_factors_raw, x -> x is not null)"),
    ).drop("risk_factors_raw")

    # Add intermediate column first
    predictions_with_raw = predictions.withColumn("risk_factors_raw", risk_factors)
    predictions = predictions_with_raw.withColumn(
        "risk_factors",
        F.expr("filter(risk_factors_raw, x -> x is not null)"),
    ).drop("risk_factors_raw")

    return predictions


def save_predictions(
    predictions: "DataFrame",
    data_bucket: str,
    date: str,
    model_version: str,
) -> dict:
    """Save predictions to S3.

    Args:
        predictions: Predictions DataFrame
        data_bucket: Data lake bucket
        date: Processing date
        model_version: Model version

    Returns:
        Statistics dictionary
    """
    # Select output columns
    output_columns = [
        "prediction_id",
        "transaction_id",
        "account_id",
        "fraud_score",
        "fraud_status",
        "confidence",
        "risk_factors",
        "processed_at",
    ]

    output_df = predictions.select(output_columns)

    # Add model version
    output_df = output_df.withColumn("model_version", F.lit(model_version))

    # Write to S3
    output_path = f"s3a://{data_bucket}/predictions/date={date}"
    output_df.coalesce(10).write.mode("overwrite").parquet(output_path)

    logger.info("Predictions saved to %s", output_path)

    # Calculate statistics
    stats = {
        "total_processed": predictions.count(),
        "fraud_count": predictions.filter(F.col("fraud_status") == "FRAUDULENT").count(),
        "suspicious_count": predictions.filter(F.col("fraud_status") == "SUSPICIOUS").count(),
        "legitimate_count": predictions.filter(F.col("fraud_status") == "LEGITIMATE").count(),
        "output_path": output_path,
    }

    return stats


def write_alerts_to_dynamodb(
    predictions: "DataFrame",
    alerts_table: str,
    model_version: str,
) -> int:
    """Write fraud alerts to DynamoDB.

    Args:
        predictions: Predictions DataFrame (filtered to fraud/suspicious)
        alerts_table: DynamoDB table name
        model_version: Model version

    Returns:
        Number of alerts written
    """
    # Filter to only fraud and suspicious
    alerts_df = predictions.filter(F.col("fraud_status").isin(["FRAUDULENT", "SUSPICIOUS"]))

    if alerts_df.count() == 0:
        logger.info("No alerts to write")
        return 0

    # Select columns for alerts
    alert_columns = [
        "prediction_id",
        "transaction_id",
        "account_id",
        "fraud_score",
        "fraud_status",
        "risk_factors",
        "amount",
        "processed_at",
    ]

    # Add alert-specific fields
    alerts_df = alerts_df.select(alert_columns).withColumn(
        "alert_id",
        F.concat(F.lit("alert-"), F.col("transaction_id")),
    ).withColumn(
        "severity",
        F.when(F.col("fraud_status") == "FRAUDULENT", "HIGH").otherwise("MEDIUM"),
    ).withColumn(
        "alert_type",
        F.lit("FRAUD_DETECTED"),
    ).withColumn(
        "acknowledged",
        F.lit(False),
    ).withColumn(
        "model_version",
        F.lit(model_version),
    )

    # Write to DynamoDB using foreachPartition
    def write_partition(partition):
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(alerts_table)

        with table.batch_writer() as batch:
            for row in partition:
                item = {
                    "alert_id": row.alert_id,
                    "transaction_id": row.transaction_id,
                    "account_id": row.account_id,
                    "fraud_score": Decimal(str(row.fraud_score)),
                    "fraud_status": row.fraud_status,
                    "severity": row.severity,
                    "alert_type": row.alert_type,
                    "risk_factors": row.risk_factors if row.risk_factors else [],
                    "amount": Decimal(str(row.amount)) if row.amount else Decimal("0"),
                    "created_at": row.processed_at.isoformat() if row.processed_at else datetime.utcnow().isoformat(),
                    "acknowledged": row.acknowledged,
                    "model_version": row.model_version,
                }
                batch.put_item(Item=item)

    alerts_df.foreachPartition(write_partition)

    alert_count = alerts_df.count()
    logger.info("Written %d alerts to DynamoDB table %s", alert_count, alerts_table)

    return alert_count


def save_job_metadata(
    spark: SparkSession,
    data_bucket: str,
    date: str,
    model_version: str,
    stats: dict,
) -> None:
    """Save job metadata to S3.

    Args:
        spark: SparkSession
        data_bucket: Data lake bucket
        date: Processing date
        model_version: Model version
        stats: Job statistics
    """
    metadata = {
        "job_name": "batch_scoring",
        "execution_date": date,
        "model_version": model_version,
        "completed_at": datetime.utcnow().isoformat(),
        **stats,
    }

    metadata_path = f"s3a://{data_bucket}/metadata/batch_scoring/date={date}/metadata.json"
    metadata_df = spark.createDataFrame([{"metadata": json.dumps(metadata)}])
    metadata_df.coalesce(1).write.mode("overwrite").text(metadata_path)

    logger.info("Job metadata saved to %s", metadata_path)


def main() -> int:
    """Main entry point."""
    configure_logging()
    args = parse_args()

    processing_date = args.date or datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(
        "Starting Batch Scoring Job - Date: %s, Model: %s",
        processing_date,
        args.model_version,
    )

    try:
        # Initialize Spark
        spark = get_spark_session(
            app_name=f"BatchScoring-{processing_date}",
            config={
                "spark.sql.shuffle.partitions": "100",
            },
        )

        # Load features
        features_df = load_features(
            spark=spark,
            data_bucket=args.data_bucket,
            date=processing_date,
        )

        if features_df.count() == 0:
            logger.warning("No features to score")
            return 0

        # Load model
        model = load_model(
            models_bucket=args.models_bucket,
            model_version=args.model_version,
        )

        # Score transactions
        predictions = score_transactions(
            model=model,
            features_df=features_df,
            fraud_threshold=args.fraud_threshold,
            suspicious_threshold=args.suspicious_threshold,
        )

        # Add risk factors
        predictions = identify_risk_factors(predictions)

        # Save predictions
        stats = save_predictions(
            predictions=predictions,
            data_bucket=args.data_bucket,
            date=processing_date,
            model_version=args.model_version,
        )

        # Write alerts to DynamoDB
        alert_count = write_alerts_to_dynamodb(
            predictions=predictions,
            alerts_table=args.alerts_table,
            model_version=args.model_version,
        )
        stats["alerts_created"] = alert_count

        # Save metadata
        save_job_metadata(
            spark=spark,
            data_bucket=args.data_bucket,
            date=processing_date,
            model_version=args.model_version,
            stats=stats,
        )

        logger.info("Batch Scoring Job completed successfully")
        logger.info("Stats: %s", json.dumps(stats))

        return 0

    except Exception as e:
        logger.error("Batch Scoring Job failed: %s", str(e), exc_info=True)
        return 1

    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
