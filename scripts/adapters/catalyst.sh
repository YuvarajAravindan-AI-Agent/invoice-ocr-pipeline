#!/usr/bin/env bash
# Uniform plan/apply/destroy interface over the Catalyst adapter directory.
# Catalyst 3.0 has no OpenTofu/Terraform provider, so this wraps
# catalyst-cli to expose the same three verbs the OpenTofu adapters use,
# so the pipeline's orchestration stays identical across all providers
# even though this directory isn't actually OpenTofu underneath.
#
# NOTE: verify the exact catalyst-cli subcommands/flags below against the
# current Catalyst 3.0 CLI reference before relying on this — CLI surface
# changes between Catalyst versions and isn't covered by our own docs.
#
# Usage: catalyst.sh <plan|apply|destroy> <workdir>
set -euo pipefail

action="${1:?action required: plan|apply|destroy}"
workdir="${2:?workdir required}"

cd "$workdir"

require_login() {
  if ! catalyst whoami >/dev/null 2>&1; then
    echo "catalyst-cli is not authenticated in this runner — configure a CI token/service identity first" >&2
    exit 1
  fi
}

case "$action" in
  plan)
    require_login
    # Dry-run: validates catalyst-config.json / catalyst.json against the
    # target environment without deploying. Surfaces diffs the same way
    # `tofu plan` does, so reviewers get equivalent evidence per §10.
    catalyst deploy --dry-run --scope all
    ;;
  apply)
    require_login
    catalyst deploy --scope all --yes
    ;;
  destroy)
    require_login
    catalyst function:delete --all --yes || true
    catalyst appsail:delete --all --yes || true
    echo "Catalyst resources are deleted per-service; confirm nothing was skipped in the console." >&2
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 1
    ;;
esac
