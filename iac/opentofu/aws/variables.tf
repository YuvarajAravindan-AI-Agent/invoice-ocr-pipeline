# Mirrors ../modules/common/variables.tf — kept as a real variables.tf
# here (rather than only referencing the module) so `tofu plan` in this
# directory is self-contained and can be var-file'd directly by
# scripts/adapters/opentofu.sh.

variable "service_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "image" { type = string }
variable "cpu" { type = number }
variable "memory_gib" { type = number }
variable "replicas" { type = number }
variable "database_url" {
  type      = string
  default   = null
  sensitive = true
}
variable "labels" {
  type    = map(string)
  default = {}
}
