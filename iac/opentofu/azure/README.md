# iac/opentofu/azure

Copy 2 (one of several) — the azure implementation of the common
variable contract in `../modules/common`. Not yet implemented.

Typical resources for this provider's `linux_http_service` /
`relational_database` / `object_storage` / `secret_store`
capabilities: azurerm_container_app, azurerm_storage_account, azurerm_postgresql_flexible_server, azurerm_key_vault.

Must accept exactly the variables in
`../modules/common/variables.tf` and expose the outputs in
`../modules/common/outputs.tf` — that uniformity is what lets
`scripts/adapters/opentofu.sh` and the CI pipeline treat every
provider identically.
