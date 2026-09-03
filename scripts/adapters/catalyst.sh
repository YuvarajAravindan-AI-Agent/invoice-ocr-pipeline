#!/usr/bin/env bash
# Uniform plan/apply/destroy interface over the Catalyst adapter directory.
# Catalyst has no OpenTofu/Terraform provider, so this wraps catalyst-cli
# to expose the same three verbs the OpenTofu adapters use.
#
# Grounded against the current Catalyst CLI docs (docs.catalyst.zoho.com,
# checked 2026-09-03) — corrects an earlier version of this script that
# guessed at flags. Known-real commands/flags used below:
#   catalyst whoami                                    (auth check)
#   catalyst deploy --only <targets> [--token/-p/--dc]  (apply)
#   catalyst deploy --except <targets>
#   catalyst functions:delete <function_name_or_id>     (destroy, functions only)
#   global flags: -p/--project, --org, --token, --dc, --verbose
# Source: https://docs.catalyst.zoho.com/en/cli/v1/cli-command-reference/
#         https://docs.catalyst.zoho.com/en/cli/v1/deploy-resources/deploy-options/
#
# IMPORTANT GAP — read before trusting the "plan" step below:
# The Catalyst CLI has no dry-run/plan/preview flag (confirmed absent
# from the deploy-options reference). There is no way to get a `tofu
# plan`-equivalent diff before deploying. "plan" here can only do local
# structural validation — the actual review evidence for a Catalyst
# change is the PR diff of the config files themselves, not a generated
# plan. Don't present this script's plan output as equivalent to an
# OpenTofu plan in release evidence (§10) — call out the difference.
#
# Also gapped: there is no documented `appsail:delete` command. destroy
# below can only remove Functions via the CLI; AppSail services must be
# deleted through the Catalyst console until/unless that command exists.
#
# Usage: catalyst.sh <plan|apply|destroy> <workdir>
# Env:   CATALYST_CI_TOKEN       (required — passed as --token)
#        CATALYST_PROJECT        (required — passed as -p)
#        CATALYST_DC             (optional — passed as --dc, e.g. "in")
#        CATALYST_DEPLOY_TARGETS (required for apply — comma list, e.g.
#                                  "appsail:api,appsail:worker")
set -euo pipefail

action="${1:?action required: plan|apply|destroy}"
workdir="${2:?workdir required}"

cd "$workdir"

: "${CATALYST_CI_TOKEN:?CATALYST_CI_TOKEN env var required}"
: "${CATALYST_PROJECT:?CATALYST_PROJECT env var required}"

common_flags=(--token "$CATALYST_CI_TOKEN" -p "$CATALYST_PROJECT")
if [[ -n "${CATALYST_DC:-}" ]]; then
  common_flags+=(--dc "$CATALYST_DC")
fi

require_login() {
  if ! catalyst whoami "${common_flags[@]}" >/dev/null 2>&1; then
    echo "catalyst-cli could not authenticate with the supplied token/project" >&2
    exit 1
  fi
}

case "$action" in
  plan)
    require_login
    echo "No dry-run exists in the Catalyst CLI — validating local config only." >&2
    for required_file in catalyst.json; do
      if [[ ! -f "$required_file" ]]; then
        echo "missing required file: $required_file" >&2
        exit 1
      fi
    done
    echo "Local config present. Review the actual change via this PR's diff of catalyst.json / app-config.json / functions/*/catalyst-config.json — there is no generated plan output for Catalyst." >&2
    ;;
  apply)
    require_login
    : "${CATALYST_DEPLOY_TARGETS:?CATALYST_DEPLOY_TARGETS env var required, e.g. appsail:api,appsail:worker}"
    catalyst deploy --only "$CATALYST_DEPLOY_TARGETS" "${common_flags[@]}"
    ;;
  destroy)
    require_login
    : "${CATALYST_DEPLOY_TARGETS:?CATALYST_DEPLOY_TARGETS env var required}"
    IFS=',' read -ra targets <<< "$CATALYST_DEPLOY_TARGETS"
    for target in "${targets[@]}"; do
      if [[ "$target" == functions:* ]]; then
        catalyst functions:delete "${target#functions:}" "${common_flags[@]}"
      else
        echo "no CLI delete command exists for '$target' (e.g. appsail) — remove it via the Catalyst console" >&2
      fi
    done
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 1
    ;;
esac
