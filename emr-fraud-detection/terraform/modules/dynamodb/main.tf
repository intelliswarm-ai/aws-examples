################################################################################
# DynamoDB Module - Alerts and Predictions Tables
################################################################################

################################################################################
# Fraud Alerts Table
################################################################################

resource "aws_dynamodb_table" "alerts" {
  name         = "${var.name_prefix}-fraud-alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "account_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "severity"
    type = "S"
  }

  # GSI for querying by account
  global_secondary_index {
    name            = "account-index"
    hash_key        = "account_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for querying by severity
  global_secondary_index {
    name            = "severity-index"
    hash_key        = "severity"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-fraud-alerts"
  })
}

################################################################################
# Predictions Table
################################################################################

resource "aws_dynamodb_table" "predictions" {
  name         = "${var.name_prefix}-predictions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "prediction_id"

  attribute {
    name = "prediction_id"
    type = "S"
  }

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "account_id"
    type = "S"
  }

  attribute {
    name = "processed_at"
    type = "S"
  }

  # GSI for querying by transaction
  global_secondary_index {
    name            = "transaction-index"
    hash_key        = "transaction_id"
    projection_type = "ALL"
  }

  # GSI for querying by account
  global_secondary_index {
    name            = "account-index"
    hash_key        = "account_id"
    range_key       = "processed_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-predictions"
  })
}

################################################################################
# Pipeline Executions Table
################################################################################

resource "aws_dynamodb_table" "executions" {
  name         = "${var.name_prefix}-executions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "execution_id"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "pipeline_name"
    type = "S"
  }

  attribute {
    name = "started_at"
    type = "S"
  }

  # GSI for querying by pipeline
  global_secondary_index {
    name            = "pipeline-index"
    hash_key        = "pipeline_name"
    range_key       = "started_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-executions"
  })
}
