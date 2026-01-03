"""EMR Service for cluster and job management.

This module provides a wrapper around EMR operations for managing
Spark clusters and submitting jobs.
"""

import time
from typing import Any

from aws_lambda_powertools import Logger

from ..common import (
    ClusterCreationError,
    ClusterNotFoundError,
    ClusterTerminationError,
    EMRClusterConfig,
    EMRClusterState,
    EMRStepState,
    SparkJobConfig,
    StepExecutionError,
    StepSubmissionError,
    StepTimeoutError,
    settings,
)
from ..common.clients import get_emr_client

logger = Logger()


class EMRService:
    """Service for EMR cluster and job management."""

    def __init__(self, client: Any = None) -> None:
        """Initialize EMR service.

        Args:
            client: boto3 EMR client (optional)
        """
        self.client = client or get_emr_client()

    def create_cluster(self, config: EMRClusterConfig) -> str:
        """Create a new EMR cluster.

        Args:
            config: Cluster configuration

        Returns:
            Cluster ID

        Raises:
            ClusterCreationError: If cluster creation fails
        """
        try:
            instances_config: dict[str, Any] = {
                "InstanceGroups": [
                    {
                        "Name": "Master",
                        "Market": "ON_DEMAND",
                        "InstanceRole": "MASTER",
                        "InstanceType": config.master_instance_type,
                        "InstanceCount": 1,
                    },
                    {
                        "Name": "Core",
                        "Market": "SPOT" if config.use_spot_instances else "ON_DEMAND",
                        "InstanceRole": "CORE",
                        "InstanceType": config.core_instance_type,
                        "InstanceCount": config.core_instance_count,
                    },
                ],
                "Ec2SubnetId": config.subnet_id if hasattr(config, "subnet_id") else settings.emr_subnet_id,
                "KeepJobFlowAliveWhenNoSteps": config.keep_job_flow_alive,
                "TerminationProtected": config.termination_protected,
            }

            if config.task_instance_count and config.task_instance_count > 0:
                instances_config["InstanceGroups"].append({
                    "Name": "Task",
                    "Market": "SPOT" if config.use_spot_instances else "ON_DEMAND",
                    "InstanceRole": "TASK",
                    "InstanceType": config.task_instance_type,
                    "InstanceCount": config.task_instance_count,
                    "BidPrice": str(config.spot_bid_percentage / 100) if config.use_spot_instances else None,
                })

            response = self.client.run_job_flow(
                Name=config.cluster_name,
                ReleaseLabel=config.release_label,
                Applications=[{"Name": app} for app in config.applications],
                Instances=instances_config,
                LogUri=config.log_uri,
                ServiceRole=settings.emr_service_role,
                JobFlowRole=settings.emr_ec2_role,
                VisibleToAllUsers=True,
                AutoTerminationPolicy={"IdleTimeout": config.idle_timeout_seconds} if config.auto_terminate else None,
                Tags=[{"Key": k, "Value": v} for k, v in config.tags.items()],
            )

            cluster_id = response["JobFlowId"]
            logger.info("Cluster created", cluster_id=cluster_id, cluster_name=config.cluster_name)
            return cluster_id

        except Exception as e:
            raise ClusterCreationError(
                message=f"Failed to create cluster: {e}",
                cluster_name=config.cluster_name,
            )

    def get_cluster_status(self, cluster_id: str) -> str:
        """Get cluster status.

        Args:
            cluster_id: EMR cluster ID

        Returns:
            Cluster state string

        Raises:
            ClusterNotFoundError: If cluster doesn't exist
        """
        try:
            response = self.client.describe_cluster(ClusterId=cluster_id)
            return response["Cluster"]["Status"]["State"]

        except self.client.exceptions.InvalidRequestException:
            raise ClusterNotFoundError(cluster_id)

    def wait_for_cluster_ready(
        self,
        cluster_id: str,
        timeout_seconds: int = 1800,
        poll_interval: int = 30,
    ) -> bool:
        """Wait for cluster to be ready.

        Args:
            cluster_id: EMR cluster ID
            timeout_seconds: Maximum wait time
            poll_interval: Seconds between polls

        Returns:
            True if cluster is ready

        Raises:
            ClusterNotFoundError: If cluster doesn't exist
            TimeoutError: If timeout exceeded
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status = self.get_cluster_status(cluster_id)

            if status in [EMRClusterState.RUNNING.value, EMRClusterState.WAITING.value]:
                logger.info("Cluster ready", cluster_id=cluster_id, status=status)
                return True

            if status in [EMRClusterState.TERMINATED.value, EMRClusterState.TERMINATED_WITH_ERRORS.value]:
                raise ClusterTerminationError(cluster_id, f"Cluster terminated with status: {status}")

            logger.debug("Waiting for cluster", cluster_id=cluster_id, status=status)
            time.sleep(poll_interval)

        raise TimeoutError(f"Cluster {cluster_id} not ready within {timeout_seconds} seconds")

    def terminate_cluster(self, cluster_id: str) -> None:
        """Terminate an EMR cluster.

        Args:
            cluster_id: EMR cluster ID

        Raises:
            ClusterTerminationError: If termination fails
        """
        try:
            self.client.terminate_job_flows(JobFlowIds=[cluster_id])
            logger.info("Cluster termination initiated", cluster_id=cluster_id)

        except Exception as e:
            raise ClusterTerminationError(cluster_id, str(e))

    def submit_step(self, cluster_id: str, config: SparkJobConfig) -> str:
        """Submit a Spark step to an EMR cluster.

        Args:
            cluster_id: EMR cluster ID
            config: Spark job configuration

        Returns:
            Step ID

        Raises:
            StepSubmissionError: If step submission fails
        """
        try:
            step = config.to_emr_step()

            response = self.client.add_job_flow_steps(
                JobFlowId=cluster_id,
                Steps=[step],
            )

            step_id = response["StepIds"][0]
            logger.info("Step submitted", cluster_id=cluster_id, step_id=step_id, job_name=config.job_name)
            return step_id

        except Exception as e:
            raise StepSubmissionError(
                message=f"Failed to submit step: {e}",
                cluster_id=cluster_id,
                step_name=config.job_name,
            )

    def get_step_status(self, cluster_id: str, step_id: str) -> dict[str, Any]:
        """Get step status.

        Args:
            cluster_id: EMR cluster ID
            step_id: Step ID

        Returns:
            Step status dictionary
        """
        response = self.client.describe_step(ClusterId=cluster_id, StepId=step_id)
        step = response["Step"]

        return {
            "id": step["Id"],
            "name": step["Name"],
            "state": step["Status"]["State"],
            "state_change_reason": step["Status"].get("StateChangeReason", {}),
        }

    def wait_for_step_completion(
        self,
        cluster_id: str,
        step_id: str,
        timeout_seconds: int = 3600,
        poll_interval: int = 30,
    ) -> dict[str, Any]:
        """Wait for step to complete.

        Args:
            cluster_id: EMR cluster ID
            step_id: Step ID
            timeout_seconds: Maximum wait time
            poll_interval: Seconds between polls

        Returns:
            Step status dictionary

        Raises:
            StepExecutionError: If step fails
            StepTimeoutError: If timeout exceeded
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status = self.get_step_status(cluster_id, step_id)
            state = status["state"]

            if state == EMRStepState.COMPLETED.value:
                logger.info("Step completed", cluster_id=cluster_id, step_id=step_id)
                return status

            if state in [EMRStepState.FAILED.value, EMRStepState.CANCELLED.value, EMRStepState.INTERRUPTED.value]:
                reason = status["state_change_reason"].get("Message", "Unknown")
                raise StepExecutionError(
                    message=f"Step failed: {reason}",
                    cluster_id=cluster_id,
                    step_id=step_id,
                    step_state=state,
                    failure_reason=reason,
                )

            logger.debug("Waiting for step", cluster_id=cluster_id, step_id=step_id, state=state)
            time.sleep(poll_interval)

        raise StepTimeoutError(cluster_id, step_id, timeout_seconds)

    def list_clusters(
        self,
        states: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List EMR clusters.

        Args:
            states: Filter by cluster states

        Returns:
            List of cluster summaries
        """
        params: dict[str, Any] = {}
        if states:
            params["ClusterStates"] = states

        clusters = []
        marker = None

        while True:
            if marker:
                params["Marker"] = marker

            response = self.client.list_clusters(**params)
            clusters.extend(response.get("Clusters", []))

            marker = response.get("Marker")
            if not marker:
                break

        return clusters
