"""Glue service for healthcare imaging data lake catalog management."""

import time
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import settings
from src.common.exceptions import CatalogError, CrawlerError
from src.common.models import CatalogEntry, CrawlerRun, CrawlerStatus, PartitionSpec

logger = Logger()


class GlueService:
    """Service for Glue Data Catalog operations."""

    def __init__(
        self,
        database: str | None = None,
        crawler_name: str | None = None,
    ) -> None:
        """Initialize Glue service.

        Args:
            database: Glue database name.
            crawler_name: Glue crawler name.
        """
        self.database = database or settings.glue_database
        self.crawler_name = crawler_name or settings.glue_crawler_name

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )
        self.client = boto3.client("glue", config=config, region_name=settings.aws_region)

    def create_database(self, database: str | None = None) -> None:
        """Create Glue database if it doesn't exist.

        Args:
            database: Database name (defaults to configured database).

        Raises:
            CatalogError: If database creation fails.
        """
        db_name = database or self.database
        try:
            self.client.create_database(
                DatabaseInput={
                    "Name": db_name,
                    "Description": "Healthcare Imaging Data Lake - HIPAA Compliant",
                    "Parameters": {
                        "classification": "healthcare",
                        "compliance": "hipaa",
                    },
                }
            )
            logger.info("Database created", extra={"database": db_name})

        except ClientError as e:
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                logger.info("Database already exists", extra={"database": db_name})
            else:
                raise CatalogError(
                    f"Failed to create database: {e}",
                    database=db_name,
                ) from e

    def get_table(
        self,
        table_name: str,
        database: str | None = None,
    ) -> CatalogEntry | None:
        """Get table metadata from catalog.

        Args:
            table_name: Table name.
            database: Database name.

        Returns:
            CatalogEntry or None if table doesn't exist.
        """
        db_name = database or self.database
        try:
            response = self.client.get_table(DatabaseName=db_name, Name=table_name)
            table = response["Table"]

            columns = [
                {"name": col["Name"], "type": col["Type"]}
                for col in table.get("StorageDescriptor", {}).get("Columns", [])
            ]

            partition_keys = [
                key["Name"] for key in table.get("PartitionKeys", [])
            ]

            return CatalogEntry(
                database=db_name,
                table_name=table_name,
                location=table.get("StorageDescriptor", {}).get("Location", ""),
                columns=columns,
                partition_keys=partition_keys,
                row_count=table.get("Parameters", {}).get("recordCount"),
                size_bytes=table.get("Parameters", {}).get("sizeKey"),
                last_updated=table.get("UpdateTime"),
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "EntityNotFoundException":
                return None
            raise CatalogError(
                f"Failed to get table: {e}",
                database=db_name,
                table_name=table_name,
            ) from e

    def list_tables(self, database: str | None = None) -> list[str]:
        """List all tables in database.

        Args:
            database: Database name.

        Returns:
            List of table names.
        """
        db_name = database or self.database
        tables: list[str] = []
        paginator = self.client.get_paginator("get_tables")

        for page in paginator.paginate(DatabaseName=db_name):
            for table in page.get("TableList", []):
                tables.append(table["Name"])

        return tables

    def add_partition(
        self,
        table_name: str,
        partition: PartitionSpec,
        location: str,
        database: str | None = None,
    ) -> None:
        """Add partition to table.

        Args:
            table_name: Table name.
            partition: Partition specification.
            location: S3 location for partition data.
            database: Database name.

        Raises:
            CatalogError: If partition creation fails.
        """
        db_name = database or self.database
        partition_values = list(partition.partition_values.values())

        try:
            # Get table to copy storage descriptor
            table = self.get_table(table_name, db_name)
            if not table:
                raise CatalogError(
                    f"Table {table_name} not found",
                    database=db_name,
                    table_name=table_name,
                )

            self.client.create_partition(
                DatabaseName=db_name,
                TableName=table_name,
                PartitionInput={
                    "Values": partition_values,
                    "StorageDescriptor": {
                        "Location": location,
                        "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                        "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                        "Compressed": True,
                        "SerdeInfo": {
                            "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                        },
                    },
                },
            )
            logger.info(
                "Partition added",
                extra={
                    "table": table_name,
                    "partition": partition.path,
                },
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                logger.info(
                    "Partition already exists",
                    extra={"table": table_name, "partition": partition.path},
                )
            else:
                raise CatalogError(
                    f"Failed to add partition: {e}",
                    database=db_name,
                    table_name=table_name,
                ) from e

    def get_partitions(
        self,
        table_name: str,
        database: str | None = None,
        expression: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get partitions for a table.

        Args:
            table_name: Table name.
            database: Database name.
            expression: Filter expression (e.g., "year='2024'").

        Returns:
            List of partition dictionaries.
        """
        db_name = database or self.database
        partitions: list[dict[str, Any]] = []
        paginator = self.client.get_paginator("get_partitions")

        params: dict[str, Any] = {
            "DatabaseName": db_name,
            "TableName": table_name,
        }
        if expression:
            params["Expression"] = expression

        for page in paginator.paginate(**params):
            for partition in page.get("Partitions", []):
                partitions.append(
                    {
                        "values": partition["Values"],
                        "location": partition["StorageDescriptor"]["Location"],
                        "creation_time": partition.get("CreationTime"),
                    }
                )

        return partitions

    def start_crawler(self, crawler_name: str | None = None) -> None:
        """Start Glue crawler.

        Args:
            crawler_name: Crawler name.

        Raises:
            CrawlerError: If crawler start fails.
        """
        name = crawler_name or self.crawler_name
        try:
            self.client.start_crawler(Name=name)
            logger.info("Crawler started", extra={"crawler": name})

        except ClientError as e:
            if e.response["Error"]["Code"] == "CrawlerRunningException":
                logger.info("Crawler already running", extra={"crawler": name})
            else:
                raise CrawlerError(
                    f"Failed to start crawler: {e}",
                    crawler_name=name,
                ) from e

    def get_crawler_status(self, crawler_name: str | None = None) -> CrawlerRun:
        """Get crawler status.

        Args:
            crawler_name: Crawler name.

        Returns:
            CrawlerRun with status information.

        Raises:
            CrawlerError: If status retrieval fails.
        """
        name = crawler_name or self.crawler_name
        try:
            response = self.client.get_crawler(Name=name)
            crawler = response["Crawler"]

            status_map = {
                "READY": CrawlerStatus.READY,
                "RUNNING": CrawlerStatus.RUNNING,
                "STOPPING": CrawlerStatus.STOPPING,
            }
            status = status_map.get(crawler["State"], CrawlerStatus.READY)

            last_crawl = crawler.get("LastCrawl", {})
            return CrawlerRun(
                crawler_name=name,
                status=status,
                start_time=last_crawl.get("StartTime"),
                end_time=last_crawl.get("EndTime") if status == CrawlerStatus.READY else None,
                tables_created=last_crawl.get("TablesCreated", 0),
                tables_updated=last_crawl.get("TablesUpdated", 0),
                tables_deleted=last_crawl.get("TablesDeleted", 0),
                error_message=last_crawl.get("ErrorMessage"),
            )

        except ClientError as e:
            raise CrawlerError(
                f"Failed to get crawler status: {e}",
                crawler_name=name,
            ) from e

    def wait_for_crawler_completion(
        self,
        crawler_name: str | None = None,
        timeout: int = 1800,
        poll_interval: int = 30,
    ) -> CrawlerRun:
        """Wait for crawler to complete.

        Args:
            crawler_name: Crawler name.
            timeout: Maximum wait time in seconds.
            poll_interval: Polling interval in seconds.

        Returns:
            Final CrawlerRun status.

        Raises:
            CrawlerError: If crawler fails or times out.
        """
        name = crawler_name or self.crawler_name
        start_time = time.time()

        while True:
            status = self.get_crawler_status(name)

            if status.status == CrawlerStatus.READY:
                if status.error_message:
                    raise CrawlerError(
                        f"Crawler failed: {status.error_message}",
                        crawler_name=name,
                    )
                return status

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise CrawlerError(
                    f"Crawler timed out after {timeout} seconds",
                    crawler_name=name,
                )

            logger.info(
                "Waiting for crawler",
                extra={"crawler": name, "status": status.status.value, "elapsed": elapsed},
            )
            time.sleep(poll_interval)

    def batch_create_partition(
        self,
        table_name: str,
        partitions: list[tuple[PartitionSpec, str]],
        database: str | None = None,
    ) -> dict[str, int]:
        """Batch create partitions.

        Args:
            table_name: Table name.
            partitions: List of (partition_spec, location) tuples.
            database: Database name.

        Returns:
            Dictionary with created and failed counts.
        """
        db_name = database or self.database

        partition_inputs = []
        for partition, location in partitions:
            partition_inputs.append(
                {
                    "Values": list(partition.partition_values.values()),
                    "StorageDescriptor": {
                        "Location": location,
                        "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                        "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                        "Compressed": True,
                        "SerdeInfo": {
                            "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                        },
                    },
                }
            )

        try:
            response = self.client.batch_create_partition(
                DatabaseName=db_name,
                TableName=table_name,
                PartitionInputList=partition_inputs,
            )

            errors = response.get("Errors", [])
            return {
                "created": len(partitions) - len(errors),
                "failed": len(errors),
            }

        except ClientError as e:
            raise CatalogError(
                f"Batch partition creation failed: {e}",
                database=db_name,
                table_name=table_name,
            ) from e

    def update_table_statistics(
        self,
        table_name: str,
        row_count: int,
        size_bytes: int,
        database: str | None = None,
    ) -> None:
        """Update table statistics.

        Args:
            table_name: Table name.
            row_count: Number of rows.
            size_bytes: Total size in bytes.
            database: Database name.
        """
        db_name = database or self.database
        try:
            self.client.update_table(
                DatabaseName=db_name,
                TableInput={
                    "Name": table_name,
                    "Parameters": {
                        "recordCount": str(row_count),
                        "sizeKey": str(size_bytes),
                        "UPDATED_BY_CRAWLER": datetime.utcnow().isoformat(),
                    },
                },
            )
            logger.info(
                "Table statistics updated",
                extra={"table": table_name, "row_count": row_count},
            )

        except ClientError as e:
            logger.warning(f"Failed to update table statistics: {e}")
