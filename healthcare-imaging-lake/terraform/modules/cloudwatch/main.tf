################################################################################
# CloudWatch Module - Monitoring and Alerting for Healthcare Imaging Data Lake
################################################################################

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Invocations"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.api_handler_name],
            [".", ".", ".", var.ingestion_handler_name],
            [".", ".", ".", var.catalog_handler_name],
            [".", ".", ".", var.query_handler_name]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Errors"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", var.api_handler_name],
            [".", ".", ".", var.ingestion_handler_name],
            [".", ".", ".", var.catalog_handler_name],
            [".", ".", ".", var.query_handler_name]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Duration"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.api_handler_name],
            [".", ".", ".", var.ingestion_handler_name],
            [".", ".", ".", var.catalog_handler_name],
            [".", ".", ".", var.query_handler_name]
          ]
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Athena Query Execution"
          region = var.aws_region
          metrics = [
            ["AWS/Athena", "TotalExecutionTime", "WorkGroup", var.athena_workgroup_name],
            [".", "ProcessedBytes", ".", "."]
          ]
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "S3 Bucket Metrics"
          region = var.aws_region
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", var.images_bucket_name, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."]
          ]
          period = 86400
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "Glue Crawler Metrics"
          region = var.aws_region
          metrics = [
            ["Glue", "glue.driver.aggregate.numCompletedStages", "JobName", var.glue_crawler_name, "JobRunId", "ALL", "Type", "gauge"],
            [".", "glue.driver.aggregate.numFailedStages", ".", ".", ".", ".", ".", "."]
          ]
          period = 300
          stat   = "Sum"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset([
    var.api_handler_name,
    var.ingestion_handler_name,
    var.catalog_handler_name,
    var.query_handler_name
  ])

  alarm_name          = "${var.name_prefix}-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.error_threshold
  alarm_description   = "Lambda function ${each.key} error rate exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = {
    (var.api_handler_name)       = var.api_duration_threshold
    (var.ingestion_handler_name) = var.ingestion_duration_threshold
    (var.query_handler_name)     = var.query_duration_threshold
  }

  alarm_name          = "${var.name_prefix}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = each.value
  alarm_description   = "Lambda function ${each.key} duration exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "athena_query_timeout" {
  alarm_name          = "${var.name_prefix}-athena-query-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TotalExecutionTime"
  namespace           = "AWS/Athena"
  period              = 300
  statistic           = "Average"
  threshold           = var.athena_timeout_threshold
  alarm_description   = "Athena query execution time exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    WorkGroup = var.athena_workgroup_name
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "athena_data_scanned" {
  alarm_name          = "${var.name_prefix}-athena-data-scanned"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ProcessedBytes"
  namespace           = "AWS/Athena"
  period              = 3600
  statistic           = "Sum"
  threshold           = var.athena_data_scanned_threshold
  alarm_description   = "Athena data scanned exceeded threshold (cost control)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    WorkGroup = var.athena_workgroup_name
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions

  tags = var.tags
}

# Log Metric Filters for HIPAA Audit
resource "aws_cloudwatch_log_metric_filter" "access_denied" {
  name           = "${var.name_prefix}-access-denied"
  pattern        = "{ $.errorCode = \"AccessDenied\" || $.errorCode = \"UnauthorizedAccess\" }"
  log_group_name = var.api_handler_log_group

  metric_transformation {
    name      = "AccessDeniedCount"
    namespace = "${var.name_prefix}/Security"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "access_denied" {
  alarm_name          = "${var.name_prefix}-access-denied"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "AccessDeniedCount"
  namespace           = "${var.name_prefix}/Security"
  period              = 300
  statistic           = "Sum"
  threshold           = var.access_denied_threshold
  alarm_description   = "Access denied events exceeded threshold - potential security incident"
  treat_missing_data  = "notBreaching"

  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions

  tags = var.tags
}

resource "aws_cloudwatch_log_metric_filter" "phi_access" {
  name           = "${var.name_prefix}-phi-access"
  pattern        = "{ $.action = \"GetPatientData\" || $.action = \"QueryClinicalRecords\" }"
  log_group_name = var.api_handler_log_group

  metric_transformation {
    name      = "PHIAccessCount"
    namespace = "${var.name_prefix}/HIPAA"
    value     = "1"
  }
}

# SNS Topic for Alarms (if not provided)
resource "aws_sns_topic" "alarms" {
  count = var.create_sns_topic ? 1 : 0

  name              = "${var.name_prefix}-alarms"
  kms_master_key_id = var.sns_kms_key_id

  tags = var.tags
}
