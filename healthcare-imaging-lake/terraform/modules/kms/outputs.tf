output "key_id" {
  description = "KMS key ID"
  value       = aws_kms_key.main.key_id
}

output "key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.main.arn
}

output "alias_name" {
  description = "KMS key alias"
  value       = aws_kms_alias.main.name
}

output "alias_arn" {
  description = "KMS alias ARN"
  value       = aws_kms_alias.main.arn
}
