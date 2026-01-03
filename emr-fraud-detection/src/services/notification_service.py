"""Notification Service for fraud alerts.

This module provides a wrapper around SNS operations for sending
fraud alert notifications.
"""

import json
from typing import Any

from aws_lambda_powertools import Logger

from ..common import FraudAlert, settings
from ..common.clients import get_sns_client

logger = Logger()


class NotificationService:
    """Service for SNS notifications."""

    def __init__(self, client: Any = None, topic_arn: str | None = None) -> None:
        """Initialize Notification service.

        Args:
            client: boto3 SNS client (optional)
            topic_arn: SNS topic ARN (optional)
        """
        self.client = client or get_sns_client()
        self.topic_arn = topic_arn or settings.fraud_alerts_topic_arn

    def send_alert(self, alert: FraudAlert) -> str:
        """Send a fraud alert notification.

        Args:
            alert: Fraud alert to send

        Returns:
            Message ID

        Raises:
            Exception: If send fails
        """
        message = alert.to_sns_message()

        try:
            response = self.client.publish(
                TopicArn=self.topic_arn,
                Message=json.dumps(message),
                Subject=f"Fraud Alert [{alert.severity.value}]: {alert.alert_type.value}",
                MessageStructure="json",
                MessageAttributes={
                    "severity": {
                        "DataType": "String",
                        "StringValue": alert.severity.value,
                    },
                    "alert_type": {
                        "DataType": "String",
                        "StringValue": alert.alert_type.value,
                    },
                    "account_id": {
                        "DataType": "String",
                        "StringValue": alert.account_id,
                    },
                },
            )

            message_id = response["MessageId"]
            logger.info(
                "Alert notification sent",
                alert_id=alert.alert_id,
                message_id=message_id,
                severity=alert.severity.value,
            )

            return message_id

        except Exception as e:
            logger.error(
                "Failed to send alert notification",
                alert_id=alert.alert_id,
                error=str(e),
            )
            raise

    def send_message(
        self,
        subject: str,
        message: str,
        topic_arn: str | None = None,
    ) -> str:
        """Send a simple message notification.

        Args:
            subject: Message subject
            message: Message body
            topic_arn: Override topic ARN

        Returns:
            Message ID
        """
        try:
            response = self.client.publish(
                TopicArn=topic_arn or self.topic_arn,
                Subject=subject,
                Message=message,
            )

            message_id = response["MessageId"]
            logger.info("Message sent", message_id=message_id, subject=subject)
            return message_id

        except Exception as e:
            logger.error("Failed to send message", subject=subject, error=str(e))
            raise

    def send_json(
        self,
        subject: str,
        data: dict[str, Any],
        topic_arn: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> str:
        """Send a JSON message notification.

        Args:
            subject: Message subject
            data: JSON data to send
            topic_arn: Override topic ARN
            attributes: Message attributes

        Returns:
            Message ID
        """
        message_attrs: dict[str, dict[str, str]] = {}
        if attributes:
            for key, value in attributes.items():
                message_attrs[key] = {
                    "DataType": "String",
                    "StringValue": value,
                }

        try:
            params: dict[str, Any] = {
                "TopicArn": topic_arn or self.topic_arn,
                "Subject": subject,
                "Message": json.dumps(data, default=str),
            }

            if message_attrs:
                params["MessageAttributes"] = message_attrs

            response = self.client.publish(**params)

            message_id = response["MessageId"]
            logger.info("JSON message sent", message_id=message_id, subject=subject)
            return message_id

        except Exception as e:
            logger.error("Failed to send JSON message", subject=subject, error=str(e))
            raise

    def send_batch_summary(
        self,
        fraud_count: int,
        suspicious_count: int,
        total_processed: int,
        date: str,
    ) -> str:
        """Send a batch processing summary notification.

        Args:
            fraud_count: Number of fraudulent transactions
            suspicious_count: Number of suspicious transactions
            total_processed: Total transactions processed
            date: Processing date

        Returns:
            Message ID
        """
        fraud_rate = (fraud_count / total_processed * 100) if total_processed > 0 else 0

        message = f"""
Fraud Detection Daily Summary - {date}
========================================

Total Transactions Processed: {total_processed:,}
Fraudulent Transactions: {fraud_count:,}
Suspicious Transactions: {suspicious_count:,}
Fraud Detection Rate: {fraud_rate:.2f}%

Please review the dashboard for details.
        """.strip()

        subject = f"Fraud Detection Summary: {fraud_count} fraud, {suspicious_count} suspicious ({date})"

        return self.send_message(
            subject=subject,
            message=message,
            topic_arn=settings.pipeline_notifications_topic_arn or self.topic_arn,
        )

    def send_pipeline_status(
        self,
        execution_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Send a pipeline status notification.

        Args:
            execution_id: Pipeline execution ID
            status: Pipeline status (STARTED, COMPLETED, FAILED)
            details: Additional details

        Returns:
            Message ID
        """
        status_emoji = {
            "STARTED": "🚀",
            "RUNNING": "⏳",
            "COMPLETED": "✅",
            "SUCCEEDED": "✅",
            "FAILED": "❌",
        }.get(status, "ℹ️")

        subject = f"{status_emoji} Pipeline {status}: {execution_id}"

        message_lines = [
            f"Pipeline Execution: {execution_id}",
            f"Status: {status}",
            "",
        ]

        if details:
            message_lines.append("Details:")
            for key, value in details.items():
                message_lines.append(f"  - {key}: {value}")

        message = "\n".join(message_lines)

        return self.send_message(
            subject=subject,
            message=message,
            topic_arn=settings.pipeline_notifications_topic_arn or self.topic_arn,
        )
