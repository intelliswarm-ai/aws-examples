################################################################################
# SNS Module - Notifications
################################################################################

################################################################################
# Fraud Alerts Topic
################################################################################

resource "aws_sns_topic" "fraud_alerts" {
  name = "${var.name_prefix}-fraud-alerts"

  kms_master_key_id = "alias/aws/sns"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-fraud-alerts"
  })
}

resource "aws_sns_topic_subscription" "fraud_alerts_email" {
  count = var.fraud_alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.fraud_alerts.arn
  protocol  = "email"
  endpoint  = var.fraud_alert_email
}

resource "aws_sns_topic_subscription" "fraud_alerts_sms" {
  count = var.enable_sms_alerts && var.sms_phone_number != "" ? 1 : 0

  topic_arn = aws_sns_topic.fraud_alerts.arn
  protocol  = "sms"
  endpoint  = var.sms_phone_number
}

################################################################################
# Pipeline Notifications Topic
################################################################################

resource "aws_sns_topic" "pipeline_notifications" {
  name = "${var.name_prefix}-pipeline-notifications"

  kms_master_key_id = "alias/aws/sns"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-pipeline-notifications"
  })
}

resource "aws_sns_topic_subscription" "pipeline_notifications_email" {
  count = var.fraud_alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.pipeline_notifications.arn
  protocol  = "email"
  endpoint  = var.fraud_alert_email
}

################################################################################
# Lambda DLQ Topic
################################################################################

resource "aws_sns_topic" "lambda_dlq" {
  count = var.lambda_dlq_enabled ? 1 : 0

  name = "${var.name_prefix}-lambda-dlq"

  kms_master_key_id = "alias/aws/sns"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-lambda-dlq"
  })
}
