"""Orchestration Handler.

This Lambda function handles Step Functions callbacks and pipeline
orchestration tasks.
"""

from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..common import PipelineExecution, PipelineStatus, settings
from ..services.dynamodb_service import DynamoDBService
from ..services.emr_service import EMRService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb_service = DynamoDBService()
emr_service = EMRService()


@tracer.capture_method
def validate_input(event: dict[str, Any]) -> dict[str, Any]:
    """Validate pipeline input parameters.

    Args:
        event: Pipeline input event

    Returns:
        Validation result with enriched parameters

    Raises:
        ValueError: If input is invalid
    """
    mode = event.get("mode", "FULL")
    if mode not in ["FULL", "TRAINING", "SCORING_ONLY"]:
        raise ValueError(f"Invalid mode: {mode}. Must be FULL, TRAINING, or SCORING_ONLY")

    date = event.get("date")
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    model_version = event.get("modelVersion", settings.model_version)

    # Create pipeline execution record
    execution = PipelineExecution(
        pipeline_name="fraud-detection",
        execution_mode=mode,
        status=PipelineStatus.RUNNING,
        input_location=settings.get_s3_raw_path(f"year={date[:4]}/month={date[5:7]}/day={date[8:10]}"),
        output_location=settings.get_s3_predictions_path(f"date={date}"),
        model_location=settings.get_s3_model_path(model_version),
    )

    # Store execution record
    dynamodb_service.put_execution(execution)

    logger.info(
        "Pipeline validated",
        execution_id=execution.execution_id,
        mode=mode,
        date=date,
        model_version=model_version,
    )

    metrics.add_metric(name="PipelineStarted", unit=MetricUnit.Count, value=1)

    return {
        "valid": True,
        "execution_id": execution.execution_id,
        "mode": mode,
        "date": date,
        "modelVersion": model_version,
        "input_location": execution.input_location,
        "output_location": execution.output_location,
        "model_location": execution.model_location,
    }


@tracer.capture_method
def check_cluster_status(event: dict[str, Any]) -> dict[str, Any]:
    """Check EMR cluster status.

    Args:
        event: Event with cluster_id

    Returns:
        Cluster status information
    """
    cluster_id = event.get("cluster_id") or event.get("cluster", {}).get("ClusterId")
    if not cluster_id:
        raise ValueError("cluster_id is required")

    status = emr_service.get_cluster_status(cluster_id)

    logger.info("Cluster status", cluster_id=cluster_id, status=status)

    return {
        "cluster_id": cluster_id,
        "status": status,
        "is_ready": status in ["RUNNING", "WAITING"],
        "is_terminated": status in ["TERMINATED", "TERMINATED_WITH_ERRORS"],
    }


@tracer.capture_method
def update_execution_status(event: dict[str, Any]) -> dict[str, Any]:
    """Update pipeline execution status.

    Args:
        event: Event with execution_id and status

    Returns:
        Update result
    """
    execution_id = event.get("execution_id")
    status = event.get("status", "RUNNING")
    error_message = event.get("error_message")
    metrics_data = event.get("metrics", {})

    if not execution_id:
        raise ValueError("execution_id is required")

    # Get existing execution
    execution = dynamodb_service.get_execution(execution_id)
    if not execution:
        logger.warning("Execution not found", execution_id=execution_id)
        return {"success": False, "message": "Execution not found"}

    # Update status
    execution.status = PipelineStatus(status)
    if status in ["SUCCEEDED", "FAILED"]:
        execution.completed_at = datetime.utcnow()
    if error_message:
        execution.error_message = error_message
    if metrics_data:
        execution.metrics.update(metrics_data)
        execution.transactions_processed = metrics_data.get("transactions_processed", 0)
        execution.fraud_detected = metrics_data.get("fraud_detected", 0)
        execution.suspicious_detected = metrics_data.get("suspicious_detected", 0)

    dynamodb_service.put_execution(execution)

    logger.info(
        "Execution status updated",
        execution_id=execution_id,
        status=status,
    )

    if status == "SUCCEEDED":
        metrics.add_metric(name="PipelineSucceeded", unit=MetricUnit.Count, value=1)
    elif status == "FAILED":
        metrics.add_metric(name="PipelineFailed", unit=MetricUnit.Count, value=1)

    return {
        "success": True,
        "execution_id": execution_id,
        "status": status,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for orchestration tasks.

    Routes to the appropriate function based on the 'action' field.

    Args:
        event: Event with action and parameters
        context: Lambda context

    Returns:
        Action result
    """
    action = event.get("action", "validate")

    logger.info("Orchestration action", action=action)

    if action == "validate":
        return validate_input(event.get("input", event))
    elif action == "check_cluster":
        return check_cluster_status(event)
    elif action == "update_status":
        return update_execution_status(event)
    else:
        raise ValueError(f"Unknown action: {action}")
