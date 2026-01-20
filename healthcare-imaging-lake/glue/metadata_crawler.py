"""Glue ETL job for healthcare imaging metadata processing.

This job processes raw metadata files (NDJSON) and converts them to
optimized Parquet format with proper partitioning for efficient queries.

Usage:
    glue job run --job-name healthcare-imaging-etl \
        --arguments='--source_path=s3://bucket/metadata/ \
                     --target_path=s3://bucket/processed/ \
                     --database=healthcare_imaging \
                     --table_name=imaging_metadata'
"""

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    LongType,
    MapType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Initialize Glue context
sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)

# Get job arguments
args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "source_path",
        "target_path",
        "database",
        "table_name",
        "partition_year",
        "partition_month",
        "partition_day",
    ],
)

job.init(args["JOB_NAME"], args)

# Configuration
SOURCE_PATH = args["source_path"]
TARGET_PATH = args["target_path"]
DATABASE = args["database"]
TABLE_NAME = args["table_name"]
PARTITION_YEAR = args.get("partition_year")
PARTITION_MONTH = args.get("partition_month")
PARTITION_DAY = args.get("partition_day")


def get_imaging_schema() -> StructType:
    """Define schema for imaging metadata."""
    return StructType(
        [
            StructField("image_id", StringType(), False),
            StructField("study_id", StringType(), False),
            StructField("series_id", StringType(), True),
            StructField("patient_id", StringType(), False),
            StructField("modality", StringType(), False),
            StructField("body_part", StringType(), False),
            StructField("laterality", StringType(), True),
            StructField("facility_id", StringType(), False),
            StructField("acquisition_date", TimestampType(), False),
            StructField("s3_uri", StringType(), False),
            StructField("file_size_bytes", LongType(), False),
            StructField("image_format", StringType(), True),
            StructField("pixel_spacing", ArrayType(DoubleType()), True),
            StructField("slice_thickness", DoubleType(), True),
            StructField("rows", IntegerType(), True),
            StructField("columns", IntegerType(), True),
            StructField("bits_allocated", IntegerType(), True),
            StructField("dicom_tags", MapType(StringType(), StringType()), True),
            StructField("condition_codes", ArrayType(StringType()), True),
            StructField("created_at", TimestampType(), True),
            StructField("updated_at", TimestampType(), True),
        ]
    )


def get_clinical_schema() -> StructType:
    """Define schema for clinical records."""
    return StructType(
        [
            StructField("record_id", StringType(), False),
            StructField("patient_id", StringType(), False),
            StructField("study_id", StringType(), False),
            StructField("encounter_id", StringType(), True),
            StructField("diagnosis", StringType(), True),
            StructField("condition_codes", ArrayType(StringType()), True),
            StructField("procedure_codes", ArrayType(StringType()), True),
            StructField("physician_id", StringType(), True),
            StructField("facility_id", StringType(), False),
            StructField("record_date", TimestampType(), False),
            StructField("notes_summary", StringType(), True),
            StructField("age_at_study", IntegerType(), True),
            StructField("sex", StringType(), True),
            StructField("created_at", TimestampType(), True),
            StructField("updated_at", TimestampType(), True),
        ]
    )


def read_source_data(path: str, schema: StructType) -> DynamicFrame:
    """Read source NDJSON data from S3.

    Args:
        path: S3 path to source data.
        schema: Expected schema.

    Returns:
        DynamicFrame with source data.
    """
    print(f"Reading source data from: {path}")

    # Read as JSON with schema
    df = spark.read.option("multiline", "false").schema(schema).json(path)

    print(f"Read {df.count()} records from source")

    return DynamicFrame.fromDF(df, glue_context, "source_data")


def add_partition_columns(dynamic_frame: DynamicFrame) -> DynamicFrame:
    """Add partition columns based on acquisition_date or record_date.

    Args:
        dynamic_frame: Input DynamicFrame.

    Returns:
        DynamicFrame with partition columns.
    """
    df = dynamic_frame.toDF()

    # Determine date column
    date_col = "acquisition_date" if "acquisition_date" in df.columns else "record_date"

    # Add partition columns
    df = df.withColumn("year", F.year(F.col(date_col)).cast(StringType()))
    df = df.withColumn("month", F.format_string("%02d", F.month(F.col(date_col))))
    df = df.withColumn("day", F.format_string("%02d", F.dayofmonth(F.col(date_col))))

    # Add processing metadata
    df = df.withColumn("_processed_at", F.current_timestamp())
    df = df.withColumn("_etl_job", F.lit(args["JOB_NAME"]))

    return DynamicFrame.fromDF(df, glue_context, "partitioned_data")


def apply_data_quality_checks(dynamic_frame: DynamicFrame) -> DynamicFrame:
    """Apply data quality checks and transformations.

    Args:
        dynamic_frame: Input DynamicFrame.

    Returns:
        DynamicFrame with quality checks applied.
    """
    df = dynamic_frame.toDF()

    # Record initial count
    initial_count = df.count()
    print(f"Initial record count: {initial_count}")

    # Remove records with null required fields
    required_cols = ["image_id", "study_id", "patient_id", "facility_id"]
    existing_required = [c for c in required_cols if c in df.columns]

    for col in existing_required:
        df = df.filter(F.col(col).isNotNull())

    # Remove duplicates based on primary key
    pk_col = "image_id" if "image_id" in df.columns else "record_id"
    df = df.dropDuplicates([pk_col])

    # Standardize modality values (uppercase)
    if "modality" in df.columns:
        df = df.withColumn("modality", F.upper(F.col("modality")))

    # Standardize body_part values (uppercase)
    if "body_part" in df.columns:
        df = df.withColumn("body_part", F.upper(F.col("body_part")))

    # Ensure condition_codes is an array
    if "condition_codes" in df.columns:
        df = df.withColumn(
            "condition_codes",
            F.when(
                F.col("condition_codes").isNull(), F.array().cast(ArrayType(StringType()))
            ).otherwise(F.col("condition_codes")),
        )

    final_count = df.count()
    print(f"Final record count after quality checks: {final_count}")
    print(f"Records filtered: {initial_count - final_count}")

    return DynamicFrame.fromDF(df, glue_context, "quality_checked_data")


def write_parquet_data(
    dynamic_frame: DynamicFrame,
    target_path: str,
    partition_keys: list,
) -> None:
    """Write data to S3 as Parquet with partitioning.

    Args:
        dynamic_frame: Data to write.
        target_path: S3 target path.
        partition_keys: Columns to partition by.
    """
    print(f"Writing Parquet data to: {target_path}")

    # Write using Glue sink
    glue_context.write_dynamic_frame.from_options(
        frame=dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": target_path,
            "partitionKeys": partition_keys,
        },
        format="parquet",
        format_options={
            "compression": "snappy",
            "useGlueParquetWriter": True,
        },
    )

    print("Parquet write complete")


def update_glue_catalog(
    dynamic_frame: DynamicFrame,
    database: str,
    table_name: str,
) -> None:
    """Update Glue Data Catalog with new data.

    Args:
        dynamic_frame: Data frame with schema.
        database: Target database.
        table_name: Target table.
    """
    print(f"Updating Glue catalog: {database}.{table_name}")

    # Use catalog update option
    glue_context.write_dynamic_frame.from_catalog(
        frame=dynamic_frame,
        database=database,
        table_name=table_name,
        additional_options={
            "enableUpdateCatalog": True,
            "updateBehavior": "UPDATE_IN_DATABASE",
        },
    )

    print("Catalog update complete")


def compute_statistics(df) -> dict:
    """Compute statistics for the processed data.

    Args:
        df: Spark DataFrame.

    Returns:
        Dictionary of statistics.
    """
    stats = {
        "total_records": df.count(),
        "processing_time": datetime.utcnow().isoformat(),
    }

    if "modality" in df.columns:
        modality_counts = df.groupBy("modality").count().collect()
        stats["modality_distribution"] = {
            row["modality"]: row["count"] for row in modality_counts
        }

    if "facility_id" in df.columns:
        stats["facility_count"] = df.select("facility_id").distinct().count()

    if "file_size_bytes" in df.columns:
        size_stats = df.agg(
            F.sum("file_size_bytes").alias("total_bytes"),
            F.avg("file_size_bytes").alias("avg_bytes"),
        ).collect()[0]
        stats["total_size_gb"] = (size_stats["total_bytes"] or 0) / (1024**3)
        stats["avg_size_mb"] = (size_stats["avg_bytes"] or 0) / (1024**2)

    return stats


def main():
    """Main ETL job entry point."""
    print("=" * 60)
    print("Healthcare Imaging Data Lake - ETL Job")
    print("=" * 60)
    print(f"Source: {SOURCE_PATH}")
    print(f"Target: {TARGET_PATH}")
    print(f"Database: {DATABASE}")
    print(f"Table: {TABLE_NAME}")
    print("=" * 60)

    # Determine schema based on table name
    if "clinical" in TABLE_NAME.lower():
        schema = get_clinical_schema()
        partition_keys = ["year", "month", "day"]
    else:
        schema = get_imaging_schema()
        partition_keys = ["year", "month", "day"]

    # Build source path with partition filter if specified
    source_path = SOURCE_PATH
    if PARTITION_YEAR and PARTITION_MONTH and PARTITION_DAY:
        source_path = f"{SOURCE_PATH}year={PARTITION_YEAR}/month={PARTITION_MONTH}/day={PARTITION_DAY}/"
        print(f"Processing specific partition: {source_path}")

    # Read source data
    source_dynamic_frame = read_source_data(source_path, schema)

    # Apply data quality checks
    quality_frame = apply_data_quality_checks(source_dynamic_frame)

    # Add partition columns
    partitioned_frame = add_partition_columns(quality_frame)

    # Compute statistics before writing
    df = partitioned_frame.toDF()
    stats = compute_statistics(df)
    print(f"Statistics: {stats}")

    # Write to target
    write_parquet_data(partitioned_frame, TARGET_PATH, partition_keys)

    # Update catalog
    try:
        update_glue_catalog(partitioned_frame, DATABASE, TABLE_NAME)
    except Exception as e:
        print(f"Catalog update warning (non-fatal): {e}")

    print("=" * 60)
    print("ETL Job Complete")
    print(f"Processed {stats['total_records']} records")
    print("=" * 60)

    job.commit()


if __name__ == "__main__":
    main()
