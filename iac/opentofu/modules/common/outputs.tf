# Common output contract — every provider adapter should expose these so
# tests/smoke/run.sh and tests/portability/ can assert against a
# provider-neutral shape.

output "service_url" {
  description = "Public HTTPS endpoint for the deployed service"
  value       = null # each provider module overrides this
}

output "database_endpoint" {
  description = "Reachable endpoint for the relational database, if provisioned"
  value       = null
}
