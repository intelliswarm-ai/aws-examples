################################################################################
# Lake Formation Module - Fine-Grained Access Control for HIPAA
################################################################################

data "aws_caller_identity" "current" {}

# Lake Formation Settings
resource "aws_lakeformation_data_lake_settings" "main" {
  admins = var.admin_arns

  create_database_default_permissions {
    principal   = "IAM_ALLOWED_PRINCIPALS"
    permissions = []
  }

  create_table_default_permissions {
    principal   = "IAM_ALLOWED_PRINCIPALS"
    permissions = []
  }
}

# Register S3 Locations with Lake Formation
resource "aws_lakeformation_resource" "images" {
  arn      = var.images_bucket_arn
  role_arn = var.lakeformation_role_arn
}

resource "aws_lakeformation_resource" "metadata" {
  arn      = var.metadata_bucket_arn
  role_arn = var.lakeformation_role_arn
}

# Database Permissions
resource "aws_lakeformation_permissions" "database_admin" {
  for_each = toset(var.admin_arns)

  principal = each.value

  database {
    name = var.database_name
  }

  permissions = [
    "ALL",
    "CREATE_TABLE",
    "DESCRIBE"
  ]
}

# Table Permissions for Imaging Metadata
resource "aws_lakeformation_permissions" "imaging_admin" {
  for_each = toset(var.admin_arns)

  principal = each.value

  table {
    database_name = var.database_name
    name          = var.imaging_table_name
  }

  permissions = [
    "ALL",
    "SELECT",
    "INSERT",
    "DELETE",
    "DESCRIBE",
    "ALTER"
  ]
}

# Table Permissions for Clinical Records
resource "aws_lakeformation_permissions" "clinical_admin" {
  for_each = toset(var.admin_arns)

  principal = each.value

  table {
    database_name = var.database_name
    name          = var.clinical_table_name
  }

  permissions = [
    "ALL",
    "SELECT",
    "INSERT",
    "DELETE",
    "DESCRIBE",
    "ALTER"
  ]
}

# Data Cell Filter for Researcher Access (PHI masked)
resource "aws_lakeformation_data_cells_filter" "researcher_imaging" {
  table_data {
    database_name    = var.database_name
    name             = "${var.imaging_table_name}_researcher_filter"
    table_catalog_id = data.aws_caller_identity.current.account_id
    table_name       = var.imaging_table_name

    column_wildcard {
      excluded_column_names = ["patient_id"]
    }

    row_filter {
      filter_expression = "TRUE"
    }
  }
}

resource "aws_lakeformation_data_cells_filter" "researcher_clinical" {
  table_data {
    database_name    = var.database_name
    name             = "${var.clinical_table_name}_researcher_filter"
    table_catalog_id = data.aws_caller_identity.current.account_id
    table_name       = var.clinical_table_name

    column_wildcard {
      excluded_column_names = ["patient_id", "diagnosis", "notes_summary"]
    }

    row_filter {
      filter_expression = "TRUE"
    }
  }
}
