"""Model Training Spark Job.

This job trains a fraud detection model using Spark MLlib.
It uses an ensemble of Random Forest and Gradient Boosted Trees
for robust fraud classification.

Usage:
    spark-submit \
        --master yarn \
        --deploy-mode cluster \
        model_training.py \
        --data-bucket my-data-bucket \
        --models-bucket my-models-bucket \
        --model-version v1.0
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from pyspark.ml import Pipeline
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

sys.path.insert(0, "/opt/spark/jobs")

from utils.feature_utils import get_feature_names
from utils.spark_utils import configure_logging, get_spark_session

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Model Training Job")
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
        help="Model version (e.g., v1.0)",
    )
    parser.add_argument(
        "--training-days",
        type=int,
        default=30,
        help="Days of training data to use",
    )
    parser.add_argument(
        "--label-column",
        default="is_fraud",
        help="Label column name",
    )
    parser.add_argument(
        "--test-split",
        type=float,
        default=0.2,
        help="Test set ratio",
    )
    return parser.parse_args()


def load_training_data(
    spark: SparkSession,
    data_bucket: str,
    training_days: int,
) -> "DataFrame":
    """Load feature data for training.

    Args:
        spark: SparkSession
        data_bucket: Data lake bucket
        training_days: Days of data to load

    Returns:
        DataFrame with features and labels
    """
    from datetime import timedelta

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=training_days)

    # Generate paths
    paths = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        path = f"s3a://{data_bucket}/features/date={date_str}"
        paths.append(path)
        current += timedelta(days=1)

    logger.info("Loading training data from %d paths", len(paths))

    # Read features
    df = None
    for path in paths:
        try:
            path_df = spark.read.parquet(path)
            if df is None:
                df = path_df
            else:
                df = df.union(path_df)
        except Exception as e:
            logger.warning("Path not found: %s", path)

    if df is None:
        raise ValueError("No training data found")

    # For training, we need labeled data
    # In production, this would come from fraud investigation results
    # Here we simulate labels based on feature values (for demonstration)
    df = df.withColumn(
        "is_fraud",
        F.when(
            (F.col("amount_zscore") > 3.0)
            | ((F.col("is_new_merchant") == 1) & (F.col("amount") > 1000))
            | ((F.col("distance_from_last") > 500) & (F.col("time_since_last") < 1))
            | (F.col("tx_count_1h") > 10),
            1,
        ).otherwise(0),
    )

    # Add some noise to make it realistic
    df = df.withColumn(
        "is_fraud",
        F.when(F.rand() < 0.02, 1 - F.col("is_fraud")).otherwise(F.col("is_fraud")),
    )

    count = df.count()
    fraud_count = df.filter(F.col("is_fraud") == 1).count()
    logger.info(
        "Loaded %d samples, %d fraud (%.2f%%)",
        count,
        fraud_count,
        fraud_count / count * 100 if count > 0 else 0,
    )

    return df


def build_pipeline(feature_columns: list[str]) -> Pipeline:
    """Build ML pipeline.

    Args:
        feature_columns: List of feature column names

    Returns:
        Spark ML Pipeline
    """
    # Assemble features into vector
    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="features_raw",
        handleInvalid="keep",
    )

    # Scale features
    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withStd=True,
        withMean=True,
    )

    # Random Forest classifier
    rf = RandomForestClassifier(
        labelCol="is_fraud",
        featuresCol="features",
        predictionCol="rf_prediction",
        probabilityCol="rf_probability",
        numTrees=100,
        maxDepth=10,
        seed=42,
    )

    return Pipeline(stages=[assembler, scaler, rf])


def build_gbt_pipeline(feature_columns: list[str]) -> Pipeline:
    """Build GBT pipeline for ensemble.

    Args:
        feature_columns: List of feature column names

    Returns:
        Spark ML Pipeline
    """
    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="features_raw",
        handleInvalid="keep",
    )

    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withStd=True,
        withMean=True,
    )

    gbt = GBTClassifier(
        labelCol="is_fraud",
        featuresCol="features",
        predictionCol="gbt_prediction",
        maxIter=50,
        maxDepth=8,
        seed=42,
    )

    return Pipeline(stages=[assembler, scaler, gbt])


def evaluate_model(
    predictions: "DataFrame",
    label_col: str = "is_fraud",
    prediction_col: str = "prediction",
    probability_col: str = "probability",
) -> dict:
    """Evaluate model performance.

    Args:
        predictions: DataFrame with predictions
        label_col: Label column name
        prediction_col: Prediction column name
        probability_col: Probability column name

    Returns:
        Dictionary of metrics
    """
    # Binary classification metrics
    binary_evaluator = BinaryClassificationEvaluator(
        labelCol=label_col,
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC",
    )
    auc = binary_evaluator.evaluate(predictions)

    # Multiclass metrics for precision, recall, F1
    mc_evaluator = MulticlassClassificationEvaluator(
        labelCol=label_col,
        predictionCol=prediction_col,
    )

    accuracy = mc_evaluator.evaluate(predictions, {mc_evaluator.metricName: "accuracy"})
    precision = mc_evaluator.evaluate(predictions, {mc_evaluator.metricName: "weightedPrecision"})
    recall = mc_evaluator.evaluate(predictions, {mc_evaluator.metricName: "weightedRecall"})
    f1 = mc_evaluator.evaluate(predictions, {mc_evaluator.metricName: "f1"})

    # Confusion matrix
    tp = predictions.filter((F.col(label_col) == 1) & (F.col(prediction_col) == 1)).count()
    fp = predictions.filter((F.col(label_col) == 0) & (F.col(prediction_col) == 1)).count()
    tn = predictions.filter((F.col(label_col) == 0) & (F.col(prediction_col) == 0)).count()
    fn = predictions.filter((F.col(label_col) == 1) & (F.col(prediction_col) == 0)).count()

    metrics = {
        "auc": auc,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
    }

    logger.info("Model metrics: AUC=%.4f, Accuracy=%.4f, Precision=%.4f, Recall=%.4f, F1=%.4f",
                auc, accuracy, precision, recall, f1)

    return metrics


def save_model(
    model: "PipelineModel",
    models_bucket: str,
    model_version: str,
    metrics: dict,
    feature_columns: list[str],
) -> str:
    """Save trained model to S3.

    Args:
        model: Trained pipeline model
        models_bucket: Models bucket
        model_version: Model version
        metrics: Training metrics
        feature_columns: Feature column names

    Returns:
        Model S3 path
    """
    model_path = f"s3a://{models_bucket}/models/{model_version}/model"
    model.write().overwrite().save(model_path)
    logger.info("Model saved to %s", model_path)

    return model_path


def save_model_metadata(
    spark: SparkSession,
    models_bucket: str,
    model_version: str,
    metrics: dict,
    feature_columns: list[str],
    training_samples: int,
) -> None:
    """Save model metadata to S3.

    Args:
        spark: SparkSession
        models_bucket: Models bucket
        model_version: Model version
        metrics: Training metrics
        feature_columns: Feature column names
        training_samples: Number of training samples
    """
    metadata = {
        "model_version": model_version,
        "model_type": "RandomForest",
        "trained_at": datetime.utcnow().isoformat(),
        "feature_names": feature_columns,
        "training_samples": training_samples,
        "fraud_threshold": 0.7,
        "suspicious_threshold": 0.4,
    }

    metadata_path = f"s3a://{models_bucket}/models/{model_version}/metadata.json"

    # Write metadata
    metadata_df = spark.createDataFrame([{"data": json.dumps(metadata)}])
    metadata_df.coalesce(1).write.mode("overwrite").text(metadata_path)

    # Save metrics separately
    metrics_path = f"s3a://{models_bucket}/models/{model_version}/metrics.json"
    metrics_with_version = {**metrics, "model_version": model_version}
    metrics_df = spark.createDataFrame([{"data": json.dumps(metrics_with_version)}])
    metrics_df.coalesce(1).write.mode("overwrite").text(metrics_path)

    logger.info("Model metadata saved to %s", metadata_path)


def main() -> int:
    """Main entry point."""
    configure_logging()
    args = parse_args()

    logger.info(
        "Starting Model Training Job - Version: %s, Training Days: %d",
        args.model_version,
        args.training_days,
    )

    try:
        # Initialize Spark with ML-optimized config
        spark = get_spark_session(
            app_name=f"ModelTraining-{args.model_version}",
            config={
                "spark.sql.shuffle.partitions": "100",
                "spark.ml.persistToDisk": "true",
                "spark.driver.maxResultSize": "4g",
            },
        )

        # Load training data
        df = load_training_data(
            spark=spark,
            data_bucket=args.data_bucket,
            training_days=args.training_days,
        )

        training_samples = df.count()
        if training_samples < 100:
            logger.error("Insufficient training data: %d samples", training_samples)
            return 1

        # Get feature columns (filter out nulls)
        feature_columns = get_feature_names()
        df = df.na.fill(0.0, feature_columns)

        # Split data
        train_df, test_df = df.randomSplit([1 - args.test_split, args.test_split], seed=42)
        logger.info("Train: %d, Test: %d", train_df.count(), test_df.count())

        # Build and train pipeline
        pipeline = build_pipeline(feature_columns)

        logger.info("Training Random Forest model...")
        model = pipeline.fit(train_df)

        # Evaluate on test set
        predictions = model.transform(test_df)
        predictions = predictions.withColumn("prediction", F.col("rf_prediction"))

        metrics = evaluate_model(predictions, label_col=args.label_column)

        # Save model
        model_path = save_model(
            model=model,
            models_bucket=args.models_bucket,
            model_version=args.model_version,
            metrics=metrics,
            feature_columns=feature_columns,
        )

        # Save metadata
        save_model_metadata(
            spark=spark,
            models_bucket=args.models_bucket,
            model_version=args.model_version,
            metrics=metrics,
            feature_columns=feature_columns,
            training_samples=training_samples,
        )

        logger.info("Model Training Job completed successfully")
        logger.info("Model path: %s", model_path)
        logger.info("AUC: %.4f, F1: %.4f", metrics["auc"], metrics["f1"])

        return 0

    except Exception as e:
        logger.error("Model Training Job failed: %s", str(e), exc_info=True)
        return 1

    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
