################################################################################
# Kinesis Module - Transaction Stream
################################################################################

resource "aws_kinesis_stream" "transactions" {
  name             = var.stream_name
  shard_count      = var.shard_count
  retention_period = var.retention_period

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  stream_mode_details {
    stream_mode = var.stream_mode
  }

  tags = merge(var.tags, {
    Name = var.stream_name
  })
}

################################################################################
# CloudWatch Alarms
################################################################################

resource "aws_cloudwatch_metric_alarm" "iterator_age" {
  alarm_name          = "${var.name_prefix}-kinesis-iterator-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.iterator_age_threshold
  alarm_description   = "Kinesis iterator age is too high"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "write_throughput" {
  alarm_name          = "${var.name_prefix}-kinesis-write-exceeded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Kinesis write throughput exceeded"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions.name
  }

  tags = var.tags
}
