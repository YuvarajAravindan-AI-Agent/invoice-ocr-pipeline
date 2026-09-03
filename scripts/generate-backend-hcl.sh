#!/usr/bin/env bash
# Turns the `backend:` block for one provider (extracted from
# deploy/provider-matrix.yaml as JSON) into a backend-config HCL file
# that `tofu init -backend-config=<file>` can consume.
#
# Usage: generate-backend-hcl.sh <backend.json> <output.hcl>
set -euo pipefail

input="${1:?input backend json required}"
output="${2:?output hcl path required}"

if [[ "$(jq -r 'type' "$input")" == "null" ]]; then
  echo "no backend block for this provider — skipping" >&2
  : > "$output"
  exit 0
fi

jq -r 'to_entries[] | select(.key != "type") | "\(.key) = \"\(.value)\""' "$input" > "$output"
