"""DynamoDB Service for alerts and predictions storage.

This module provides a wrapper around DynamoDB operations for storing
and querying fraud alerts and predictions.
"""

from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger

from ..common import (
    DynamoDBError,
    FraudAlert,
    FraudPrediction,
    FraudStatus,
    PipelineExecution,
    settings,
)
from ..common.clients import get_dynamodb_client

logger = Logger()


class DynamoDBService:
    """Service for DynamoDB operations."""

    def __init__(self, client: Any = None) -> None:
        """Initialize DynamoDB service.

        Args:
            client: boto3 DynamoDB client (optional)
        """
        self.client = client or get_dynamodb_client()
        self.alerts_table = settings.alerts_table_name
        self.predictions_table = settings.predictions_table_name
        self.executions_table = settings.executions_table_name

    def put_alert(self, alert: FraudAlert) -> None:
        """Store a fraud alert.

        Args:
            alert: Fraud alert to store

        Raises:
            DynamoDBError: If put fails
        """
        try:
            self.client.put_item(
                TableName=self.alerts_table,
                Item=alert.to_dynamodb_item(),
            )
            logger.debug("Alert stored", alert_id=alert.alert_id)

        except Exception as e:
            raise DynamoDBError(
                message=f"Failed to store alert: {e}",
                table_name=self.alerts_table,
                operation="put_item",
            )

    def get_alert(self, alert_id: str) -> FraudAlert | None:
        """Get an alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            FraudAlert or None if not found
        """
        try:
            response = self.client.get_item(
                TableName=self.alerts_table,
                Key={"alert_id": {"S": alert_id}},
            )

            item = response.get("Item")
            if not item:
                return None

            return self._item_to_alert(item)

        except Exception as e:
            logger.error("Failed to get alert", alert_id=alert_id, error=str(e))
            return None

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: User/system acknowledging

        Returns:
            True if acknowledged successfully
        """
        try:
            self.client.update_item(
                TableName=self.alerts_table,
                Key={"alert_id": {"S": alert_id}},
                UpdateExpression="SET acknowledged = :ack, acknowledged_by = :by, acknowledged_at = :at",
                ExpressionAttributeValues={
                    ":ack": {"BOOL": True},
                    ":by": {"S": acknowledged_by},
                    ":at": {"S": datetime.utcnow().isoformat()},
                },
                ConditionExpression="attribute_exists(alert_id)",
            )
            return True

        except self.client.exceptions.ConditionalCheckFailedException:
            return False

        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False

    def query_alerts(
        self,
        account_id: str | None = None,
        severity: str | None = None,
        acknowledged: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[FraudAlert]:
        """Query alerts with filters.

        Args:
            account_id: Filter by account ID
            severity: Filter by severity
            acknowledged: Filter by acknowledgement status
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            List of matching alerts
        """
        try:
            if account_id:
                # Use account-index GSI
                response = self.client.query(
                    TableName=self.alerts_table,
                    IndexName="account-index",
                    KeyConditionExpression="account_id = :aid",
                    ExpressionAttributeValues={":aid": {"S": account_id}},
                    Limit=limit,
                    ScanIndexForward=False,
                )
            elif severity:
                # Use severity-index GSI
                response = self.client.query(
                    TableName=self.alerts_table,
                    IndexName="severity-index",
                    KeyConditionExpression="severity = :sev",
                    ExpressionAttributeValues={":sev": {"S": severity}},
                    Limit=limit,
                    ScanIndexForward=False,
                )
            else:
                # Scan with filters
                response = self.client.scan(
                    TableName=self.alerts_table,
                    Limit=limit,
                )

            items = response.get("Items", [])
            alerts = [self._item_to_alert(item) for item in items]

            # Apply additional filters
            if acknowledged is not None:
                alerts = [a for a in alerts if a.acknowledged == acknowledged]
            if start_date:
                alerts = [a for a in alerts if a.created_at >= start_date]
            if end_date:
                alerts = [a for a in alerts if a.created_at <= end_date]

            return alerts

        except Exception as e:
            logger.error("Failed to query alerts", error=str(e))
            return []

    def put_prediction(self, prediction: FraudPrediction) -> None:
        """Store a fraud prediction.

        Args:
            prediction: Fraud prediction to store
        """
        try:
            self.client.put_item(
                TableName=self.predictions_table,
                Item=prediction.to_dynamodb_item(),
            )
            logger.debug("Prediction stored", prediction_id=prediction.prediction_id)

        except Exception as e:
            raise DynamoDBError(
                message=f"Failed to store prediction: {e}",
                table_name=self.predictions_table,
                operation="put_item",
            )

    def get_prediction_by_transaction(self, transaction_id: str) -> FraudPrediction | None:
        """Get prediction by transaction ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            FraudPrediction or None if not found
        """
        try:
            response = self.client.query(
                TableName=self.predictions_table,
                IndexName="transaction-index",
                KeyConditionExpression="transaction_id = :tid",
                ExpressionAttributeValues={":tid": {"S": transaction_id}},
                Limit=1,
            )

            items = response.get("Items", [])
            if not items:
                return None

            return self._item_to_prediction(items[0])

        except Exception as e:
            logger.error("Failed to get prediction", transaction_id=transaction_id, error=str(e))
            return None

    def query_predictions(
        self,
        account_id: str | None = None,
        fraud_status: FraudStatus | None = None,
        min_score: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[FraudPrediction]:
        """Query predictions with filters.

        Args:
            account_id: Filter by account ID
            fraud_status: Filter by fraud status
            min_score: Minimum fraud score
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            List of matching predictions
        """
        try:
            if account_id:
                response = self.client.query(
                    TableName=self.predictions_table,
                    IndexName="account-index",
                    KeyConditionExpression="account_id = :aid",
                    ExpressionAttributeValues={":aid": {"S": account_id}},
                    Limit=limit,
                    ScanIndexForward=False,
                )
            else:
                response = self.client.scan(
                    TableName=self.predictions_table,
                    Limit=limit,
                )

            items = response.get("Items", [])
            predictions = [self._item_to_prediction(item) for item in items]

            # Apply filters
            if fraud_status:
                predictions = [p for p in predictions if p.fraud_status == fraud_status]
            if min_score is not None:
                predictions = [p for p in predictions if p.fraud_score >= min_score]
            if start_date:
                predictions = [p for p in predictions if p.processed_at >= start_date]
            if end_date:
                predictions = [p for p in predictions if p.processed_at <= end_date]

            return predictions

        except Exception as e:
            logger.error("Failed to query predictions", error=str(e))
            return []

    def put_execution(self, execution: PipelineExecution) -> None:
        """Store a pipeline execution record.

        Args:
            execution: Pipeline execution to store
        """
        try:
            self.client.put_item(
                TableName=self.executions_table,
                Item=execution.to_dynamodb_item(),
            )
            logger.debug("Execution stored", execution_id=execution.execution_id)

        except Exception as e:
            raise DynamoDBError(
                message=f"Failed to store execution: {e}",
                table_name=self.executions_table,
                operation="put_item",
            )

    def get_execution(self, execution_id: str) -> PipelineExecution | None:
        """Get execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            PipelineExecution or None if not found
        """
        try:
            response = self.client.get_item(
                TableName=self.executions_table,
                Key={"execution_id": {"S": execution_id}},
            )

            item = response.get("Item")
            if not item:
                return None

            return self._item_to_execution(item)

        except Exception as e:
            logger.error("Failed to get execution", execution_id=execution_id, error=str(e))
            return None

    def _item_to_alert(self, item: dict[str, Any]) -> FraudAlert:
        """Convert DynamoDB item to FraudAlert."""
        return FraudAlert(
            alert_id=item["alert_id"]["S"],
            transaction_id=item["transaction_id"]["S"],
            account_id=item["account_id"]["S"],
            fraud_score=float(item["fraud_score"]["N"]),
            alert_type=item["alert_type"]["S"],
            severity=item["severity"]["S"],
            message=item["message"]["S"],
            recommended_action=item["recommended_action"]["S"],
            created_at=datetime.fromisoformat(item["created_at"]["S"]),
            acknowledged=item.get("acknowledged", {}).get("BOOL", False),
            acknowledged_by=item.get("acknowledged_by", {}).get("S"),
            acknowledged_at=datetime.fromisoformat(item["acknowledged_at"]["S"]) if "acknowledged_at" in item else None,
        )

    def _item_to_prediction(self, item: dict[str, Any]) -> FraudPrediction:
        """Convert DynamoDB item to FraudPrediction."""
        return FraudPrediction(
            prediction_id=item["prediction_id"]["S"],
            transaction_id=item["transaction_id"]["S"],
            account_id=item["account_id"]["S"],
            fraud_score=float(item["fraud_score"]["N"]),
            fraud_status=FraudStatus(item["fraud_status"]["S"]),
            confidence=float(item["confidence"]["N"]),
            risk_factors=item.get("risk_factors", {}).get("SS", []),
            model_version=item["model_version"]["S"],
            processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
        )

    def _item_to_execution(self, item: dict[str, Any]) -> PipelineExecution:
        """Convert DynamoDB item to PipelineExecution."""
        return PipelineExecution(
            execution_id=item["execution_id"]["S"],
            pipeline_name=item["pipeline_name"]["S"],
            execution_mode=item.get("execution_mode", {}).get("S", "FULL"),
            status=item["status"]["S"],
            started_at=datetime.fromisoformat(item["started_at"]["S"]),
            completed_at=datetime.fromisoformat(item["completed_at"]["S"]) if "completed_at" in item else None,
            transactions_processed=int(item.get("transactions_processed", {}).get("N", 0)),
            fraud_detected=int(item.get("fraud_detected", {}).get("N", 0)),
            suspicious_detected=int(item.get("suspicious_detected", {}).get("N", 0)),
            error_message=item.get("error_message", {}).get("S"),
        )
