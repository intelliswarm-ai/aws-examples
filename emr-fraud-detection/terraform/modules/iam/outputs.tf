output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.lambda.name
}

output "emr_service_role_arn" {
  description = "EMR service role ARN"
  value       = aws_iam_role.emr_service.arn
}

output "emr_service_role_name" {
  description = "EMR service role name"
  value       = aws_iam_role.emr_service.name
}

output "emr_ec2_role_arn" {
  description = "EMR EC2 role ARN"
  value       = aws_iam_role.emr_ec2.arn
}

output "emr_ec2_role_name" {
  description = "EMR EC2 role name"
  value       = aws_iam_role.emr_ec2.name
}

output "emr_instance_profile_name" {
  description = "EMR EC2 instance profile name"
  value       = aws_iam_instance_profile.emr_ec2.name
}

output "emr_instance_profile_arn" {
  description = "EMR EC2 instance profile ARN"
  value       = aws_iam_instance_profile.emr_ec2.arn
}

output "emr_autoscaling_role_arn" {
  description = "EMR autoscaling role ARN"
  value       = aws_iam_role.emr_autoscaling.arn
}

output "step_functions_role_arn" {
  description = "Step Functions role ARN"
  value       = aws_iam_role.step_functions.arn
}

output "step_functions_role_name" {
  description = "Step Functions role name"
  value       = aws_iam_role.step_functions.name
}
