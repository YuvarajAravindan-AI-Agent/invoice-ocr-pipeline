# iac/opentofu/alibaba

Copy 2 (one of several) — the alibaba implementation of the common
variable contract in `../modules/common`. Not yet implemented.

Typical resources for this provider's `linux_http_service` /
`relational_database` / `object_storage` / `secret_store`
capabilities: alicloud_ecs_instance / alicloud_fc_function, alicloud_oss_bucket, alicloud_db_instance, alicloud_kms_key.

Must accept exactly the variables in
`../modules/common/variables.tf` and expose the outputs in
`../modules/common/outputs.tf` — that uniformity is what lets
`scripts/adapters/opentofu.sh` and the CI pipeline treat every
provider identically.
