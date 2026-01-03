################################################################################
# Lambda Module - Serverless Functions
################################################################################

data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/placeholder.zip"

  source {
    content  = "# Placeholder - replace with actual code"
    filename = "handler.py"
  }
}

locals {
  lambda_environment = {
    AWS_REGION                = data.aws_region.current.name
    LOG_LEVEL                 = "INFO"
    KINESIS_STREAM_NAME       = var.kinesis_stream_name
    RAW_BUCKET                = var.raw_bucket_name
    PREDICTIONS_BUCKET        = var.predictions_bucket_name
    ALERTS_TABLE_NAME         = var.alerts_table_name
    PREDICTIONS_TABLE_NAME    = var.predictions_table_name
    FRAUD_ALERTS_TOPIC_ARN    = var.fraud_alerts_topic_arn
    FRAUD_THRESHOLD           = tostring(var.fraud_threshold)
    SUSPICIOUS_THRESHOLD      = tostring(var.suspicious_threshold)
    MODEL_VERSION             = var.model_version
    POWERTOOLS_SERVICE_NAME   = "fraud-detection"
    POWERTOOLS_METRICS_NAMESPACE = "FraudDetection"
  }
}

data "aws_region" "current" {}

################################################################################
# Ingestion Lambda (API Gateway -> Kinesis)
################################################################################

resource "aws_lambda_function" "ingestion" {
  function_name = "${var.name_prefix}-ingestion"
  role          = var.lambda_role_arn
  handler       = "ingestion_handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = local.lambda_environment
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ingestion"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${aws_lambda_function.ingestion.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

################################################################################
# Stream Processor Lambda (Kinesis -> S3)
################################################################################

resource "aws_lambda_function" "stream_processor" {
  function_name = "${var.name_prefix}-stream-processor"
  role          = var.lambda_role_arn
  handler       = "stream_processor.handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 512

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = local.lambda_environment
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-stream-processor"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "stream_processor" {
  name              = "/aws/lambda/${aws_lambda_function.stream_processor.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn                   = var.kinesis_stream_arn
  function_name                      = aws_lambda_function.stream_processor.arn
  starting_position                  = "LATEST"
  batch_size                         = 100
  maximum_batching_window_in_seconds = 5
  parallelization_factor             = 2

  destination_config {
    on_failure {
      destination_arn = var.fraud_alerts_topic_arn
    }
  }
}

################################################################################
# Orchestration Lambda (Step Functions callbacks)
################################################################################

resource "aws_lambda_function" "orchestration" {
  function_name = "${var.name_prefix}-orchestration"
  role          = var.lambda_role_arn
  handler       = "orchestration_handler.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = local.lambda_environment
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-orchestration"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "orchestration" {
  name              = "/aws/lambda/${aws_lambda_function.orchestration.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

################################################################################
# Alert Lambda (Fraud notifications)
################################################################################

resource "aws_lambda_function" "alert" {
  function_name = "${var.name_prefix}-alert"
  role          = var.lambda_role_arn
  handler       = "alert_handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = local.lambda_environment
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alert"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "alert" {
  name              = "/aws/lambda/${aws_lambda_function.alert.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

################################################################################
# Query Lambda (API for querying results)
################################################################################

resource "aws_lambda_function" "query" {
  function_name = "${var.name_prefix}-query"
  role          = var.lambda_role_arn
  handler       = "query_handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = local.lambda_environment
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-query"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "query" {
  name              = "/aws/lambda/${aws_lambda_function.query.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}
