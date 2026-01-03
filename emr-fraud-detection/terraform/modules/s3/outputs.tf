output "raw_bucket_name" {
  description = "Raw data bucket name"
  value       = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  description = "Raw data bucket ARN"
  value       = aws_s3_bucket.raw.arn
}

output "features_bucket_name" {
  description = "Features bucket name"
  value       = aws_s3_bucket.features.id
}

output "features_bucket_arn" {
  description = "Features bucket ARN"
  value       = aws_s3_bucket.features.arn
}

output "models_bucket_name" {
  description = "Models bucket name"
  value       = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  description = "Models bucket ARN"
  value       = aws_s3_bucket.models.arn
}

output "predictions_bucket_name" {
  description = "Predictions bucket name"
  value       = aws_s3_bucket.predictions.id
}

output "predictions_bucket_arn" {
  description = "Predictions bucket ARN"
  value       = aws_s3_bucket.predictions.arn
}

output "scripts_bucket_name" {
  description = "Scripts bucket name"
  value       = aws_s3_bucket.scripts.id
}

output "scripts_bucket_arn" {
  description = "Scripts bucket ARN"
  value       = aws_s3_bucket.scripts.arn
}

output "logs_bucket_name" {
  description = "Logs bucket name"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "Logs bucket ARN"
  value       = aws_s3_bucket.logs.arn
}
