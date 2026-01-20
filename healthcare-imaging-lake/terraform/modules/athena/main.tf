################################################################################
# Athena Module - Query Workgroup for Healthcare Imaging
################################################################################

resource "aws_athena_workgroup" "main" {
  name = var.workgroup_name

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.results_bucket_name}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = var.kms_key_arn
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }

    bytes_scanned_cutoff_per_query = var.bytes_scanned_cutoff
  }

  tags = var.tags
}

# Named Queries
resource "aws_athena_named_query" "imaging_by_modality" {
  name        = "${var.workgroup_name}-imaging-by-modality"
  workgroup   = aws_athena_workgroup.main.name
  database    = var.database_name
  description = "Query imaging data by modality and body part"

  query = <<-EOT
    SELECT
        modality,
        body_part,
        COUNT(*) as image_count,
        COUNT(DISTINCT patient_id) as patient_count
    FROM imaging_metadata
    WHERE year = ? AND month = ?
    GROUP BY modality, body_part
    ORDER BY image_count DESC
  EOT
}

resource "aws_athena_named_query" "imaging_by_condition" {
  name        = "${var.workgroup_name}-imaging-by-condition"
  workgroup   = aws_athena_workgroup.main.name
  database    = var.database_name
  description = "Query imaging data by condition codes"

  query = <<-EOT
    SELECT
        image_id,
        study_id,
        s3_uri,
        modality,
        body_part,
        condition_codes
    FROM imaging_metadata
    WHERE CARDINALITY(ARRAY_INTERSECT(condition_codes, ARRAY[?])) > 0
    LIMIT 1000
  EOT
}

resource "aws_athena_named_query" "ml_cohort" {
  name        = "${var.workgroup_name}-ml-cohort"
  workgroup   = aws_athena_workgroup.main.name
  database    = var.database_name
  description = "Extract ML training cohort"

  query = <<-EOT
    WITH positive AS (
        SELECT image_id, s3_uri, modality, body_part, condition_codes, 'positive' as label
        FROM imaging_metadata
        WHERE CARDINALITY(ARRAY_INTERSECT(condition_codes, ARRAY[?])) > 0
        LIMIT ?
    ),
    negative AS (
        SELECT image_id, s3_uri, modality, body_part, condition_codes, 'negative' as label
        FROM imaging_metadata
        WHERE CARDINALITY(ARRAY_INTERSECT(condition_codes, ARRAY[?])) = 0
        LIMIT ?
    )
    SELECT * FROM positive
    UNION ALL
    SELECT * FROM negative
  EOT
}
