data "azuread_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

locals {
  resource_suffix = random_string.suffix.result
  language_name   = "${var.name_prefix}-${local.resource_suffix}"
}

resource "azurerm_resource_group" "comments" {
  name     = "${var.name_prefix}-${local.resource_suffix}"
  location = var.location
}

resource "azurerm_virtual_network" "comments" {
  name                = "${var.name_prefix}-vnet-${local.resource_suffix}"
  location            = azurerm_resource_group.comments.location
  resource_group_name = azurerm_resource_group.comments.name
  address_space       = ["10.42.0.0/16"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = "private-endpoints"
  resource_group_name               = azurerm_resource_group.comments.name
  virtual_network_name              = azurerm_virtual_network.comments.name
  address_prefixes                  = ["10.42.1.0/24"]
  private_endpoint_network_policies = "Disabled"
}

resource "azuread_application" "comments_api" {
  display_name     = "${var.name_prefix}-api"
  identifier_uris  = ["api://${random_uuid.api_application_uri.result}"]
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      admin_consent_description  = "Allow the application to create and manage comments as the signed-in user."
      admin_consent_display_name = "Access comments as the signed-in user"
      enabled                    = true
      id                         = random_uuid.api_scope.result
      type                       = "User"
      user_consent_description   = "Allow this application to access comments as you."
      user_consent_display_name  = "Access comments as you"
      value                      = "access_as_user"
    }
  }
}

resource "random_uuid" "api_scope" {}
resource "random_uuid" "api_application_uri" {}

resource "azuread_service_principal" "comments_api" {
  client_id = azuread_application.comments_api.client_id
}

resource "azurerm_cognitive_account" "language" {
  name                  = local.language_name
  location              = azurerm_resource_group.comments.location
  resource_group_name   = azurerm_resource_group.comments.name
  kind                  = "TextAnalytics"
  sku_name              = "S"
  custom_subdomain_name = local.language_name

  local_auth_enabled            = false
  public_network_access_enabled = var.public_network_access_enabled
}

resource "azurerm_private_dns_zone" "language" {
  name                = "privatelink.cognitiveservices.azure.com"
  resource_group_name = azurerm_resource_group.comments.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "language" {
  name                  = "${var.name_prefix}-language-dns-${local.resource_suffix}"
  resource_group_name   = azurerm_resource_group.comments.name
  private_dns_zone_name = azurerm_private_dns_zone.language.name
  virtual_network_id    = azurerm_virtual_network.comments.id
}

resource "azurerm_private_endpoint" "language" {
  name                = "${var.name_prefix}-language-pe-${local.resource_suffix}"
  location            = azurerm_resource_group.comments.location
  resource_group_name = azurerm_resource_group.comments.name
  subnet_id           = azurerm_subnet.private_endpoints.id

  private_service_connection {
    name                           = "${var.name_prefix}-language-connection"
    private_connection_resource_id = azurerm_cognitive_account.language.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "language-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.language.id]
  }
}

resource "azurerm_user_assigned_identity" "comments_api" {
  name                = "${var.name_prefix}-workload-${local.resource_suffix}"
  location            = azurerm_resource_group.comments.location
  resource_group_name = azurerm_resource_group.comments.name
}

resource "azurerm_role_assignment" "language_user" {
  scope                = azurerm_cognitive_account.language.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.comments_api.principal_id
  principal_type       = "ServicePrincipal"
}