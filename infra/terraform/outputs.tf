output "entra_tenant_id" {
  description = "Set ENTRA_TENANT_ID for the API."
  value       = data.azuread_client_config.current.tenant_id
}

output "entra_client_id" {
  description = "Set ENTRA_CLIENT_ID to this API application client ID."
  value       = azuread_application.comments_api.client_id
}

output "entra_api_audience" {
  description = "Set ENTRA_API_AUDIENCE to this API client ID (Entra v2 access-token audience)."
  value       = azuread_application.comments_api.client_id
}

output "entra_api_scope" {
  description = "OAuth scope clients request to obtain an API access token."
  value       = "${one(azuread_application.comments_api.identifier_uris)}/access_as_user"
}

output "azure_language_endpoint" {
  description = "Set AZURE_LANGUAGE_ENDPOINT for Azure AI Language."
  value       = azurerm_cognitive_account.language.endpoint
}

output "azure_workload_identity_client_id" {
  description = "Set AZURE_CLIENT_ID and attach this identity to the API workload."
  value       = azurerm_user_assigned_identity.comments_api.client_id
}

output "azure_workload_identity_principal_id" {
  description = "Principal ID of the managed identity granted access to Azure Language."
  value       = azurerm_user_assigned_identity.comments_api.principal_id
}

output "azure_private_vnet_id" {
  description = "Attach the API workload to this VNet to access Azure Language privately."
  value       = azurerm_virtual_network.comments.id
}

output "azure_private_endpoint_subnet_id" {
  description = "Subnet reserved for Azure private endpoints."
  value       = azurerm_subnet.private_endpoints.id
}