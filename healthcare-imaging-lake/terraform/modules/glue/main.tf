################################################################################
# Glue Module - Data Catalog for Healthcare Imaging
################################################################################

# Glue Database
resource "aws_glue_catalog_database" "main" {
  name        = var.database_name
  description = "Healthcare Imaging Data Lake - HIPAA Compliant"

  parameters = {
    classification = "healthcare"
    compliance     = "hipaa"
  }
}

# Imaging Metadata Table
resource "aws_glue_catalog_table" "imaging" {
  name          = var.imaging_table_name
  database_name = aws_glue_catalog_database.main.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "storage.location.template" = "s3://${var.metadata_bucket_name}/metadata/year=$${year}/month=$${month}/day=$${day}"
  }

  storage_descriptor {
    location      = "s3://${var.metadata_bucket_name}/metadata/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "image_id"
      type = "string"
    }
    columns {
      name = "study_id"
      type = "string"
    }
    columns {
      name = "series_id"
      type = "string"
    }
    columns {
      name = "patient_id"
      type = "string"
    }
    columns {
      name = "modality"
      type = "string"
    }
    columns {
      name = "body_part"
      type = "string"
    }
    columns {
      name = "laterality"
      type = "string"
    }
    columns {
      name = "facility_id"
      type = "string"
    }
    columns {
      name = "acquisition_date"
      type = "timestamp"
    }
    columns {
      name = "s3_uri"
      type = "string"
    }
    columns {
      name = "file_size_bytes"
      type = "bigint"
    }
    columns {
      name = "image_format"
      type = "string"
    }
    columns {
      name = "condition_codes"
      type = "array<string>"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}

# Clinical Records Table
resource "aws_glue_catalog_table" "clinical" {
  name          = var.clinical_table_name
  database_name = aws_glue_catalog_database.main.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "storage.location.template" = "s3://${var.metadata_bucket_name}/clinical/year=$${year}/month=$${month}/day=$${day}"
  }

  storage_descriptor {
    location      = "s3://${var.metadata_bucket_name}/clinical/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "record_id"
      type = "string"
    }
    columns {
      name = "patient_id"
      type = "string"
    }
    columns {
      name = "study_id"
      type = "string"
    }
    columns {
      name = "encounter_id"
      type = "string"
    }
    columns {
      name = "diagnosis"
      type = "string"
    }
    columns {
      name = "condition_codes"
      type = "array<string>"
    }
    columns {
      name = "procedure_codes"
      type = "array<string>"
    }
    columns {
      name = "physician_id"
      type = "string"
    }
    columns {
      name = "facility_id"
      type = "string"
    }
    columns {
      name = "record_date"
      type = "timestamp"
    }
    columns {
      name = "notes_summary"
      type = "string"
    }
    columns {
      name = "age_at_study"
      type = "int"
    }
    columns {
      name = "sex"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}

# Glue Crawler
resource "aws_glue_crawler" "metadata" {
  name          = "${var.name_prefix}-crawler"
  database_name = aws_glue_catalog_database.main.name
  role          = var.glue_role_arn
  schedule      = var.crawler_schedule

  s3_target {
    path = "s3://${var.metadata_bucket_name}/metadata/"
  }

  s3_target {
    path = "s3://${var.metadata_bucket_name}/clinical/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })

  tags = var.tags
}

# Glue ETL Job
resource "aws_glue_job" "etl" {
  name     = "${var.name_prefix}-etl"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.metadata_bucket_name}/glue-scripts/metadata_crawler.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--database"                         = var.database_name
    "--source_path"                      = "s3://${var.metadata_bucket_name}/metadata/"
    "--target_path"                      = "s3://${var.metadata_bucket_name}/processed/"
  }

  execution_property {
    max_concurrent_runs = 2
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  tags = var.tags
}
