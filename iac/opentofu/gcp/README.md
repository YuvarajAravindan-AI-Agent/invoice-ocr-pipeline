# iac/opentofu/gcp

Copy 2 (one of several) — the gcp implementation of the common
variable contract in `../modules/common`. Not yet implemented.

Typical resources for this provider's `linux_http_service` /
`relational_database` / `object_storage` / `secret_store`
capabilities: google_cloud_run_v2_service, google_storage_bucket, google_sql_database_instance, google_secret_manager_secret.

Must accept exactly the variables in
`../modules/common/variables.tf` and expose the outputs in
`../modules/common/outputs.tf` — that uniformity is what lets
`scripts/adapters/opentofu.sh` and the CI pipeline treat every
provider identically.
