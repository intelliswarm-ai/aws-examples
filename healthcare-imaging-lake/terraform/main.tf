################################################################################
# Healthcare Imaging Data Lake - Main Terraform Configuration
# HIPAA-compliant infrastructure with Lake Formation fine-grained access control
################################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Compliance  = "HIPAA"
    })
  }
}

################################################################################
# Data Sources
################################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

################################################################################
# Locals
################################################################################

locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  name_prefix = "${var.project_name}-${var.environment}"

  # Bucket names with account ID for uniqueness
  images_bucket_name   = var.images_bucket_name != "" ? var.images_bucket_name : "${local.name_prefix}-images-${local.account_id}"
  metadata_bucket_name = var.metadata_bucket_name != "" ? var.metadata_bucket_name : "${local.name_prefix}-metadata-${local.account_id}"
  results_bucket_name  = var.results_bucket_name != "" ? var.results_bucket_name : "${local.name_prefix}-results-${local.account_id}"

  # Lambda environment variables
  lambda_environment = {
    ENVIRONMENT       = var.environment
    AWS_REGION        = var.aws_region
    IMAGES_BUCKET     = module.s3.images_bucket_name
    METADATA_BUCKET   = module.s3.metadata_bucket_name
    RESULTS_BUCKET    = module.s3.results_bucket_name
    KMS_KEY_ID        = module.kms.key_id
    KMS_KEY_ARN       = module.kms.key_arn
    GLUE_DATABASE     = var.glue_database
    IMAGING_TABLE     = var.imaging_table_name
    CLINICAL_TABLE    = var.clinical_table_name
    ATHENA_WORKGROUP  = var.athena_workgroup
    GLUE_CRAWLER_NAME = "${local.name_prefix}-crawler"
    LOG_LEVEL         = var.log_level
  }
}

################################################################################
# KMS Module - Customer Managed Key for HIPAA Encryption
################################################################################

module "kms" {
  source = "./modules/kms"

  name_prefix         = local.name_prefix
  environment         = var.environment
  enable_key_rotation = true
  deletion_window     = var.kms_deletion_window

  admin_role_arns = var.kms_admin_arns
  usage_role_arns = concat(
    [module.iam.lambda_role_arn],
    [module.iam.glue_role_arn],
    var.kms_usage_arns
  )

  tags = var.tags
}

################################################################################
# S3 Module - Encrypted Storage for Images and Metadata
################################################################################

module "s3" {
  source = "./modules/s3"

  name_prefix          = local.name_prefix
  images_bucket_name   = local.images_bucket_name
  metadata_bucket_name = local.metadata_bucket_name
  results_bucket_name  = local.results_bucket_name

  kms_key_arn = module.kms.key_arn

  enable_versioning     = var.enable_s3_versioning
  enable_access_logging = var.enable_s3_access_logging

  lifecycle_rules = var.s3_lifecycle_rules

  tags = var.tags
}

################################################################################
# IAM Module - Roles and Policies
################################################################################

module "iam" {
  source = "./modules/iam"

  name_prefix = local.name_prefix
  environment = var.environment

  images_bucket_arn   = module.s3.images_bucket_arn
  metadata_bucket_arn = module.s3.metadata_bucket_arn
  results_bucket_arn  = module.s3.results_bucket_arn
  kms_key_arn         = module.kms.key_arn
  glue_database       = var.glue_database

  enable_lakeformation = var.enable_lakeformation

  tags = var.tags
}

################################################################################
# Glue Module - Data Catalog and Crawlers
################################################################################

module "glue" {
  source = "./modules/glue"

  name_prefix = local.name_prefix
  environment = var.environment

  database_name      = var.glue_database
  imaging_table_name = var.imaging_table_name
  clinical_table_name = var.clinical_table_name

  metadata_bucket_name = module.s3.metadata_bucket_name
  glue_role_arn        = module.iam.glue_role_arn

  crawler_schedule = var.glue_crawler_schedule

  tags = var.tags
}

################################################################################
# Lake Formation Module - Fine-Grained Access Control
################################################################################

module "lakeformation" {
  source = "./modules/lakeformation"

  count = var.enable_lakeformation ? 1 : 0

  name_prefix = local.name_prefix

  database_name = var.glue_database
  admin_arns    = var.lakeformation_admin_arns

  images_bucket_arn     = module.s3.images_bucket_arn
  metadata_bucket_arn   = module.s3.metadata_bucket_arn
  lakeformation_role_arn = module.iam.lakeformation_role_arn

  imaging_table_name  = var.imaging_table_name
  clinical_table_name = var.clinical_table_name

  tags = var.tags

  depends_on = [module.glue]
}

################################################################################
# Athena Module - Query Workgroup
################################################################################

module "athena" {
  source = "./modules/athena"

  name_prefix = local.name_prefix
  environment = var.environment

  workgroup_name       = var.athena_workgroup
  results_bucket_name  = module.s3.results_bucket_name
  kms_key_arn          = module.kms.key_arn

  bytes_scanned_cutoff = var.athena_bytes_limit
  query_timeout        = var.athena_query_timeout

  tags = var.tags
}

################################################################################
# Lambda Module - Serverless Functions
################################################################################

module "lambda" {
  source = "./modules/lambda"

  name_prefix = local.name_prefix
  environment = var.environment

  lambda_role_arn  = module.iam.lambda_role_arn
  kms_key_arn      = module.kms.key_arn

  environment_variables = local.lambda_environment

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout
  runtime     = var.lambda_runtime

  # Source code paths
  source_path = "${path.module}/../src"

  tags = var.tags
}

################################################################################
# CloudWatch Module - Monitoring and Logging
################################################################################

module "cloudwatch" {
  source = "./modules/cloudwatch"

  name_prefix = local.name_prefix
  environment = var.environment

  kms_key_arn = module.kms.key_arn

  lambda_function_names = module.lambda.function_names
  glue_job_name         = module.glue.etl_job_name

  alarm_email        = var.alarm_email
  retention_days     = var.log_retention_days
  enable_dashboards  = var.enable_cloudwatch_dashboards

  tags = var.tags
}
