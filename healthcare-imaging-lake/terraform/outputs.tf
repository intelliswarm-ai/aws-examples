################################################################################
# Healthcare Imaging Data Lake - Terraform Outputs
################################################################################

################################################################################
# S3 Outputs
################################################################################

output "images_bucket_name" {
  description = "Name of the images S3 bucket"
  value       = module.s3.images_bucket_name
}

output "images_bucket_arn" {
  description = "ARN of the images S3 bucket"
  value       = module.s3.images_bucket_arn
}

output "metadata_bucket_name" {
  description = "Name of the metadata S3 bucket"
  value       = module.s3.metadata_bucket_name
}

output "metadata_bucket_arn" {
  description = "ARN of the metadata S3 bucket"
  value       = module.s3.metadata_bucket_arn
}

output "results_bucket_name" {
  description = "Name of the query results S3 bucket"
  value       = module.s3.results_bucket_name
}

################################################################################
# KMS Outputs
################################################################################

output "kms_key_id" {
  description = "ID of the KMS key"
  value       = module.kms.key_id
}

output "kms_key_arn" {
  description = "ARN of the KMS key"
  value       = module.kms.key_arn
  sensitive   = true
}

################################################################################
# Glue Outputs
################################################################################

output "glue_database_name" {
  description = "Name of the Glue database"
  value       = module.glue.database_name
}

output "imaging_table_name" {
  description = "Name of the imaging metadata table"
  value       = module.glue.imaging_table_name
}

output "clinical_table_name" {
  description = "Name of the clinical records table"
  value       = module.glue.clinical_table_name
}

output "glue_crawler_name" {
  description = "Name of the Glue crawler"
  value       = module.glue.crawler_name
}

output "glue_etl_job_name" {
  description = "Name of the Glue ETL job"
  value       = module.glue.etl_job_name
}

################################################################################
# Athena Outputs
################################################################################

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = module.athena.workgroup_name
}

output "athena_output_location" {
  description = "S3 location for Athena query results"
  value       = module.athena.output_location
}

################################################################################
# Lambda Outputs
################################################################################

output "api_handler_arn" {
  description = "ARN of the API handler Lambda function"
  value       = module.lambda.api_handler_arn
}

output "ingestion_handler_arn" {
  description = "ARN of the ingestion handler Lambda function"
  value       = module.lambda.ingestion_handler_arn
}

output "catalog_handler_arn" {
  description = "ARN of the catalog handler Lambda function"
  value       = module.lambda.catalog_handler_arn
}

output "query_handler_arn" {
  description = "ARN of the query handler Lambda function"
  value       = module.lambda.query_handler_arn
}

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value       = module.lambda.function_names
}

################################################################################
# IAM Outputs
################################################################################

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = module.iam.lambda_role_arn
}

output "glue_role_arn" {
  description = "ARN of the Glue service role"
  value       = module.iam.glue_role_arn
}

################################################################################
# Lake Formation Outputs
################################################################################

output "lakeformation_enabled" {
  description = "Whether Lake Formation is enabled"
  value       = var.enable_lakeformation
}

################################################################################
# CloudWatch Outputs
################################################################################

output "log_group_names" {
  description = "Names of CloudWatch log groups"
  value       = module.cloudwatch.log_group_names
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = module.cloudwatch.dashboard_name
}

################################################################################
# Configuration Export
################################################################################

output "environment_config" {
  description = "Environment configuration for Lambda functions"
  value = {
    ENVIRONMENT       = var.environment
    AWS_REGION        = var.aws_region
    IMAGES_BUCKET     = module.s3.images_bucket_name
    METADATA_BUCKET   = module.s3.metadata_bucket_name
    RESULTS_BUCKET    = module.s3.results_bucket_name
    KMS_KEY_ID        = module.kms.key_id
    GLUE_DATABASE     = var.glue_database
    IMAGING_TABLE     = var.imaging_table_name
    CLINICAL_TABLE    = var.clinical_table_name
    ATHENA_WORKGROUP  = var.athena_workgroup
  }
  sensitive = true
}
