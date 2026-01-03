################################################################################
# EMR Spark Fraud Detection Pipeline - Outputs
################################################################################

# General
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# S3 Buckets
output "raw_bucket_name" {
  description = "Raw data bucket name"
  value       = module.s3.raw_bucket_name
}

output "features_bucket_name" {
  description = "Features bucket name"
  value       = module.s3.features_bucket_name
}

output "models_bucket_name" {
  description = "Models bucket name"
  value       = module.s3.models_bucket_name
}

output "predictions_bucket_name" {
  description = "Predictions bucket name"
  value       = module.s3.predictions_bucket_name
}

output "scripts_bucket_name" {
  description = "Scripts bucket name"
  value       = module.s3.scripts_bucket_name
}

# Kinesis
output "kinesis_stream_name" {
  description = "Kinesis stream name"
  value       = module.kinesis.stream_name
}

output "kinesis_stream_arn" {
  description = "Kinesis stream ARN"
  value       = module.kinesis.stream_arn
}

# DynamoDB
output "alerts_table_name" {
  description = "Fraud alerts DynamoDB table name"
  value       = module.dynamodb.alerts_table_name
}

output "predictions_table_name" {
  description = "Predictions DynamoDB table name"
  value       = module.dynamodb.predictions_table_name
}

# API Gateway
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "api_key" {
  description = "API key (if enabled)"
  value       = var.enable_api_key ? module.api_gateway.api_key : null
  sensitive   = true
}

# EMR
output "batch_cluster_id" {
  description = "Batch EMR cluster ID"
  value       = module.emr.batch_cluster_id
}

output "streaming_cluster_id" {
  description = "Streaming EMR cluster ID"
  value       = var.streaming_enabled ? module.emr.streaming_cluster_id : null
}

output "emr_master_public_dns" {
  description = "EMR master node public DNS"
  value       = module.emr.master_public_dns
}

# Step Functions
output "pipeline_state_machine_arn" {
  description = "ML pipeline state machine ARN"
  value       = module.step_functions.state_machine_arn
}

output "pipeline_state_machine_name" {
  description = "ML pipeline state machine name"
  value       = module.step_functions.state_machine_name
}

# SNS
output "fraud_alerts_topic_arn" {
  description = "Fraud alerts SNS topic ARN"
  value       = module.sns.fraud_alerts_topic_arn
}

output "pipeline_notifications_topic_arn" {
  description = "Pipeline notifications SNS topic ARN"
  value       = module.sns.pipeline_notifications_topic_arn
}

# Lambda Functions
output "lambda_function_names" {
  description = "Lambda function names"
  value       = module.lambda.function_names
}

# CloudWatch
output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.cloudwatch.dashboard_url
}

# Environment Variables for Application
output "environment_variables" {
  description = "Environment variables for application configuration"
  value = {
    AWS_REGION                       = var.aws_region
    KINESIS_STREAM_NAME              = module.kinesis.stream_name
    KINESIS_STREAM_ARN               = module.kinesis.stream_arn
    RAW_BUCKET                       = module.s3.raw_bucket_name
    FEATURES_BUCKET                  = module.s3.features_bucket_name
    MODELS_BUCKET                    = module.s3.models_bucket_name
    PREDICTIONS_BUCKET               = module.s3.predictions_bucket_name
    SCRIPTS_BUCKET                   = module.s3.scripts_bucket_name
    ALERTS_TABLE_NAME                = module.dynamodb.alerts_table_name
    PREDICTIONS_TABLE_NAME           = module.dynamodb.predictions_table_name
    FRAUD_ALERTS_TOPIC_ARN           = module.sns.fraud_alerts_topic_arn
    PIPELINE_NOTIFICATIONS_TOPIC_ARN = module.sns.pipeline_notifications_topic_arn
    PIPELINE_STATE_MACHINE_ARN       = module.step_functions.state_machine_arn
    EMR_CLUSTER_ID                   = module.emr.batch_cluster_id
    STREAMING_CLUSTER_ID             = var.streaming_enabled ? module.emr.streaming_cluster_id : ""
    FRAUD_THRESHOLD                  = tostring(var.fraud_threshold)
    SUSPICIOUS_THRESHOLD             = tostring(var.suspicious_threshold)
    MODEL_VERSION                    = var.model_version
  }
  sensitive = false
}
