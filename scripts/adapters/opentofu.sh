#!/usr/bin/env bash
# Uniform plan/apply/destroy interface over an OpenTofu adapter directory.
# Called identically for aws/azure/gcp/alibaba/<new-cloud> — the only
# per-provider differences live inside iac/<provider>/*.tf and the
# backend config file generated from deploy/provider-matrix.yaml.
#
# Usage: opentofu.sh <plan|apply|destroy> <workdir> <backend-config-file> [var-file]
set -euo pipefail

action="${1:?action required: plan|apply|destroy}"
workdir="${2:?workdir required}"
backend_config="${3:?backend config file required}"
var_file="${4:-}"

cd "$workdir"

tofu init -backend-config="$backend_config" -input=false

tofu fmt -check -recursive
tofu validate

var_args=()
if [[ -n "$var_file" && -f "$var_file" ]]; then
  var_args=(-var-file="$var_file")
fi

case "$action" in
  plan)
    tofu plan -input=false -out=tfplan "${var_args[@]}"
    ;;
  apply)
    if [[ -f tfplan ]]; then
      tofu apply -input=false -auto-approve tfplan
    else
      tofu apply -input=false -auto-approve "${var_args[@]}"
    fi
    ;;
  destroy)
    tofu destroy -input=false -auto-approve "${var_args[@]}"
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 1
    ;;
esac
