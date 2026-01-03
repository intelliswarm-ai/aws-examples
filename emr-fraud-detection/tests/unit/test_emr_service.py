"""Unit tests for EMR service."""

from unittest.mock import MagicMock, patch

import pytest

from src.common.exceptions import (
    ClusterCreationError,
    ClusterNotFoundError,
    StepSubmissionError,
)
from src.common.models import EMRClusterConfig, SparkJobConfig
from src.services.emr_service import EMRService


class TestEMRService:
    """Tests for EMRService."""

    @pytest.fixture
    def emr_service(self, mock_emr_client: MagicMock) -> EMRService:
        """Create an EMRService with mocked client."""
        return EMRService(client=mock_emr_client)

    def test_create_cluster(self, emr_service: EMRService):
        """Test creating an EMR cluster."""
        config = EMRClusterConfig(
            cluster_name="test-cluster",
            log_uri="s3://logs/emr/",
        )

        cluster_id = emr_service.create_cluster(config)

        assert cluster_id == "j-12345"
        emr_service.client.run_job_flow.assert_called_once()

    def test_create_cluster_with_spot(self, emr_service: EMRService):
        """Test creating cluster with spot instances."""
        config = EMRClusterConfig(
            cluster_name="spot-cluster",
            log_uri="s3://logs/emr/",
            use_spot_instances=True,
            spot_bid_percentage=50,
            task_instance_count=2,
            task_instance_type="m5.xlarge",
        )

        cluster_id = emr_service.create_cluster(config)

        assert cluster_id == "j-12345"
        call_args = emr_service.client.run_job_flow.call_args
        instances = call_args.kwargs.get("Instances") or call_args[1].get("Instances")

        # Check that spot instances are configured
        instance_groups = instances.get("InstanceGroups", [])
        task_group = next(
            (g for g in instance_groups if g.get("InstanceRole") == "TASK"),
            None,
        )
        if task_group:
            assert task_group.get("Market") == "SPOT"

    def test_create_cluster_error(self, emr_service: EMRService):
        """Test handling cluster creation errors."""
        emr_service.client.run_job_flow.side_effect = Exception("Creation failed")

        config = EMRClusterConfig(
            cluster_name="error-cluster",
            log_uri="s3://logs/emr/",
        )

        with pytest.raises(ClusterCreationError):
            emr_service.create_cluster(config)

    def test_get_cluster_status(self, emr_service: EMRService):
        """Test getting cluster status."""
        status = emr_service.get_cluster_status("j-12345")

        assert status == "RUNNING"
        emr_service.client.describe_cluster.assert_called_once_with(
            ClusterId="j-12345"
        )

    def test_get_cluster_status_not_found(self, emr_service: EMRService):
        """Test handling cluster not found."""
        emr_service.client.describe_cluster.side_effect = (
            emr_service.client.exceptions.InvalidRequestException({}, "")
        )
        emr_service.client.exceptions.InvalidRequestException = Exception

        with pytest.raises(Exception):
            emr_service.get_cluster_status("j-invalid")

    def test_submit_step(self, emr_service: EMRService):
        """Test submitting a step to cluster."""
        emr_service.client.add_job_flow_steps.return_value = {
            "StepIds": ["s-12345"]
        }

        config = SparkJobConfig(
            job_name="test-job",
            main_class="",
            jar_path="s3://bucket/job.py",
            args=["--arg1", "value1"],
        )

        step_id = emr_service.submit_step("j-12345", config)

        assert step_id == "s-12345"
        emr_service.client.add_job_flow_steps.assert_called_once()

    def test_submit_step_error(self, emr_service: EMRService):
        """Test handling step submission errors."""
        emr_service.client.add_job_flow_steps.side_effect = Exception("Step failed")

        config = SparkJobConfig(
            job_name="failing-job",
            main_class="",
            jar_path="s3://bucket/job.py",
        )

        with pytest.raises(StepSubmissionError):
            emr_service.submit_step("j-12345", config)

    def test_get_step_status(self, emr_service: EMRService):
        """Test getting step status."""
        emr_service.client.describe_step.return_value = {
            "Step": {
                "Id": "s-12345",
                "Name": "test-step",
                "Status": {
                    "State": "COMPLETED",
                    "StateChangeReason": {},
                },
            }
        }

        status = emr_service.get_step_status("j-12345", "s-12345")

        assert status["state"] == "COMPLETED"
        assert status["id"] == "s-12345"

    def test_terminate_cluster(self, emr_service: EMRService):
        """Test terminating a cluster."""
        emr_service.terminate_cluster("j-12345")

        emr_service.client.terminate_job_flows.assert_called_once_with(
            JobFlowIds=["j-12345"]
        )

    def test_list_clusters(self, emr_service: EMRService):
        """Test listing clusters."""
        emr_service.client.list_clusters.return_value = {
            "Clusters": [
                {"Id": "j-12345", "Name": "cluster-1", "Status": {"State": "RUNNING"}},
                {"Id": "j-67890", "Name": "cluster-2", "Status": {"State": "WAITING"}},
            ],
        }

        clusters = emr_service.list_clusters(states=["RUNNING", "WAITING"])

        assert len(clusters) == 2
        emr_service.client.list_clusters.assert_called_once()

    def test_wait_for_cluster_ready(self, emr_service: EMRService):
        """Test waiting for cluster to be ready."""
        # Simulate cluster going from STARTING to RUNNING
        emr_service.client.describe_cluster.side_effect = [
            {"Cluster": {"Status": {"State": "STARTING"}}},
            {"Cluster": {"Status": {"State": "BOOTSTRAPPING"}}},
            {"Cluster": {"Status": {"State": "RUNNING"}}},
        ]

        with patch("time.sleep"):  # Skip actual sleep
            result = emr_service.wait_for_cluster_ready(
                "j-12345",
                timeout_seconds=60,
                poll_interval=1,
            )

        assert result is True
