output "batch_cluster_id" {
  description = "Batch EMR cluster ID"
  value       = "managed-by-step-functions"
}

output "streaming_cluster_id" {
  description = "Streaming EMR cluster ID"
  value       = var.streaming_enabled ? aws_emr_cluster.streaming[0].id : null
}

output "master_public_dns" {
  description = "Streaming cluster master public DNS"
  value       = var.streaming_enabled ? aws_emr_cluster.streaming[0].master_public_dns : null
}

output "emr_master_security_group_id" {
  description = "EMR master security group ID"
  value       = aws_security_group.emr_master.id
}

output "emr_slave_security_group_id" {
  description = "EMR slave security group ID"
  value       = aws_security_group.emr_slave.id
}

output "batch_cluster_config" {
  description = "Batch cluster configuration for Step Functions"
  value = {
    release_label        = var.release_label
    master_instance_type = var.master_instance_type
    core_instance_type   = var.core_instance_type
    core_instance_count  = var.core_instance_count
    logs_bucket          = var.logs_bucket
    scripts_bucket       = var.scripts_bucket
    subnet_id            = var.subnet_id
    master_sg_id         = aws_security_group.emr_master.id
    slave_sg_id          = aws_security_group.emr_slave.id
    use_spot             = var.use_spot_instances
    spot_bid_percentage  = var.spot_bid_percentage
  }
}
