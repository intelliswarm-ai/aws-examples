"""Unit tests for Kinesis service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.common.models import Transaction, TransactionChannel, TransactionType
from src.services.kinesis_service import KinesisService


class TestKinesisService:
    """Tests for KinesisService."""

    @pytest.fixture
    def kinesis_service(self, mock_kinesis_client: MagicMock) -> KinesisService:
        """Create a KinesisService with mocked client."""
        return KinesisService(
            stream_name="test-stream",
            client=mock_kinesis_client,
        )

    def test_put_record(self, kinesis_service: KinesisService, sample_transaction: dict):
        """Test putting a single record."""
        tx = Transaction(**sample_transaction)

        result = kinesis_service.put_record(tx)

        assert result["ShardId"] == "shard-001"
        kinesis_service.client.put_record.assert_called_once()

    def test_put_records_batch(
        self,
        kinesis_service: KinesisService,
        sample_transaction_batch: list,
    ):
        """Test putting multiple records."""
        transactions = [
            Transaction(**tx) for tx in sample_transaction_batch
        ]

        kinesis_service.client.put_records.return_value = {
            "FailedRecordCount": 0,
            "Records": [
                {"ShardId": f"shard-{i}", "SequenceNumber": str(i)}
                for i in range(len(transactions))
            ],
        }

        result = kinesis_service.put_records(transactions)

        assert result["FailedRecordCount"] == 0
        kinesis_service.client.put_records.assert_called_once()

    def test_put_records_with_failures(self, kinesis_service: KinesisService):
        """Test handling partial failures in batch put."""
        transactions = [
            Transaction(
                account_id=f"ACC{i:03d}",
                transaction_type=TransactionType.PURCHASE,
                channel=TransactionChannel.ONLINE,
                amount="100.00",
                currency="USD",
            )
            for i in range(3)
        ]

        # First call has failures, second succeeds
        kinesis_service.client.put_records.side_effect = [
            {
                "FailedRecordCount": 1,
                "Records": [
                    {"ShardId": "shard-0", "SequenceNumber": "0"},
                    {"ErrorCode": "ProvisionedThroughputExceededException"},
                    {"ShardId": "shard-2", "SequenceNumber": "2"},
                ],
            },
            {
                "FailedRecordCount": 0,
                "Records": [{"ShardId": "shard-1", "SequenceNumber": "1"}],
            },
        ]

        result = kinesis_service.put_records(transactions, max_retries=2)

        # Should have retried the failed record
        assert kinesis_service.client.put_records.call_count == 2

    def test_get_shard_iterator(self, kinesis_service: KinesisService):
        """Test getting shard iterator."""
        kinesis_service.client.get_shard_iterator.return_value = {
            "ShardIterator": "test-iterator"
        }

        iterator = kinesis_service.get_shard_iterator(
            shard_id="shard-001",
            iterator_type="LATEST",
        )

        assert iterator == "test-iterator"
        kinesis_service.client.get_shard_iterator.assert_called_once_with(
            StreamName="test-stream",
            ShardId="shard-001",
            ShardIteratorType="LATEST",
        )

    def test_get_records(self, kinesis_service: KinesisService, sample_transaction: dict):
        """Test getting records from stream."""
        kinesis_service.client.get_records.return_value = {
            "Records": [
                {
                    "Data": json.dumps(sample_transaction).encode(),
                    "SequenceNumber": "123",
                    "PartitionKey": sample_transaction["account_id"],
                }
            ],
            "NextShardIterator": "next-iterator",
            "MillisBehindLatest": 0,
        }

        records, next_iterator = kinesis_service.get_records("test-iterator")

        assert len(records) == 1
        assert next_iterator == "next-iterator"

    def test_describe_stream(self, kinesis_service: KinesisService):
        """Test describing stream."""
        kinesis_service.client.describe_stream.return_value = {
            "StreamDescription": {
                "StreamName": "test-stream",
                "StreamARN": "arn:aws:kinesis:us-east-1:123456789012:stream/test-stream",
                "StreamStatus": "ACTIVE",
                "Shards": [
                    {"ShardId": "shard-001"},
                    {"ShardId": "shard-002"},
                ],
            }
        }

        result = kinesis_service.describe_stream()

        assert result["StreamName"] == "test-stream"
        assert result["StreamStatus"] == "ACTIVE"
        assert len(result["Shards"]) == 2

    def test_stream_exists(self, kinesis_service: KinesisService):
        """Test checking if stream exists."""
        kinesis_service.client.describe_stream.return_value = {
            "StreamDescription": {"StreamStatus": "ACTIVE"}
        }

        assert kinesis_service.stream_exists() is True

    def test_stream_not_exists(self, kinesis_service: KinesisService):
        """Test checking if stream doesn't exist."""
        kinesis_service.client.describe_stream.side_effect = (
            kinesis_service.client.exceptions.ResourceNotFoundException({}, "")
        )

        # Mock the exception class
        kinesis_service.client.exceptions.ResourceNotFoundException = Exception

        with pytest.raises(Exception):
            kinesis_service.describe_stream()
