################################################################################
# CloudWatch Module - Monitoring and Alarms
################################################################################

################################################################################
# Dashboard
################################################################################

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-fraud-detection"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Transaction Ingestion"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/Kinesis", "IncomingRecords", "StreamName", var.kinesis_stream_name, { stat = "Sum", period = 60 }],
            [".", "IncomingBytes", ".", ".", { stat = "Sum", period = 60 }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Kinesis Iterator Age"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/Kinesis", "GetRecords.IteratorAgeMilliseconds", "StreamName", var.kinesis_stream_name, { stat = "Maximum", period = 60 }]
          ]
          view = "timeSeries"
          annotations = {
            horizontal = [
              { value = var.kinesis_iterator_age_threshold, label = "Threshold" }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Invocations"
          region = data.aws_region.current.name
          metrics = [for fn in var.lambda_function_names :
            ["AWS/Lambda", "Invocations", "FunctionName", fn, { stat = "Sum", period = 60 }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Errors"
          region = data.aws_region.current.name
          metrics = [for fn in var.lambda_function_names :
            ["AWS/Lambda", "Errors", "FunctionName", fn, { stat = "Sum", period = 60 }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Duration"
          region = data.aws_region.current.name
          metrics = [for fn in var.lambda_function_names :
            ["AWS/Lambda", "Duration", "FunctionName", fn, { stat = "Average", period = 60 }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB Operations"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.alerts_table_name, { stat = "Sum", period = 60 }],
            [".", "ConsumedWriteCapacityUnits", ".", ".", { stat = "Sum", period = 60 }],
            [".", "ConsumedReadCapacityUnits", "TableName", var.predictions_table_name, { stat = "Sum", period = 60 }],
            [".", "ConsumedWriteCapacityUnits", ".", ".", { stat = "Sum", period = 60 }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "API Gateway Requests"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", var.api_gateway_name, { stat = "Sum", period = 60 }],
            [".", "4XXError", ".", ".", { stat = "Sum", period = 60 }],
            [".", "5XXError", ".", ".", { stat = "Sum", period = 60 }]
          ]
          view = "timeSeries"
        }
      }
    ]
  })
}

################################################################################
# Lambda Alarms
################################################################################

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${var.name_prefix}-${each.value}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = var.lambda_error_threshold
  alarm_description   = "Lambda function ${each.value} error rate too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []
  ok_actions    = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${var.name_prefix}-${each.value}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Average"
  threshold           = var.lambda_duration_threshold
  alarm_description   = "Lambda function ${each.value} duration too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []

  tags = var.tags
}

################################################################################
# Kinesis Alarms
################################################################################

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${var.name_prefix}-kinesis-iterator-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.kinesis_iterator_age_threshold
  alarm_description   = "Kinesis iterator age too high - consumers falling behind"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StreamName = var.kinesis_stream_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []
  ok_actions    = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []

  tags = var.tags
}

################################################################################
# Alarms SNS Topic
################################################################################

resource "aws_sns_topic" "alarms" {
  count = var.alarm_email != "" ? 1 : 0

  name = "${var.name_prefix}-cloudwatch-alarms"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "alarms_email" {
  count = var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

################################################################################
# Data Sources
################################################################################

data "aws_region" "current" {}
