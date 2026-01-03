"""Kinesis Service for transaction streaming.

This module provides a wrapper around Kinesis Data Streams operations
for ingesting and reading transaction data.
"""

from typing import Any

from aws_lambda_powertools import Logger

from ..common import (
    KinesisPutRecordError,
    KinesisStreamNotFoundError,
    KinesisThrottlingError,
    settings,
)
from ..common.clients import get_kinesis_client

logger = Logger()


class KinesisService:
    """Service for Kinesis Data Streams operations."""

    def __init__(self, client: Any = None, stream_name: str | None = None) -> None:
        """Initialize Kinesis service.

        Args:
            client: boto3 Kinesis client (optional)
            stream_name: Kinesis stream name (optional)
        """
        self.client = client or get_kinesis_client()
        self.stream_name = stream_name or settings.kinesis_stream_name

    def put_record(self, data: bytes, partition_key: str) -> str:
        """Put a single record to Kinesis.

        Args:
            data: Record data as bytes
            partition_key: Partition key for the record

        Returns:
            Sequence number of the record

        Raises:
            KinesisStreamNotFoundError: If stream doesn't exist
            KinesisThrottlingError: If throughput exceeded
            KinesisPutRecordError: If put fails
        """
        try:
            response = self.client.put_record(
                StreamName=self.stream_name,
                Data=data,
                PartitionKey=partition_key,
            )
            return response["SequenceNumber"]

        except self.client.exceptions.ResourceNotFoundException:
            raise KinesisStreamNotFoundError(self.stream_name)

        except self.client.exceptions.ProvisionedThroughputExceededException:
            raise KinesisThrottlingError(self.stream_name)

        except Exception as e:
            raise KinesisPutRecordError(
                message=f"Failed to put record: {e}",
                stream_name=self.stream_name,
            )

    def put_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Put multiple records to Kinesis.

        Args:
            records: List of records with 'Data' and 'PartitionKey'

        Returns:
            Response with failed record count and details

        Raises:
            KinesisStreamNotFoundError: If stream doesn't exist
            KinesisPutRecordError: If all records fail
        """
        if not records:
            return {"FailedRecordCount": 0, "Records": []}

        try:
            response = self.client.put_records(
                StreamName=self.stream_name,
                Records=records,
            )

            failed_count = response.get("FailedRecordCount", 0)
            if failed_count > 0:
                logger.warning(
                    "Some records failed",
                    failed_count=failed_count,
                    total=len(records),
                )

            return response

        except self.client.exceptions.ResourceNotFoundException:
            raise KinesisStreamNotFoundError(self.stream_name)

        except Exception as e:
            raise KinesisPutRecordError(
                message=f"Failed to put records: {e}",
                stream_name=self.stream_name,
                failed_count=len(records),
            )

    def describe_stream(self) -> dict[str, Any]:
        """Get stream description.

        Returns:
            Stream description with shard info

        Raises:
            KinesisStreamNotFoundError: If stream doesn't exist
        """
        try:
            response = self.client.describe_stream_summary(
                StreamName=self.stream_name,
            )
            return response["StreamDescriptionSummary"]

        except self.client.exceptions.ResourceNotFoundException:
            raise KinesisStreamNotFoundError(self.stream_name)

    def get_shard_iterator(
        self,
        shard_id: str,
        iterator_type: str = "LATEST",
        sequence_number: str | None = None,
    ) -> str:
        """Get a shard iterator for reading.

        Args:
            shard_id: Shard ID
            iterator_type: TRIM_HORIZON, LATEST, AT_SEQUENCE_NUMBER, AFTER_SEQUENCE_NUMBER
            sequence_number: Required for *_SEQUENCE_NUMBER types

        Returns:
            Shard iterator string
        """
        params: dict[str, Any] = {
            "StreamName": self.stream_name,
            "ShardId": shard_id,
            "ShardIteratorType": iterator_type,
        }

        if sequence_number and iterator_type in ["AT_SEQUENCE_NUMBER", "AFTER_SEQUENCE_NUMBER"]:
            params["StartingSequenceNumber"] = sequence_number

        response = self.client.get_shard_iterator(**params)
        return response["ShardIterator"]

    def get_records(
        self,
        shard_iterator: str,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get records from a shard.

        Args:
            shard_iterator: Shard iterator
            limit: Maximum records to fetch

        Returns:
            Tuple of (records, next_shard_iterator)
        """
        response = self.client.get_records(
            ShardIterator=shard_iterator,
            Limit=limit,
        )

        records = response.get("Records", [])
        next_iterator = response.get("NextShardIterator")

        return records, next_iterator

    def list_shards(self) -> list[dict[str, Any]]:
        """List all shards in the stream.

        Returns:
            List of shard descriptions
        """
        shards = []
        next_token = None

        while True:
            params: dict[str, Any] = {"StreamName": self.stream_name}
            if next_token:
                params["NextToken"] = next_token

            response = self.client.list_shards(**params)
            shards.extend(response.get("Shards", []))

            next_token = response.get("NextToken")
            if not next_token:
                break

        return shards
