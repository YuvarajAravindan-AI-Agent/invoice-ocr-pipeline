# Common input contract every provider adapter under iac/opentofu/<provider>
# must accept. Keep this shape identical across providers so the pipeline
# and any future codegen from blueprint/platform.yaml can call every
# adapter the same way — provider-specific values (SKU names, machine
# types, etc.) come from blueprint/environments/<env>.yaml, not from new
# variables invented per-provider.
#
# When this repo has a second consumer, promote this module to the
# platform-opentofu-modules repo and source it by git ref instead of
# copying it per service.

variable "service_name" {
  type        = string
  description = "Matches application.name in blueprint/platform.yaml"
}

variable "environment" {
  type        = string
  description = "dev, prod, etc. — matches blueprint/environments/<env>.yaml"
}

variable "region" {
  type        = string
  description = "Provider-specific region identifier"
}

variable "image" {
  type        = string
  description = "OCI image reference for the service"
}

variable "cpu" {
  type        = number
  description = "vCPU count — from blueprint compute.cpu"
}

variable "memory_gib" {
  type        = number
  description = "Memory in GiB — from blueprint compute.memory_gib"
}

variable "replicas" {
  type        = number
  description = "Instance/replica count — from blueprint compute.replicas"
}

variable "database_url" {
  type        = string
  description = "Connection string for the relational database, if the blueprint declares one"
  default     = null
  sensitive   = true
}

variable "labels" {
  type        = map(string)
  description = "Common resource labels/tags applied by every adapter"
  default     = {}
}
