variable "subscription_id" {
  description = "Azure subscription that will contain the resources."
  type        = string
}

variable "location" {
  description = "Azure region (Sweden Central is the closest to Stockholm)."
  type        = string
  default     = "swedencentral"
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

variable "container_image" {
  description = "Docker Hub image (repository:tag) the web app runs. Must be public."
  type        = string
  default     = "lynxelele/comments-api:stable"
}