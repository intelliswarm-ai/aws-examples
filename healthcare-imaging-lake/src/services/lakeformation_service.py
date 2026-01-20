"""Lake Formation service for healthcare imaging data lake fine-grained access control."""

from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import settings
from src.common.exceptions import (
    AccessDeniedError,
    DataLocationError,
    LakeFormationError,
    PermissionDeniedError,
)
from src.common.models import LakeFormationPermission

logger = Logger()


class LakeFormationService:
    """Service for Lake Formation fine-grained access control.

    Implements HIPAA-compliant row-level and cell-level security.
    """

    def __init__(self, database: str | None = None) -> None:
        """Initialize Lake Formation service.

        Args:
            database: Glue database name.
        """
        self.database = database or settings.glue_database

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )
        self.client = boto3.client(
            "lakeformation", config=config, region_name=settings.aws_region
        )

    def register_data_location(
        self,
        s3_location: str,
        role_arn: str,
        use_service_linked_role: bool = False,
    ) -> None:
        """Register S3 location with Lake Formation.

        Args:
            s3_location: S3 URI to register.
            role_arn: IAM role ARN for accessing the location.
            use_service_linked_role: Use service-linked role instead.

        Raises:
            DataLocationError: If registration fails.
        """
        try:
            self.client.register_resource(
                ResourceArn=s3_location,
                UseServiceLinkedRole=use_service_linked_role,
                RoleArn=role_arn if not use_service_linked_role else None,
            )
            logger.info(
                "Data location registered",
                extra={"location": s3_location, "role": role_arn},
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                logger.info("Data location already registered", extra={"location": s3_location})
            else:
                raise DataLocationError(
                    f"Failed to register data location: {e}",
                    s3_location=s3_location,
                ) from e

    def grant_database_permissions(
        self,
        principal_arn: str,
        database: str | None = None,
        permissions: list[str] | None = None,
        grant_option: bool = False,
    ) -> None:
        """Grant database-level permissions.

        Args:
            principal_arn: IAM principal ARN.
            database: Database name.
            permissions: List of permissions (CREATE_TABLE, DESCRIBE, etc.).
            grant_option: Allow grantee to grant permissions to others.

        Raises:
            LakeFormationError: If grant fails.
        """
        db_name = database or self.database
        perms = permissions or ["DESCRIBE"]

        try:
            params: dict[str, Any] = {
                "Principal": {"DataLakePrincipalIdentifier": principal_arn},
                "Resource": {"Database": {"Name": db_name}},
                "Permissions": perms,
            }
            if grant_option:
                params["PermissionsWithGrantOption"] = perms

            self.client.grant_permissions(**params)
            logger.info(
                "Database permissions granted",
                extra={"principal": principal_arn, "database": db_name, "permissions": perms},
            )

        except ClientError as e:
            raise LakeFormationError(
                f"Failed to grant database permissions: {e}",
                resource=db_name,
                permission=str(perms),
            ) from e

    def grant_table_permissions(
        self,
        principal_arn: str,
        table_name: str,
        database: str | None = None,
        permissions: list[str] | None = None,
        column_names: list[str] | None = None,
        grant_option: bool = False,
    ) -> None:
        """Grant table-level permissions with optional column restriction.

        Args:
            principal_arn: IAM principal ARN.
            table_name: Table name.
            database: Database name.
            permissions: List of permissions (SELECT, INSERT, DELETE, etc.).
            column_names: Specific columns to grant access to.
            grant_option: Allow grantee to grant permissions to others.

        Raises:
            PermissionDeniedError: If grant fails.
        """
        db_name = database or self.database
        perms = permissions or ["SELECT"]

        try:
            if column_names:
                # Column-level permissions
                resource = {
                    "TableWithColumns": {
                        "DatabaseName": db_name,
                        "Name": table_name,
                        "ColumnNames": column_names,
                    }
                }
            else:
                # Table-level permissions
                resource = {
                    "Table": {
                        "DatabaseName": db_name,
                        "Name": table_name,
                    }
                }

            params: dict[str, Any] = {
                "Principal": {"DataLakePrincipalIdentifier": principal_arn},
                "Resource": resource,
                "Permissions": perms,
            }
            if grant_option:
                params["PermissionsWithGrantOption"] = perms

            self.client.grant_permissions(**params)
            logger.info(
                "Table permissions granted",
                extra={
                    "principal": principal_arn,
                    "table": table_name,
                    "permissions": perms,
                    "columns": column_names,
                },
            )

        except ClientError as e:
            raise PermissionDeniedError(
                f"Failed to grant table permissions: {e}",
                principal_arn=principal_arn,
                table_name=table_name,
            ) from e

    def create_data_cell_filter(
        self,
        table_name: str,
        filter_name: str,
        row_filter_expression: str,
        column_names: list[str] | None = None,
        column_wildcard_exclude: list[str] | None = None,
        database: str | None = None,
    ) -> None:
        """Create a data cell filter for row-level and cell-level security.

        Args:
            table_name: Table name.
            filter_name: Unique filter name.
            row_filter_expression: SQL expression for row filtering.
            column_names: Columns to include (None = all columns).
            column_wildcard_exclude: Columns to exclude from wildcard.
            database: Database name.

        Raises:
            LakeFormationError: If filter creation fails.
        """
        db_name = database or self.database

        try:
            table_data: dict[str, Any] = {
                "TableCatalogId": boto3.client("sts").get_caller_identity()["Account"],
                "DatabaseName": db_name,
                "TableName": table_name,
                "Name": filter_name,
                "RowFilter": {"FilterExpression": row_filter_expression},
            }

            if column_names:
                table_data["ColumnNames"] = column_names
            elif column_wildcard_exclude:
                table_data["ColumnWildcard"] = {"ExcludedColumnNames": column_wildcard_exclude}
            else:
                table_data["ColumnWildcard"] = {}

            self.client.create_data_cells_filter(TableData=table_data)
            logger.info(
                "Data cell filter created",
                extra={
                    "table": table_name,
                    "filter": filter_name,
                    "expression": row_filter_expression,
                },
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                logger.info("Data cell filter already exists", extra={"filter": filter_name})
            else:
                raise LakeFormationError(
                    f"Failed to create data cell filter: {e}",
                    resource=f"{db_name}.{table_name}",
                ) from e

    def grant_data_cell_filter_permissions(
        self,
        principal_arn: str,
        table_name: str,
        filter_name: str,
        database: str | None = None,
    ) -> None:
        """Grant permissions to use a data cell filter.

        Args:
            principal_arn: IAM principal ARN.
            table_name: Table name.
            filter_name: Data cell filter name.
            database: Database name.

        Raises:
            PermissionDeniedError: If grant fails.
        """
        db_name = database or self.database

        try:
            self.client.grant_permissions(
                Principal={"DataLakePrincipalIdentifier": principal_arn},
                Resource={
                    "DataCellsFilter": {
                        "DatabaseName": db_name,
                        "TableName": table_name,
                        "Name": filter_name,
                    }
                },
                Permissions=["SELECT"],
            )
            logger.info(
                "Data cell filter permissions granted",
                extra={"principal": principal_arn, "filter": filter_name},
            )

        except ClientError as e:
            raise PermissionDeniedError(
                f"Failed to grant data cell filter permissions: {e}",
                principal_arn=principal_arn,
                table_name=table_name,
            ) from e

    def revoke_permissions(
        self,
        principal_arn: str,
        resource: dict[str, Any],
        permissions: list[str],
    ) -> None:
        """Revoke permissions from a principal.

        Args:
            principal_arn: IAM principal ARN.
            resource: Lake Formation resource specification.
            permissions: List of permissions to revoke.

        Raises:
            LakeFormationError: If revocation fails.
        """
        try:
            self.client.revoke_permissions(
                Principal={"DataLakePrincipalIdentifier": principal_arn},
                Resource=resource,
                Permissions=permissions,
            )
            logger.info(
                "Permissions revoked",
                extra={"principal": principal_arn, "permissions": permissions},
            )

        except ClientError as e:
            raise LakeFormationError(
                f"Failed to revoke permissions: {e}",
                permission=str(permissions),
            ) from e

    def list_permissions(
        self,
        principal_arn: str | None = None,
        resource_type: str | None = None,
    ) -> list[LakeFormationPermission]:
        """List Lake Formation permissions.

        Args:
            principal_arn: Filter by principal ARN.
            resource_type: Filter by resource type (DATABASE, TABLE, etc.).

        Returns:
            List of LakeFormationPermission objects.
        """
        permissions: list[LakeFormationPermission] = []
        paginator = self.client.get_paginator("list_permissions")

        params: dict[str, Any] = {}
        if principal_arn:
            params["Principal"] = {"DataLakePrincipalIdentifier": principal_arn}
        if resource_type:
            params["ResourceType"] = resource_type

        for page in paginator.paginate(**params):
            for perm in page.get("PrincipalResourcePermissions", []):
                principal = perm["Principal"]["DataLakePrincipalIdentifier"]
                resource = perm["Resource"]
                perms = perm["Permissions"]

                # Determine resource type and extract details
                if "Database" in resource:
                    permissions.append(
                        LakeFormationPermission(
                            principal_arn=principal,
                            resource_type="DATABASE",
                            database=resource["Database"]["Name"],
                            permissions=perms,
                        )
                    )
                elif "Table" in resource:
                    permissions.append(
                        LakeFormationPermission(
                            principal_arn=principal,
                            resource_type="TABLE",
                            database=resource["Table"]["DatabaseName"],
                            table_name=resource["Table"]["Name"],
                            permissions=perms,
                        )
                    )
                elif "TableWithColumns" in resource:
                    permissions.append(
                        LakeFormationPermission(
                            principal_arn=principal,
                            resource_type="COLUMN",
                            database=resource["TableWithColumns"]["DatabaseName"],
                            table_name=resource["TableWithColumns"]["Name"],
                            column_names=resource["TableWithColumns"].get("ColumnNames"),
                            permissions=perms,
                        )
                    )

        return permissions

    def check_permission(
        self,
        principal_arn: str,
        table_name: str,
        permission: str,
        database: str | None = None,
    ) -> bool:
        """Check if principal has specific permission on table.

        Args:
            principal_arn: IAM principal ARN.
            table_name: Table name.
            permission: Permission to check (SELECT, INSERT, etc.).
            database: Database name.

        Returns:
            True if principal has the permission.
        """
        db_name = database or self.database

        try:
            response = self.client.get_effective_permissions_for_path(
                ResourceArn=f"arn:aws:glue:{settings.aws_region}:{boto3.client('sts').get_caller_identity()['Account']}:table/{db_name}/{table_name}",
            )

            for perm in response.get("Permissions", []):
                if (
                    perm["Principal"]["DataLakePrincipalIdentifier"] == principal_arn
                    and permission in perm.get("Permissions", [])
                ):
                    return True

            return False

        except ClientError:
            return False

    def set_data_lake_settings(
        self,
        admin_arns: list[str],
        create_database_default_permissions: bool = False,
        create_table_default_permissions: bool = False,
    ) -> None:
        """Configure data lake settings.

        Args:
            admin_arns: List of IAM ARNs to be data lake administrators.
            create_database_default_permissions: Grant default permissions on database creation.
            create_table_default_permissions: Grant default permissions on table creation.

        Raises:
            LakeFormationError: If settings update fails.
        """
        try:
            admins = [{"DataLakePrincipalIdentifier": arn} for arn in admin_arns]

            params: dict[str, Any] = {
                "DataLakeSettings": {
                    "DataLakeAdmins": admins,
                    "CreateDatabaseDefaultPermissions": (
                        [] if not create_database_default_permissions else None
                    ),
                    "CreateTableDefaultPermissions": (
                        [] if not create_table_default_permissions else None
                    ),
                }
            }

            # Remove None values
            params["DataLakeSettings"] = {
                k: v for k, v in params["DataLakeSettings"].items() if v is not None
            }

            self.client.put_data_lake_settings(**params)
            logger.info("Data lake settings updated", extra={"admins": admin_arns})

        except ClientError as e:
            raise LakeFormationError(
                f"Failed to set data lake settings: {e}",
            ) from e

    def create_facility_filter(
        self,
        table_name: str,
        facility_id: str,
        database: str | None = None,
    ) -> str:
        """Create a row filter for facility-based access.

        Args:
            table_name: Table name.
            facility_id: Facility ID to filter on.
            database: Database name.

        Returns:
            Filter name created.
        """
        filter_name = f"{table_name}_facility_{facility_id}"
        row_filter = f"facility_id = '{facility_id}'"

        self.create_data_cell_filter(
            table_name=table_name,
            filter_name=filter_name,
            row_filter_expression=row_filter,
            database=database,
        )

        return filter_name

    def create_researcher_filter(
        self,
        table_name: str,
        database: str | None = None,
    ) -> str:
        """Create a filter for researchers that masks PHI columns.

        Args:
            table_name: Table name.
            database: Database name.

        Returns:
            Filter name created.
        """
        filter_name = f"{table_name}_researcher_view"

        # Exclude PHI columns from researcher access
        phi_columns = ["patient_id", "diagnosis", "notes_summary"]

        self.create_data_cell_filter(
            table_name=table_name,
            filter_name=filter_name,
            row_filter_expression="TRUE",  # All rows
            column_wildcard_exclude=phi_columns,
            database=database,
        )

        return filter_name

    def verify_hipaa_access(
        self,
        principal_arn: str,
        table_name: str,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Verify HIPAA-compliant access configuration.

        Args:
            principal_arn: IAM principal ARN.
            table_name: Table name.
            database: Database name.

        Returns:
            Dictionary with access verification results.
        """
        db_name = database or self.database
        permissions = self.list_permissions(principal_arn=principal_arn)

        table_perms = [
            p for p in permissions
            if p.table_name == table_name and p.database == db_name
        ]

        has_select = any("SELECT" in p.permissions for p in table_perms)
        has_column_restriction = any(p.column_names is not None for p in table_perms)
        has_row_filter = any(p.row_filter is not None for p in table_perms)

        return {
            "principal": principal_arn,
            "table": f"{db_name}.{table_name}",
            "has_access": has_select,
            "column_level_security": has_column_restriction,
            "row_level_security": has_row_filter,
            "hipaa_compliant": has_select and (has_column_restriction or has_row_filter),
            "permissions": [p.model_dump() for p in table_perms],
        }
