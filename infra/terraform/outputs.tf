output "entra_tenant_id" {
  description = "Entra tenant ID the API validates tokens against."
  value       = data.azuread_client_config.current.tenant_id
}

output "entra_client_id" {
  description = "API application client ID."
  value       = azuread_application.comments_api.client_id
}

output "entra_api_audience" {
  description = "Entra v2 access-token audience (the API client ID)."
  value       = azuread_application.comments_api.client_id
}

output "entra_api_scope" {
  description = "OAuth scope clients request to obtain an API access token."
  value       = "${azuread_application_identifier_uri.comments_api.identifier_uri}/access_as_user"
}

output "azure_language_endpoint" {
  description = "Azure AI Language endpoint."
  value       = azurerm_cognitive_account.language.endpoint
}

output "azure_workload_identity_client_id" {
  description = "Client ID of the managed identity used by the web app."
  value       = azurerm_user_assigned_identity.comments_api.client_id
}

output "resource_group_name" {
  description = "Resource group containing the Azure resources."
  value       = azurerm_resource_group.comments.name
}

output "web_app_name" {
  description = "Name of the App Service web app."
  value       = azurerm_linux_web_app.api.name
}

output "web_app_url" {
  description = "Public URL of the deployed API."
  value       = "https://${azurerm_linux_web_app.api.default_hostname}"
}