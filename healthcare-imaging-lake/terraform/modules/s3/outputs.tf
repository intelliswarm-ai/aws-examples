output "images_bucket_name" {
  description = "Name of the images bucket"
  value       = aws_s3_bucket.images.id
}

output "images_bucket_arn" {
  description = "ARN of the images bucket"
  value       = aws_s3_bucket.images.arn
}

output "metadata_bucket_name" {
  description = "Name of the metadata bucket"
  value       = aws_s3_bucket.metadata.id
}

output "metadata_bucket_arn" {
  description = "ARN of the metadata bucket"
  value       = aws_s3_bucket.metadata.arn
}

output "results_bucket_name" {
  description = "Name of the results bucket"
  value       = aws_s3_bucket.results.id
}

output "results_bucket_arn" {
  description = "ARN of the results bucket"
  value       = aws_s3_bucket.results.arn
}
