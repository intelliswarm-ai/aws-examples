output "state_machine_arn" {
  description = "State machine ARN"
  value       = aws_sfn_state_machine.pipeline.arn
}

output "state_machine_name" {
  description = "State machine name"
  value       = aws_sfn_state_machine.pipeline.name
}

output "state_machine_id" {
  description = "State machine ID"
  value       = aws_sfn_state_machine.pipeline.id
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.sfn.name
}
