################################################################################
# Lambda Module - Serverless Functions for Healthcare Imaging Data Lake
################################################################################

# Lambda Function: API Handler
resource "aws_lambda_function" "api_handler" {
  function_name = "${var.name_prefix}-api-handler"
  description   = "Main API handler for healthcare imaging data lake"
  role          = var.lambda_role_arn
  handler       = "src.handlers.api_handler.handler"
  runtime       = "python3.12"
  timeout       = var.api_timeout
  memory_size   = var.api_memory_size

  s3_bucket = var.deployment_bucket
  s3_key    = var.deployment_key

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      IMAGES_BUCKET        = var.images_bucket_name
      METADATA_BUCKET      = var.metadata_bucket_name
      KMS_KEY_ID           = var.kms_key_id
      GLUE_DATABASE        = var.glue_database_name
      ATHENA_WORKGROUP     = var.athena_workgroup_name
      RESULTS_BUCKET       = var.results_bucket_name
      ENABLE_LAKEFORMATION = tostring(var.enable_lakeformation)
      LOG_LEVEL            = var.log_level
      POWERTOOLS_SERVICE_NAME = "healthcare-imaging-lake"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags
}

# Lambda Function: Ingestion Handler
resource "aws_lambda_function" "ingestion_handler" {
  function_name = "${var.name_prefix}-ingestion-handler"
  description   = "Handles image and metadata ingestion with encryption"
  role          = var.lambda_role_arn
  handler       = "src.handlers.ingestion_handler.handler"
  runtime       = "python3.12"
  timeout       = var.ingestion_timeout
  memory_size   = var.ingestion_memory_size

  s3_bucket = var.deployment_bucket
  s3_key    = var.deployment_key

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      IMAGES_BUCKET        = var.images_bucket_name
      METADATA_BUCKET      = var.metadata_bucket_name
      KMS_KEY_ID           = var.kms_key_id
      GLUE_DATABASE        = var.glue_database_name
      LOG_LEVEL            = var.log_level
      POWERTOOLS_SERVICE_NAME = "healthcare-imaging-lake"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags
}

# Lambda Function: Catalog Handler
resource "aws_lambda_function" "catalog_handler" {
  function_name = "${var.name_prefix}-catalog-handler"
  description   = "Manages Glue catalog and crawler operations"
  role          = var.lambda_role_arn
  handler       = "src.handlers.catalog_handler.handler"
  runtime       = "python3.12"
  timeout       = var.catalog_timeout
  memory_size   = var.catalog_memory_size

  s3_bucket = var.deployment_bucket
  s3_key    = var.deployment_key

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      GLUE_DATABASE        = var.glue_database_name
      GLUE_CRAWLER_NAME    = var.glue_crawler_name
      LOG_LEVEL            = var.log_level
      POWERTOOLS_SERVICE_NAME = "healthcare-imaging-lake"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags
}

# Lambda Function: Query Handler
resource "aws_lambda_function" "query_handler" {
  function_name = "${var.name_prefix}-query-handler"
  description   = "Executes Athena queries for subset extraction"
  role          = var.lambda_role_arn
  handler       = "src.handlers.query_handler.handler"
  runtime       = "python3.12"
  timeout       = var.query_timeout
  memory_size   = var.query_memory_size

  s3_bucket = var.deployment_bucket
  s3_key    = var.deployment_key

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      GLUE_DATABASE        = var.glue_database_name
      ATHENA_WORKGROUP     = var.athena_workgroup_name
      RESULTS_BUCKET       = var.results_bucket_name
      ENABLE_LAKEFORMATION = tostring(var.enable_lakeformation)
      LOG_LEVEL            = var.log_level
      POWERTOOLS_SERVICE_NAME = "healthcare-imaging-lake"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags
}

# S3 Event Trigger for Ingestion
resource "aws_lambda_permission" "s3_invoke_ingestion" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.images_bucket_name}"
}

resource "aws_s3_bucket_notification" "image_upload" {
  bucket = var.images_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingestion_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".dcm"
  }

  depends_on = [aws_lambda_permission.s3_invoke_ingestion]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "api_handler" {
  name              = "/aws/lambda/${aws_lambda_function.api_handler.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "ingestion_handler" {
  name              = "/aws/lambda/${aws_lambda_function.ingestion_handler.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "catalog_handler" {
  name              = "/aws/lambda/${aws_lambda_function.catalog_handler.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "query_handler" {
  name              = "/aws/lambda/${aws_lambda_function.query_handler.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = var.tags
}
