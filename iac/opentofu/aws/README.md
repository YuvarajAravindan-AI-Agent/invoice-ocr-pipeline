# iac/opentofu/aws

Copy 2 (one of several) — the aws implementation of the common
variable contract in `../modules/common`. Not yet implemented.

Typical resources for this provider's `linux_http_service` /
`relational_database` / `object_storage` / `secret_store`
capabilities: aws_ecs_service / aws_lambda_function, aws_s3_bucket, aws_db_instance, aws_iam_role.

Must accept exactly the variables in
`../modules/common/variables.tf` and expose the outputs in
`../modules/common/outputs.tf` — that uniformity is what lets
`scripts/adapters/opentofu.sh` and the CI pipeline treat every
provider identically.
