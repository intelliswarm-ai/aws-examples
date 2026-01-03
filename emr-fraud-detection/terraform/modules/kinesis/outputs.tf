output "stream_name" {
  description = "Kinesis stream name"
  value       = aws_kinesis_stream.transactions.name
}

output "stream_arn" {
  description = "Kinesis stream ARN"
  value       = aws_kinesis_stream.transactions.arn
}

output "shard_count" {
  description = "Number of shards"
  value       = aws_kinesis_stream.transactions.shard_count
}
