variable "subscription_id" {
  description = "Azure subscription that will contain the Language resource."
  type        = string
}

variable "location" {
  description = "Azure region for the resource group and Language resource."
  type        = string
  default     = "eastus"
}

variable "name_prefix" {
  description = "Lowercase prefix used for Azure resource names."
  type        = string
  default     = "comments-api"

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,18}[a-z0-9])?$", var.name_prefix))
    error_message = "name_prefix must start and end with a lowercase letter or digit and contain at most 20 lowercase letters, digits, or hyphens."
  }
}

variable "public_network_access_enabled" {
  description = "Allow public network access to Azure Language. Keep disabled for workloads attached to the provisioned private network."
  type        = bool
  default     = false
}