output "data_lake_settings" {
  description = "Lake Formation data lake settings"
  value       = aws_lakeformation_data_lake_settings.main.admins
}

output "researcher_imaging_filter" {
  description = "Name of the researcher filter for imaging table"
  value       = aws_lakeformation_data_cells_filter.researcher_imaging.table_data[0].name
}

output "researcher_clinical_filter" {
  description = "Name of the researcher filter for clinical table"
  value       = aws_lakeformation_data_cells_filter.researcher_clinical.table_data[0].name
}
