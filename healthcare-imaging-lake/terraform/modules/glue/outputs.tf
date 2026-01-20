output "database_name" {
  description = "Name of the Glue database"
  value       = aws_glue_catalog_database.main.name
}

output "imaging_table_name" {
  description = "Name of the imaging metadata table"
  value       = aws_glue_catalog_table.imaging.name
}

output "clinical_table_name" {
  description = "Name of the clinical records table"
  value       = aws_glue_catalog_table.clinical.name
}

output "crawler_name" {
  description = "Name of the Glue crawler"
  value       = aws_glue_crawler.metadata.name
}

output "etl_job_name" {
  description = "Name of the Glue ETL job"
  value       = aws_glue_job.etl.name
}
