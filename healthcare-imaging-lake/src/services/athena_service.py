"""Athena service for healthcare imaging data lake queries."""

import time
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import settings
from src.common.exceptions import QueryError, QueryTimeoutError
from src.common.models import QueryResult, QueryState

logger = Logger()


class AthenaService:
    """Service for Athena query operations."""

    def __init__(
        self,
        database: str | None = None,
        workgroup: str | None = None,
        output_location: str | None = None,
    ) -> None:
        """Initialize Athena service.

        Args:
            database: Glue database name.
            workgroup: Athena workgroup name.
            output_location: S3 location for query results.
        """
        self.database = database or settings.glue_database
        self.workgroup = workgroup or settings.athena_workgroup
        self.output_location = output_location or settings.athena_output_location

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )
        self.client = boto3.client("athena", config=config, region_name=settings.aws_region)

    def execute_query(
        self,
        query: str,
        database: str | None = None,
        workgroup: str | None = None,
        wait: bool = True,
        timeout: int | None = None,
    ) -> QueryResult:
        """Execute Athena SQL query.

        Args:
            query: SQL query string.
            database: Database name (overrides default).
            workgroup: Workgroup name (overrides default).
            wait: Wait for query completion.
            timeout: Query timeout in seconds.

        Returns:
            QueryResult with execution details.

        Raises:
            QueryError: If query execution fails.
            QueryTimeoutError: If query times out.
        """
        db_name = database or self.database
        wg_name = workgroup or self.workgroup
        timeout_seconds = timeout or settings.athena_query_timeout

        try:
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": db_name},
                WorkGroup=wg_name,
                ResultConfiguration={"OutputLocation": self.output_location},
            )

            query_execution_id = response["QueryExecutionId"]
            logger.info(
                "Query started",
                extra={"query_id": query_execution_id, "database": db_name},
            )

            if wait:
                return self._wait_for_completion(
                    query_execution_id, timeout_seconds, query
                )

            return QueryResult(
                query_execution_id=query_execution_id,
                state=QueryState.QUEUED,
                query=query,
                database=db_name,
            )

        except ClientError as e:
            raise QueryError(
                f"Failed to start query: {e}",
                query=query,
            ) from e

    def get_query_execution(self, query_execution_id: str) -> QueryResult:
        """Get query execution status.

        Args:
            query_execution_id: Query execution ID.

        Returns:
            QueryResult with current status.

        Raises:
            QueryError: If status retrieval fails.
        """
        try:
            response = self.client.get_query_execution(
                QueryExecutionId=query_execution_id
            )

            execution = response["QueryExecution"]
            status = execution["Status"]
            statistics = execution.get("Statistics", {})

            state_map = {
                "QUEUED": QueryState.QUEUED,
                "RUNNING": QueryState.RUNNING,
                "SUCCEEDED": QueryState.SUCCEEDED,
                "FAILED": QueryState.FAILED,
                "CANCELLED": QueryState.CANCELLED,
            }

            return QueryResult(
                query_execution_id=query_execution_id,
                state=state_map.get(status["State"], QueryState.FAILED),
                query=execution.get("Query"),
                database=execution.get("QueryExecutionContext", {}).get("Database"),
                output_location=execution.get("ResultConfiguration", {}).get(
                    "OutputLocation"
                ),
                execution_time_ms=statistics.get("EngineExecutionTimeInMillis"),
                data_scanned_bytes=statistics.get("DataScannedInBytes"),
                error_message=status.get("StateChangeReason"),
                submitted_at=status.get("SubmissionDateTime"),
                completed_at=status.get("CompletionDateTime"),
            )

        except ClientError as e:
            raise QueryError(
                f"Failed to get query execution: {e}",
                query_execution_id=query_execution_id,
            ) from e

    def get_query_results(
        self,
        query_execution_id: str,
        max_results: int = 1000,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """Get query results with pagination.

        Args:
            query_execution_id: Query execution ID.
            max_results: Maximum results per page.
            next_token: Pagination token.

        Returns:
            Dictionary with columns, rows, and next_token.

        Raises:
            QueryError: If result retrieval fails.
        """
        try:
            params: dict[str, Any] = {
                "QueryExecutionId": query_execution_id,
                "MaxResults": max_results,
            }
            if next_token:
                params["NextToken"] = next_token

            response = self.client.get_query_results(**params)

            # Extract column names
            columns = [
                col["Label"] or col["Name"]
                for col in response["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
            ]

            # Extract rows (skip header row if no next_token)
            rows = []
            result_rows = response["ResultSet"]["Rows"]
            start_index = 0 if next_token else 1  # Skip header on first page

            for row in result_rows[start_index:]:
                row_data = [
                    datum.get("VarCharValue") for datum in row.get("Data", [])
                ]
                rows.append(dict(zip(columns, row_data)))

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "next_token": response.get("NextToken"),
            }

        except ClientError as e:
            raise QueryError(
                f"Failed to get query results: {e}",
                query_execution_id=query_execution_id,
            ) from e

    def cancel_query(self, query_execution_id: str) -> None:
        """Cancel a running query.

        Args:
            query_execution_id: Query execution ID.

        Raises:
            QueryError: If cancellation fails.
        """
        try:
            self.client.stop_query_execution(QueryExecutionId=query_execution_id)
            logger.info("Query cancelled", extra={"query_id": query_execution_id})

        except ClientError as e:
            raise QueryError(
                f"Failed to cancel query: {e}",
                query_execution_id=query_execution_id,
            ) from e

    def list_query_executions(
        self,
        workgroup: str | None = None,
        max_results: int = 50,
    ) -> list[str]:
        """List recent query executions.

        Args:
            workgroup: Workgroup name.
            max_results: Maximum results to return.

        Returns:
            List of query execution IDs.
        """
        wg_name = workgroup or self.workgroup
        try:
            response = self.client.list_query_executions(
                WorkGroup=wg_name,
                MaxResults=max_results,
            )
            return response.get("QueryExecutionIds", [])

        except ClientError as e:
            logger.warning(f"Failed to list query executions: {e}")
            return []

    def _wait_for_completion(
        self,
        query_execution_id: str,
        timeout: int,
        query: str,
    ) -> QueryResult:
        """Wait for query to complete.

        Args:
            query_execution_id: Query execution ID.
            timeout: Timeout in seconds.
            query: Original query string.

        Returns:
            Final QueryResult.

        Raises:
            QueryError: If query fails.
            QueryTimeoutError: If query times out.
        """
        start_time = time.time()
        poll_interval = 1.0

        while True:
            result = self.get_query_execution(query_execution_id)

            if result.state == QueryState.SUCCEEDED:
                logger.info(
                    "Query completed",
                    extra={
                        "query_id": query_execution_id,
                        "execution_time_ms": result.execution_time_ms,
                        "data_scanned_bytes": result.data_scanned_bytes,
                    },
                )
                return result

            if result.state == QueryState.FAILED:
                raise QueryError(
                    f"Query failed: {result.error_message}",
                    query_execution_id=query_execution_id,
                    query=query,
                )

            if result.state == QueryState.CANCELLED:
                raise QueryError(
                    "Query was cancelled",
                    query_execution_id=query_execution_id,
                    query=query,
                )

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                # Try to cancel the query
                try:
                    self.cancel_query(query_execution_id)
                except QueryError:
                    pass

                raise QueryTimeoutError(
                    f"Query timed out after {timeout} seconds",
                    query_execution_id=query_execution_id,
                    timeout_seconds=timeout,
                )

            time.sleep(poll_interval)
            # Exponential backoff capped at 5 seconds
            poll_interval = min(poll_interval * 1.5, 5.0)

    def query_imaging_by_condition(
        self,
        condition_codes: list[str],
        modality: str | None = None,
        body_part: str | None = None,
        limit: int = 1000,
    ) -> QueryResult:
        """Query imaging metadata by condition codes.

        Args:
            condition_codes: ICD-10 condition codes.
            modality: Filter by modality (CT, MRI, etc.).
            body_part: Filter by body part.
            limit: Maximum results.

        Returns:
            QueryResult with matching images.
        """
        conditions = ", ".join(f"'{code}'" for code in condition_codes)

        query = f"""
        SELECT
            image_id,
            study_id,
            s3_uri,
            modality,
            body_part,
            condition_codes,
            acquisition_date
        FROM {settings.imaging_table}
        WHERE CARDINALITY(
            ARRAY_INTERSECT(condition_codes, ARRAY[{conditions}])
        ) > 0
        """

        if modality:
            query += f"\n  AND modality = '{modality}'"
        if body_part:
            query += f"\n  AND body_part = '{body_part}'"

        query += f"\nLIMIT {limit}"

        return self.execute_query(query)

    def query_imaging_with_clinical(
        self,
        condition_codes: list[str] | None = None,
        facility_id: str | None = None,
        limit: int = 1000,
    ) -> QueryResult:
        """Query imaging with clinical record join.

        Args:
            condition_codes: Filter by ICD-10 codes.
            facility_id: Filter by facility.
            limit: Maximum results.

        Returns:
            QueryResult with joined data.
        """
        query = f"""
        SELECT
            i.image_id,
            i.study_id,
            i.s3_uri,
            i.modality,
            i.body_part,
            c.diagnosis,
            c.condition_codes,
            c.age_at_study,
            c.sex
        FROM {settings.imaging_table} i
        JOIN {settings.clinical_table} c
            ON i.study_id = c.study_id
        WHERE 1=1
        """

        if condition_codes:
            conditions = ", ".join(f"'{code}'" for code in condition_codes)
            query += f"""
        AND CARDINALITY(
            ARRAY_INTERSECT(c.condition_codes, ARRAY[{conditions}])
        ) > 0
            """

        if facility_id:
            query += f"\n  AND i.facility_id = '{facility_id}'"

        query += f"\nLIMIT {limit}"

        return self.execute_query(query)

    def get_statistics_by_modality(self) -> QueryResult:
        """Get aggregate statistics by modality.

        Returns:
            QueryResult with modality statistics.
        """
        query = f"""
        SELECT
            modality,
            body_part,
            COUNT(*) as image_count,
            COUNT(DISTINCT patient_id) as patient_count,
            SUM(file_size_bytes) / (1024*1024*1024) as total_gb,
            MIN(acquisition_date) as earliest_date,
            MAX(acquisition_date) as latest_date
        FROM {settings.imaging_table}
        GROUP BY modality, body_part
        ORDER BY image_count DESC
        """

        return self.execute_query(query)

    def extract_ml_cohort(
        self,
        positive_condition_codes: list[str],
        negative_condition_codes: list[str] | None = None,
        modality: str = "CT",
        body_part: str = "CHEST",
        samples_per_class: int = 5000,
    ) -> QueryResult:
        """Extract balanced ML training cohort.

        Args:
            positive_condition_codes: Condition codes for positive class.
            negative_condition_codes: Condition codes for negative class (or empty).
            modality: Imaging modality.
            body_part: Body part examined.
            samples_per_class: Number of samples per class.

        Returns:
            QueryResult with balanced cohort.
        """
        positive_codes = ", ".join(f"'{code}'" for code in positive_condition_codes)

        if negative_condition_codes:
            negative_codes = ", ".join(f"'{code}'" for code in negative_condition_codes)
            negative_filter = f"""
            CARDINALITY(
                ARRAY_INTERSECT(condition_codes, ARRAY[{negative_codes}])
            ) > 0
            """
        else:
            negative_filter = f"""
            CARDINALITY(
                ARRAY_INTERSECT(condition_codes, ARRAY[{positive_codes}])
            ) = 0
            AND CARDINALITY(condition_codes) = 0
            """

        query = f"""
        WITH positive AS (
            SELECT
                image_id,
                s3_uri,
                modality,
                body_part,
                condition_codes,
                'positive' as label
            FROM {settings.imaging_table}
            WHERE modality = '{modality}'
              AND body_part = '{body_part}'
              AND CARDINALITY(
                  ARRAY_INTERSECT(condition_codes, ARRAY[{positive_codes}])
              ) > 0
            LIMIT {samples_per_class}
        ),
        negative AS (
            SELECT
                image_id,
                s3_uri,
                modality,
                body_part,
                condition_codes,
                'negative' as label
            FROM {settings.imaging_table}
            WHERE modality = '{modality}'
              AND body_part = '{body_part}'
              AND {negative_filter}
            LIMIT {samples_per_class}
        )
        SELECT * FROM positive
        UNION ALL
        SELECT * FROM negative
        """

        return self.execute_query(query)
