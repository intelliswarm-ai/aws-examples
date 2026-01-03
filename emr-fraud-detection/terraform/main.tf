################################################################################
# EMR Spark Fraud Detection Pipeline - Main Terraform Configuration
################################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Uncomment to use S3 backend for state management
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "emr-fraud-detection/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

################################################################################
# Local Variables
################################################################################

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Application = "fraud-detection"
  }

  # S3 bucket names
  raw_bucket_name         = "${local.name_prefix}-raw-${data.aws_caller_identity.current.account_id}"
  features_bucket_name    = "${local.name_prefix}-features-${data.aws_caller_identity.current.account_id}"
  models_bucket_name      = "${local.name_prefix}-models-${data.aws_caller_identity.current.account_id}"
  predictions_bucket_name = "${local.name_prefix}-predictions-${data.aws_caller_identity.current.account_id}"
  scripts_bucket_name     = "${local.name_prefix}-scripts-${data.aws_caller_identity.current.account_id}"
  logs_bucket_name        = "${local.name_prefix}-logs-${data.aws_caller_identity.current.account_id}"
}

################################################################################
# Data Sources
################################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

################################################################################
# VPC Module
################################################################################

module "vpc" {
  source = "./modules/vpc"

  name_prefix         = local.name_prefix
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  enable_nat_gateway  = var.enable_nat_gateway
  single_nat_gateway  = var.single_nat_gateway
  enable_vpn_gateway  = false
  enable_flow_logs    = var.environment == "prod"
  flow_logs_bucket_arn = var.environment == "prod" ? module.s3.logs_bucket_arn : null

  tags = local.common_tags
}

################################################################################
# S3 Module
################################################################################

module "s3" {
  source = "./modules/s3"

  name_prefix             = local.name_prefix
  raw_bucket_name         = local.raw_bucket_name
  features_bucket_name    = local.features_bucket_name
  models_bucket_name      = local.models_bucket_name
  predictions_bucket_name = local.predictions_bucket_name
  scripts_bucket_name     = local.scripts_bucket_name
  logs_bucket_name        = local.logs_bucket_name
  environment             = var.environment
  enable_versioning       = var.environment == "prod"
  lifecycle_glacier_days  = 90
  lifecycle_expire_days   = 365

  tags = local.common_tags
}

################################################################################
# IAM Module
################################################################################

module "iam" {
  source = "./modules/iam"

  name_prefix             = local.name_prefix
  raw_bucket_arn          = module.s3.raw_bucket_arn
  features_bucket_arn     = module.s3.features_bucket_arn
  models_bucket_arn       = module.s3.models_bucket_arn
  predictions_bucket_arn  = module.s3.predictions_bucket_arn
  scripts_bucket_arn      = module.s3.scripts_bucket_arn
  logs_bucket_arn         = module.s3.logs_bucket_arn
  kinesis_stream_arn      = module.kinesis.stream_arn
  dynamodb_alerts_arn     = module.dynamodb.alerts_table_arn
  dynamodb_predictions_arn = module.dynamodb.predictions_table_arn
  sns_topic_arn           = module.sns.fraud_alerts_topic_arn

  tags = local.common_tags
}

################################################################################
# Kinesis Module
################################################################################

module "kinesis" {
  source = "./modules/kinesis"

  name_prefix      = local.name_prefix
  stream_name      = "${local.name_prefix}-transactions"
  shard_count      = var.kinesis_shard_count
  retention_period = var.kinesis_retention_hours

  tags = local.common_tags
}

################################################################################
# DynamoDB Module
################################################################################

module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix          = local.name_prefix
  environment          = var.environment
  enable_point_in_time = var.environment == "prod"
  alerts_ttl_days      = 90
  predictions_ttl_days = 365

  tags = local.common_tags
}

################################################################################
# SNS Module
################################################################################

module "sns" {
  source = "./modules/sns"

  name_prefix            = local.name_prefix
  fraud_alert_email      = var.fraud_alert_email
  enable_sms_alerts      = var.enable_sms_alerts
  sms_phone_number       = var.sms_phone_number
  lambda_dlq_enabled     = true

  tags = local.common_tags
}

################################################################################
# Lambda Module
################################################################################

module "lambda" {
  source = "./modules/lambda"

  name_prefix              = local.name_prefix
  lambda_role_arn          = module.iam.lambda_role_arn
  kinesis_stream_arn       = module.kinesis.stream_arn
  kinesis_stream_name      = module.kinesis.stream_name
  raw_bucket_name          = module.s3.raw_bucket_name
  predictions_bucket_name  = module.s3.predictions_bucket_name
  alerts_table_name        = module.dynamodb.alerts_table_name
  predictions_table_name   = module.dynamodb.predictions_table_name
  fraud_alerts_topic_arn   = module.sns.fraud_alerts_topic_arn
  vpc_subnet_ids           = module.vpc.private_subnet_ids
  vpc_security_group_ids   = [module.vpc.lambda_security_group_id]
  environment              = var.environment
  log_retention_days       = var.log_retention_days

  # ML configuration
  fraud_threshold      = var.fraud_threshold
  suspicious_threshold = var.suspicious_threshold
  model_version        = var.model_version

  tags = local.common_tags
}

################################################################################
# API Gateway Module
################################################################################

module "api_gateway" {
  source = "./modules/api-gateway"

  name_prefix              = local.name_prefix
  environment              = var.environment
  ingestion_lambda_arn     = module.lambda.ingestion_function_arn
  ingestion_lambda_name    = module.lambda.ingestion_function_name
  query_lambda_arn         = module.lambda.query_function_arn
  query_lambda_name        = module.lambda.query_function_name
  enable_api_key           = var.enable_api_key
  throttle_rate_limit      = var.api_rate_limit
  throttle_burst_limit     = var.api_burst_limit
  enable_access_logging    = true
  access_log_retention_days = var.log_retention_days

  tags = local.common_tags
}

################################################################################
# EMR Module
################################################################################

module "emr" {
  source = "./modules/emr"

  name_prefix             = local.name_prefix
  environment             = var.environment
  vpc_id                  = module.vpc.vpc_id
  subnet_id               = module.vpc.private_subnet_ids[0]
  emr_service_role_arn    = module.iam.emr_service_role_arn
  emr_ec2_role_arn        = module.iam.emr_ec2_role_arn
  emr_instance_profile    = module.iam.emr_instance_profile_name
  emr_autoscaling_role_arn = module.iam.emr_autoscaling_role_arn
  logs_bucket             = module.s3.logs_bucket_name
  scripts_bucket          = module.s3.scripts_bucket_name

  # Batch cluster configuration
  release_label           = var.emr_release_label
  master_instance_type    = var.emr_master_instance_type
  core_instance_type      = var.emr_core_instance_type
  core_instance_count     = var.emr_core_instance_count
  use_spot_instances      = var.emr_use_spot
  spot_bid_percentage     = var.emr_spot_bid_percentage

  # Streaming cluster configuration
  streaming_enabled              = var.streaming_enabled
  streaming_master_instance_type = var.streaming_master_instance_type
  streaming_core_instance_type   = var.streaming_core_instance_type
  streaming_core_instance_count  = var.streaming_core_instance_count

  tags = local.common_tags
}

################################################################################
# Step Functions Module
################################################################################

module "step_functions" {
  source = "./modules/step-functions"

  name_prefix             = local.name_prefix
  sfn_role_arn            = module.iam.step_functions_role_arn
  emr_cluster_config      = module.emr.batch_cluster_config
  orchestration_lambda_arn = module.lambda.orchestration_function_arn
  alert_lambda_arn        = module.lambda.alert_function_arn
  sns_topic_arn           = module.sns.pipeline_notifications_topic_arn
  scripts_bucket          = module.s3.scripts_bucket_name
  raw_bucket              = module.s3.raw_bucket_name
  features_bucket         = module.s3.features_bucket_name
  models_bucket           = module.s3.models_bucket_name
  predictions_bucket      = module.s3.predictions_bucket_name

  tags = local.common_tags
}

################################################################################
# CloudWatch Module
################################################################################

module "cloudwatch" {
  source = "./modules/cloudwatch"

  name_prefix              = local.name_prefix
  environment              = var.environment
  kinesis_stream_name      = module.kinesis.stream_name
  lambda_function_names    = module.lambda.function_names
  api_gateway_name         = module.api_gateway.api_name
  emr_cluster_id           = module.emr.batch_cluster_id
  streaming_cluster_id     = var.streaming_enabled ? module.emr.streaming_cluster_id : null
  alerts_table_name        = module.dynamodb.alerts_table_name
  predictions_table_name   = module.dynamodb.predictions_table_name
  sns_topic_arn            = module.sns.fraud_alerts_topic_arn
  alarm_email              = var.alarm_email
  enable_anomaly_detection = var.environment == "prod"

  # Thresholds
  lambda_error_threshold     = 5
  lambda_duration_threshold  = 30000
  kinesis_iterator_age_threshold = 60000
  emr_step_failure_threshold = 1

  tags = local.common_tags
}
