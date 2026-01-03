"""Streaming Scoring Spark Job.

This job uses Spark Structured Streaming to score transactions
in near real-time from Kinesis Data Streams.

Usage:
    spark-submit \
        --master yarn \
        --deploy-mode cluster \
        --packages org.apache.spark:spark-sql-kinesis_2.12:3.4.0 \
        streaming_scoring.py \
        --kinesis-stream transactions-stream \
        --models-bucket my-models-bucket \
        --model-version v1.0 \
        --checkpoint-location s3://my-bucket/checkpoints/streaming
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

import boto3
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

sys.path.insert(0, "/opt/spark/jobs")

from utils.feature_utils import get_feature_names
from utils.spark_utils import configure_logging, get_spark_session

logger = logging.getLogger(__name__)

# Default thresholds
FRAUD_THRESHOLD = 0.7
SUSPICIOUS_THRESHOLD = 0.4

# Schema for incoming transaction events
TRANSACTION_EVENT_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("account_id", StringType(), False),
    StructField("merchant_id", StringType(), True),
    StructField("transaction_type", StringType(), False),
    StructField("channel", StringType(), False),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), False),
    StructField("timestamp", TimestampType(), False),
    StructField("location_lat", DoubleType(), True),
    StructField("location_lon", DoubleType(), True),
    StructField("location_country", StringType(), True),
    StructField("location_city", StringType(), True),
    StructField("device_id", StringType(), True),
    StructField("ip_address", StringType(), True),
])


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Streaming Scoring Job")
    parser.add_argument(
        "--kinesis-stream",
        required=True,
        help="Kinesis stream name",
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
        "--checkpoint-location",
        required=True,
        help="S3 path for streaming checkpoints",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region",
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
        "--alerts-topic-arn",
        help="SNS topic ARN for fraud alerts",
    )
    parser.add_argument(
        "--trigger-interval",
        default="30 seconds",
        help="Trigger interval for micro-batches",
    )
    return parser.parse_args()


def load_model(models_bucket: str, model_version: str) -> PipelineModel:
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


def create_kinesis_stream(
    spark: SparkSession,
    stream_name: str,
    region: str,
) -> "DataFrame":
    """Create streaming DataFrame from Kinesis.

    Args:
        spark: SparkSession
        stream_name: Kinesis stream name
        region: AWS region

    Returns:
        Streaming DataFrame
    """
    return (
        spark.readStream.format("kinesis")
        .option("streamName", stream_name)
        .option("endpointUrl", f"https://kinesis.{region}.amazonaws.com")
        .option("region", region)
        .option("startingPosition", "LATEST")
        .option("awsUseInstanceProfile", "true")
        .load()
    )


def parse_transaction_events(stream_df: "DataFrame") -> "DataFrame":
    """Parse transaction events from Kinesis records.

    Args:
        stream_df: Raw Kinesis stream DataFrame

    Returns:
        Parsed transactions DataFrame
    """
    # Kinesis data comes as binary in 'data' column
    return stream_df.select(
        F.from_json(
            F.col("data").cast("string"),
            TRANSACTION_EVENT_SCHEMA,
        ).alias("event"),
        F.col("approximateArrivalTimestamp").alias("arrival_time"),
    ).select(
        "event.*",
        "arrival_time",
    )


def add_streaming_features(df: "DataFrame") -> "DataFrame":
    """Add features for streaming scoring.

    Note: Streaming features are simplified compared to batch
    because we don't have historical aggregations available.

    Args:
        df: Parsed transactions DataFrame

    Returns:
        DataFrame with features
    """
    # Temporal features
    df = df.withColumn("hour_of_day", F.hour("timestamp"))
    df = df.withColumn("day_of_week", F.dayofweek("timestamp"))
    df = df.withColumn("is_weekend", F.when(F.dayofweek("timestamp").isin([1, 7]), 1).otherwise(0))

    # Channel encoding
    channel_mapping = F.create_map(
        F.lit("POS"), F.lit(0),
        F.lit("ATM"), F.lit(1),
        F.lit("ONLINE"), F.lit(2),
        F.lit("MOBILE"), F.lit(3),
        F.lit("BRANCH"), F.lit(4),
    )
    df = df.withColumn("channel_encoded", F.coalesce(channel_mapping[F.col("channel")], F.lit(99)))

    # Transaction type encoding
    tx_type_mapping = F.create_map(
        F.lit("PURCHASE"), F.lit(0),
        F.lit("WITHDRAWAL"), F.lit(1),
        F.lit("TRANSFER"), F.lit(2),
        F.lit("DEPOSIT"), F.lit(3),
        F.lit("PAYMENT"), F.lit(4),
        F.lit("REFUND"), F.lit(5),
    )
    df = df.withColumn("tx_type_encoded", F.coalesce(tx_type_mapping[F.col("transaction_type")], F.lit(99)))

    # High-risk country flag
    high_risk_countries = ["NG", "RU", "CN", "BR", "IN", "PH", "ID", "VN"]
    high_risk_list = F.array(*[F.lit(c) for c in high_risk_countries])
    df = df.withColumn(
        "is_high_risk_country",
        F.when(F.array_contains(high_risk_list, F.col("location_country")), 1).otherwise(0),
    )

    # Placeholder features (would be enriched from state store in production)
    df = df.withColumn("tx_count_1h", F.lit(0))
    df = df.withColumn("tx_count_24h", F.lit(0))
    df = df.withColumn("tx_amount_1h", F.lit(0.0))
    df = df.withColumn("tx_amount_24h", F.lit(0.0))
    df = df.withColumn("avg_amount_30d", F.lit(0.0))
    df = df.withColumn("std_amount_30d", F.lit(1.0))
    df = df.withColumn("amount_zscore", F.lit(0.0))
    df = df.withColumn("distance_from_last", F.lit(0.0))
    df = df.withColumn("time_since_last", F.lit(0.0))
    df = df.withColumn("is_new_merchant", F.lit(0))
    df = df.withColumn("is_new_device", F.lit(0))

    return df


def score_streaming_batch(
    batch_df: "DataFrame",
    batch_id: int,
    model: PipelineModel,
    fraud_threshold: float,
    suspicious_threshold: float,
    alerts_table: str,
    alerts_topic_arn: str | None,
    model_version: str,
) -> None:
    """Process a micro-batch of transactions.

    Args:
        batch_df: Batch DataFrame
        batch_id: Batch ID
        model: ML model
        fraud_threshold: Fraud threshold
        suspicious_threshold: Suspicious threshold
        alerts_table: DynamoDB alerts table
        alerts_topic_arn: SNS topic ARN
        model_version: Model version
    """
    if batch_df.count() == 0:
        logger.debug("Empty batch: %d", batch_id)
        return

    logger.info("Processing batch %d with %d records", batch_id, batch_df.count())

    try:
        # Add features
        features_df = add_streaming_features(batch_df)

        # Fill nulls
        feature_columns = get_feature_names()
        features_df = features_df.na.fill(0.0, feature_columns)

        # Make predictions
        predictions = model.transform(features_df)

        # Extract fraud probability
        extract_fraud_prob = F.udf(lambda v: float(v[1]) if v is not None else 0.0, DoubleType())
        predictions = predictions.withColumn("fraud_score", extract_fraud_prob(F.col("rf_probability")))

        # Classify
        predictions = predictions.withColumn(
            "fraud_status",
            F.when(F.col("fraud_score") >= fraud_threshold, "FRAUDULENT")
            .when(F.col("fraud_score") >= suspicious_threshold, "SUSPICIOUS")
            .otherwise("LEGITIMATE"),
        )

        # Filter high-risk transactions
        high_risk = predictions.filter(F.col("fraud_status").isin(["FRAUDULENT", "SUSPICIOUS"]))

        if high_risk.count() > 0:
            # Write to DynamoDB
            write_alerts_to_dynamodb(high_risk, alerts_table, model_version)

            # Send SNS notifications for fraud
            if alerts_topic_arn:
                fraud_only = high_risk.filter(F.col("fraud_status") == "FRAUDULENT")
                if fraud_only.count() > 0:
                    send_sns_alerts(fraud_only, alerts_topic_arn)

        # Log statistics
        total = predictions.count()
        fraud_count = predictions.filter(F.col("fraud_status") == "FRAUDULENT").count()
        suspicious_count = predictions.filter(F.col("fraud_status") == "SUSPICIOUS").count()

        logger.info(
            "Batch %d: %d total, %d fraud, %d suspicious",
            batch_id,
            total,
            fraud_count,
            suspicious_count,
        )

    except Exception as e:
        logger.error("Error processing batch %d: %s", batch_id, str(e), exc_info=True)


def write_alerts_to_dynamodb(df: "DataFrame", table_name: str, model_version: str) -> None:
    """Write alerts to DynamoDB.

    Args:
        df: DataFrame with fraud/suspicious transactions
        table_name: DynamoDB table name
        model_version: Model version
    """
    def write_partition(partition):
        import boto3
        from datetime import datetime
        from decimal import Decimal

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        with table.batch_writer() as batch:
            for row in partition:
                item = {
                    "alert_id": f"alert-{row.transaction_id}-{int(datetime.utcnow().timestamp())}",
                    "transaction_id": row.transaction_id,
                    "account_id": row.account_id,
                    "fraud_score": Decimal(str(round(row.fraud_score, 4))),
                    "fraud_status": row.fraud_status,
                    "severity": "HIGH" if row.fraud_status == "FRAUDULENT" else "MEDIUM",
                    "alert_type": "REALTIME_FRAUD_DETECTED",
                    "amount": Decimal(str(row.amount)) if row.amount else Decimal("0"),
                    "channel": row.channel,
                    "created_at": datetime.utcnow().isoformat(),
                    "acknowledged": False,
                    "model_version": model_version,
                    "processing_mode": "STREAMING",
                }
                batch.put_item(Item=item)

    df.foreachPartition(write_partition)
    logger.info("Written %d alerts to DynamoDB", df.count())


def send_sns_alerts(df: "DataFrame", topic_arn: str) -> None:
    """Send fraud alerts to SNS.

    Args:
        df: DataFrame with fraudulent transactions
        topic_arn: SNS topic ARN
    """
    def send_partition(partition):
        import boto3
        import json

        sns = boto3.client("sns")

        for row in partition:
            message = {
                "alert_type": "REALTIME_FRAUD_DETECTED",
                "transaction_id": row.transaction_id,
                "account_id": row.account_id,
                "amount": float(row.amount) if row.amount else 0,
                "fraud_score": round(row.fraud_score, 4),
                "channel": row.channel,
                "severity": "HIGH",
                "detected_at": datetime.utcnow().isoformat(),
            }

            sns.publish(
                TopicArn=topic_arn,
                Subject=f"FRAUD ALERT: Transaction {row.transaction_id}",
                Message=json.dumps(message),
                MessageAttributes={
                    "severity": {
                        "DataType": "String",
                        "StringValue": "HIGH",
                    },
                    "alert_type": {
                        "DataType": "String",
                        "StringValue": "REALTIME_FRAUD_DETECTED",
                    },
                },
            )

    df.foreachPartition(send_partition)
    logger.info("Sent %d SNS alerts", df.count())


def start_streaming_query(
    stream_df: "DataFrame",
    model: PipelineModel,
    checkpoint_location: str,
    trigger_interval: str,
    fraud_threshold: float,
    suspicious_threshold: float,
    alerts_table: str,
    alerts_topic_arn: str | None,
    model_version: str,
) -> StreamingQuery:
    """Start the streaming query.

    Args:
        stream_df: Streaming DataFrame
        model: ML model
        checkpoint_location: Checkpoint S3 path
        trigger_interval: Trigger interval
        fraud_threshold: Fraud threshold
        suspicious_threshold: Suspicious threshold
        alerts_table: DynamoDB alerts table
        alerts_topic_arn: SNS topic ARN
        model_version: Model version

    Returns:
        StreamingQuery
    """
    # Parse events
    parsed_df = parse_transaction_events(stream_df)

    # Create writer with foreachBatch
    def process_batch(batch_df: "DataFrame", batch_id: int) -> None:
        score_streaming_batch(
            batch_df=batch_df,
            batch_id=batch_id,
            model=model,
            fraud_threshold=fraud_threshold,
            suspicious_threshold=suspicious_threshold,
            alerts_table=alerts_table,
            alerts_topic_arn=alerts_topic_arn,
            model_version=model_version,
        )

    query = (
        parsed_df.writeStream.foreachBatch(process_batch)
        .option("checkpointLocation", checkpoint_location)
        .trigger(processingTime=trigger_interval)
        .start()
    )

    return query


def main() -> int:
    """Main entry point."""
    configure_logging()
    args = parse_args()

    logger.info(
        "Starting Streaming Scoring Job - Stream: %s, Model: %s",
        args.kinesis_stream,
        args.model_version,
    )

    try:
        # Initialize Spark with streaming config
        spark = get_spark_session(
            app_name=f"StreamingScoring-{args.model_version}",
            config={
                "spark.sql.shuffle.partitions": "20",
                "spark.streaming.stopGracefullyOnShutdown": "true",
                "spark.sql.streaming.schemaInference": "true",
            },
        )

        # Load model
        model = load_model(
            models_bucket=args.models_bucket,
            model_version=args.model_version,
        )

        # Create Kinesis stream
        stream_df = create_kinesis_stream(
            spark=spark,
            stream_name=args.kinesis_stream,
            region=args.region,
        )

        # Start streaming query
        query = start_streaming_query(
            stream_df=stream_df,
            model=model,
            checkpoint_location=args.checkpoint_location,
            trigger_interval=args.trigger_interval,
            fraud_threshold=args.fraud_threshold,
            suspicious_threshold=args.suspicious_threshold,
            alerts_table=args.alerts_table,
            alerts_topic_arn=args.alerts_topic_arn,
            model_version=args.model_version,
        )

        logger.info("Streaming query started")

        # Wait for termination
        query.awaitTermination()

        return 0

    except Exception as e:
        logger.error("Streaming Scoring Job failed: %s", str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
