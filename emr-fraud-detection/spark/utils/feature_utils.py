"""Feature engineering utilities.

This module provides utilities for computing fraud detection features
from raw transaction data.
"""

import logging
from typing import Any

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)


# Schema for raw transactions
RAW_TRANSACTION_SCHEMA = StructType([
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
    StructField("user_agent", StringType(), True),
])

# Schema for feature vectors
FEATURE_VECTOR_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("account_id", StringType(), False),
    StructField("amount", DoubleType(), False),
    StructField("hour_of_day", IntegerType(), False),
    StructField("day_of_week", IntegerType(), False),
    StructField("is_weekend", IntegerType(), False),
    StructField("tx_count_1h", IntegerType(), False),
    StructField("tx_count_24h", IntegerType(), False),
    StructField("tx_amount_1h", DoubleType(), False),
    StructField("tx_amount_24h", DoubleType(), False),
    StructField("avg_amount_30d", DoubleType(), False),
    StructField("std_amount_30d", DoubleType(), False),
    StructField("amount_zscore", DoubleType(), False),
    StructField("distance_from_last", DoubleType(), True),
    StructField("time_since_last", DoubleType(), True),
    StructField("is_new_merchant", IntegerType(), False),
    StructField("is_new_device", IntegerType(), False),
    StructField("is_high_risk_country", IntegerType(), False),
    StructField("channel_encoded", IntegerType(), False),
    StructField("tx_type_encoded", IntegerType(), False),
    StructField("timestamp", TimestampType(), False),
])


class FeatureEngineer:
    """Feature engineering for fraud detection."""

    # High-risk countries for fraud (example list)
    HIGH_RISK_COUNTRIES = {"NG", "RU", "CN", "BR", "IN", "PH", "ID", "VN"}

    # Channel encoding
    CHANNEL_ENCODING = {
        "POS": 0,
        "ATM": 1,
        "ONLINE": 2,
        "MOBILE": 3,
        "BRANCH": 4,
    }

    # Transaction type encoding
    TX_TYPE_ENCODING = {
        "PURCHASE": 0,
        "WITHDRAWAL": 1,
        "TRANSFER": 2,
        "DEPOSIT": 3,
        "PAYMENT": 4,
        "REFUND": 5,
    }

    def __init__(self, df: DataFrame) -> None:
        """Initialize feature engineer.

        Args:
            df: Raw transactions DataFrame
        """
        self.df = df

    def add_temporal_features(self) -> "FeatureEngineer":
        """Add time-based features."""
        self.df = self.df.withColumn(
            "hour_of_day", F.hour("timestamp")
        ).withColumn(
            "day_of_week", F.dayofweek("timestamp")
        ).withColumn(
            "is_weekend",
            F.when(F.dayofweek("timestamp").isin([1, 7]), 1).otherwise(0),
        ).withColumn(
            "date", F.to_date("timestamp")
        )

        logger.info("Added temporal features")
        return self

    def add_velocity_features(self) -> "FeatureEngineer":
        """Add velocity features (transaction counts/amounts in time windows)."""
        # Window specifications
        account_window_1h = Window.partitionBy("account_id").orderBy(
            F.col("timestamp").cast("long")
        ).rangeBetween(-3600, 0)  # 1 hour

        account_window_24h = Window.partitionBy("account_id").orderBy(
            F.col("timestamp").cast("long")
        ).rangeBetween(-86400, 0)  # 24 hours

        self.df = self.df.withColumn(
            "tx_count_1h", F.count("*").over(account_window_1h)
        ).withColumn(
            "tx_count_24h", F.count("*").over(account_window_24h)
        ).withColumn(
            "tx_amount_1h", F.sum("amount").over(account_window_1h)
        ).withColumn(
            "tx_amount_24h", F.sum("amount").over(account_window_24h)
        )

        logger.info("Added velocity features")
        return self

    def add_statistical_features(self) -> "FeatureEngineer":
        """Add statistical features (averages, standard deviations)."""
        # 30-day rolling window
        account_window_30d = Window.partitionBy("account_id").orderBy(
            F.col("timestamp").cast("long")
        ).rangeBetween(-2592000, -1)  # 30 days, excluding current

        self.df = self.df.withColumn(
            "avg_amount_30d",
            F.coalesce(F.avg("amount").over(account_window_30d), F.lit(0.0)),
        ).withColumn(
            "std_amount_30d",
            F.coalesce(F.stddev("amount").over(account_window_30d), F.lit(1.0)),
        )

        # Z-score for amount
        self.df = self.df.withColumn(
            "amount_zscore",
            F.when(
                F.col("std_amount_30d") > 0,
                (F.col("amount") - F.col("avg_amount_30d")) / F.col("std_amount_30d"),
            ).otherwise(0.0),
        )

        logger.info("Added statistical features")
        return self

    def add_distance_features(self) -> "FeatureEngineer":
        """Add location-based features."""
        # Window to get previous transaction
        account_window = Window.partitionBy("account_id").orderBy("timestamp")

        # Previous location
        self.df = self.df.withColumn(
            "prev_lat", F.lag("location_lat").over(account_window)
        ).withColumn(
            "prev_lon", F.lag("location_lon").over(account_window)
        ).withColumn(
            "prev_timestamp", F.lag("timestamp").over(account_window)
        )

        # Haversine distance calculation
        self.df = self.df.withColumn(
            "distance_from_last",
            F.when(
                (F.col("prev_lat").isNotNull()) & (F.col("location_lat").isNotNull()),
                self._haversine_distance(
                    F.col("prev_lat"),
                    F.col("prev_lon"),
                    F.col("location_lat"),
                    F.col("location_lon"),
                ),
            ).otherwise(F.lit(None)),
        )

        # Time since last transaction (in hours)
        self.df = self.df.withColumn(
            "time_since_last",
            F.when(
                F.col("prev_timestamp").isNotNull(),
                (F.col("timestamp").cast("long") - F.col("prev_timestamp").cast("long")) / 3600.0,
            ).otherwise(F.lit(None)),
        )

        # Cleanup temporary columns
        self.df = self.df.drop("prev_lat", "prev_lon", "prev_timestamp")

        logger.info("Added distance features")
        return self

    def add_behavioral_features(self) -> "FeatureEngineer":
        """Add behavioral features (new merchant, new device, etc.)."""
        # Window for historical merchants/devices
        account_history_window = Window.partitionBy("account_id").orderBy(
            "timestamp"
        ).rowsBetween(Window.unboundedPreceding, -1)

        # Collect historical merchants and devices
        self.df = self.df.withColumn(
            "historical_merchants",
            F.collect_set("merchant_id").over(account_history_window),
        ).withColumn(
            "historical_devices",
            F.collect_set("device_id").over(account_history_window),
        )

        # Check if merchant/device is new
        self.df = self.df.withColumn(
            "is_new_merchant",
            F.when(
                (F.col("merchant_id").isNotNull())
                & (~F.array_contains(F.col("historical_merchants"), F.col("merchant_id"))),
                1,
            ).otherwise(0),
        ).withColumn(
            "is_new_device",
            F.when(
                (F.col("device_id").isNotNull())
                & (~F.array_contains(F.col("historical_devices"), F.col("device_id"))),
                1,
            ).otherwise(0),
        )

        # High-risk country flag
        high_risk_list = F.array(*[F.lit(c) for c in self.HIGH_RISK_COUNTRIES])
        self.df = self.df.withColumn(
            "is_high_risk_country",
            F.when(
                F.array_contains(high_risk_list, F.col("location_country")), 1
            ).otherwise(0),
        )

        # Cleanup
        self.df = self.df.drop("historical_merchants", "historical_devices")

        logger.info("Added behavioral features")
        return self

    def add_categorical_encoding(self) -> "FeatureEngineer":
        """Encode categorical features."""
        # Channel encoding
        channel_mapping = F.create_map(
            *[item for pair in self.CHANNEL_ENCODING.items() for item in [F.lit(pair[0]), F.lit(pair[1])]]
        )
        self.df = self.df.withColumn(
            "channel_encoded",
            F.coalesce(channel_mapping[F.col("channel")], F.lit(99)),
        )

        # Transaction type encoding
        tx_type_mapping = F.create_map(
            *[item for pair in self.TX_TYPE_ENCODING.items() for item in [F.lit(pair[0]), F.lit(pair[1])]]
        )
        self.df = self.df.withColumn(
            "tx_type_encoded",
            F.coalesce(tx_type_mapping[F.col("transaction_type")], F.lit(99)),
        )

        logger.info("Added categorical encoding")
        return self

    def build(self) -> DataFrame:
        """Build final feature vector DataFrame.

        Returns:
            DataFrame with feature vectors
        """
        # Select final columns
        feature_columns = [
            "transaction_id",
            "account_id",
            "amount",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "tx_count_1h",
            "tx_count_24h",
            "tx_amount_1h",
            "tx_amount_24h",
            "avg_amount_30d",
            "std_amount_30d",
            "amount_zscore",
            "distance_from_last",
            "time_since_last",
            "is_new_merchant",
            "is_new_device",
            "is_high_risk_country",
            "channel_encoded",
            "tx_type_encoded",
            "timestamp",
            "date",
        ]

        # Select only existing columns
        existing_cols = [c for c in feature_columns if c in self.df.columns]
        result = self.df.select(existing_cols)

        logger.info("Feature vector built with %d columns", len(existing_cols))
        return result

    @staticmethod
    def _haversine_distance(
        lat1: Any,
        lon1: Any,
        lat2: Any,
        lon2: Any,
    ) -> Any:
        """Calculate Haversine distance between two points.

        Returns distance in kilometers.
        """
        # Earth radius in km
        R = 6371.0

        lat1_rad = F.radians(lat1)
        lat2_rad = F.radians(lat2)
        dlat = F.radians(lat2 - lat1)
        dlon = F.radians(lon2 - lon1)

        a = (
            F.sin(dlat / 2) ** 2
            + F.cos(lat1_rad) * F.cos(lat2_rad) * F.sin(dlon / 2) ** 2
        )
        c = 2 * F.asin(F.sqrt(a))

        return R * c


def engineer_features(df: DataFrame) -> DataFrame:
    """Convenience function to engineer all features.

    Args:
        df: Raw transactions DataFrame

    Returns:
        DataFrame with feature vectors
    """
    return (
        FeatureEngineer(df)
        .add_temporal_features()
        .add_velocity_features()
        .add_statistical_features()
        .add_distance_features()
        .add_behavioral_features()
        .add_categorical_encoding()
        .build()
    )


def get_feature_names() -> list[str]:
    """Get list of feature names for ML model.

    Returns:
        List of feature column names
    """
    return [
        "amount",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "tx_count_1h",
        "tx_count_24h",
        "tx_amount_1h",
        "tx_amount_24h",
        "avg_amount_30d",
        "std_amount_30d",
        "amount_zscore",
        "distance_from_last",
        "time_since_last",
        "is_new_merchant",
        "is_new_device",
        "is_high_risk_country",
        "channel_encoded",
        "tx_type_encoded",
    ]
