data "azuread_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

locals {
  resource_suffix     = random_string.suffix.result
  language_name       = "${var.name_prefix}-${local.resource_suffix}"
  api_scope_id        = "6f1d3c2a-8b4e-4a7d-9c15-2e7b5a9d4f60"
  azure_cli_client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
}

resource "azurerm_resource_group" "comments" {
  name     = "${var.name_prefix}-${local.resource_suffix}"
  location = var.location
}

resource "azuread_application" "comments_api" {
  display_name     = "${var.name_prefix}-api"
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      admin_consent_description  = "Allow the application to create and manage comments as the signed-in user."
      admin_consent_display_name = "Access comments as the signed-in user"
      enabled                    = true
      id                         = local.api_scope_id
      type                       = "User"
      user_consent_description   = "Allow this application to access comments as you."
      user_consent_display_name  = "Access comments as you"
      value                      = "access_as_user"
    }
  }

  lifecycle {
    ignore_changes = [identifier_uris]
  }
}

resource "azuread_application_identifier_uri" "comments_api" {
  application_id = azuread_application.comments_api.id
  identifier_uri = "api://${azuread_application.comments_api.client_id}"
}

resource "azuread_service_principal" "comments_api" {
  client_id = azuread_application.comments_api.client_id
}

resource "azuread_application_pre_authorized" "azure_cli" {
  application_id       = azuread_application.comments_api.id
  authorized_client_id = local.azure_cli_client_id
  permission_ids       = [local.api_scope_id]
}

resource "azurerm_cognitive_account" "language" {
  name                  = local.language_name
  location              = azurerm_resource_group.comments.location
  resource_group_name   = azurerm_resource_group.comments.name
  kind                  = "TextAnalytics"
  sku_name              = "S"
  custom_subdomain_name = local.language_name

  local_auth_enabled            = false
  public_network_access_enabled = true
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

resource "azurerm_service_plan" "comments" {
  name                = "${var.name_prefix}-plan-${local.resource_suffix}"
  location            = azurerm_resource_group.comments.location
  resource_group_name = azurerm_resource_group.comments.name
  os_type             = "Linux"
  sku_name            = "B1"
}

resource "azurerm_linux_web_app" "api" {
  name                = "${var.name_prefix}-${local.resource_suffix}"
  location            = azurerm_resource_group.comments.location
  resource_group_name = azurerm_resource_group.comments.name
  service_plan_id     = azurerm_service_plan.comments.id
  https_only          = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.comments_api.id]
  }

  site_config {
    always_on = true

    application_stack {
      docker_image_name   = var.container_image
      docker_registry_url = "https://index.docker.io"
    }
  }

  app_settings = {
    WEBSITES_PORT                       = "8000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    WEBSITES_CONTAINER_START_TIME_LIMIT = "600"

    DB_DRIVER          = "mysql+pymysql"
    DB_HOST            = azurerm_mysql_flexible_server.comments.fqdn
    DB_PORT            = "3306"
    DB_USERNAME        = azurerm_mysql_flexible_server.comments.administrator_login
    DB_PASSWORD        = random_password.db.result
    DB_DATABASE        = azurerm_mysql_flexible_database.comments.name
    DB_MIGRATIONS_PATH = "/app/app/sql"
    DB_RUN_MIGRATIONS  = "true"

    SERVICE_HOST   = "0.0.0.0"
    SERVICE_PORT   = "8000"
    API_URL_PREFIX = "/comments"
    API_TAGS       = "comments"

    APPLICATION_AUTHORITY    = "https://login.microsoftonline.com"
    APPLICATION_TENANT_ID    = data.azuread_client_config.current.tenant_id
    APPLICATION_CLIENT_ID    = azuread_application.comments_api.client_id
    APPLICATION_API_AUDIENCE = azuread_application.comments_api.client_id
    APPLICATION_API_SCOPE    = "access_as_user"

    AZURE_LANGUAGE_ENDPOINT = azurerm_cognitive_account.language.endpoint
    AZURE_CLIENT_ID         = azurerm_user_assigned_identity.comments_api.client_id
  }

  depends_on = [azurerm_role_assignment.language_user]
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "azurerm_mysql_flexible_server" "comments" {
  name                   = "${var.name_prefix}-db-${local.resource_suffix}"
  resource_group_name    = azurerm_resource_group.comments.name
  location               = azurerm_resource_group.comments.location
  administrator_login    = "commentsadmin"
  administrator_password = random_password.db.result
  sku_name               = "B_Standard_B1ms"
  version                = "8.0.21"

  storage {
    size_gb = 20
  }
}

resource "azurerm_mysql_flexible_database" "comments" {
  name                = "comments"
  resource_group_name = azurerm_resource_group.comments.name
  server_name         = azurerm_mysql_flexible_server.comments.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

resource "azurerm_mysql_flexible_server_firewall_rule" "azure_services" {
  name                = "allow-azure-services"
  resource_group_name = azurerm_resource_group.comments.name
  server_name         = azurerm_mysql_flexible_server.comments.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

resource "azurerm_mysql_flexible_server_configuration" "secure_transport" {
  name                = "require_secure_transport"
  resource_group_name = azurerm_resource_group.comments.name
  server_name         = azurerm_mysql_flexible_server.comments.name
  value               = "OFF"
}