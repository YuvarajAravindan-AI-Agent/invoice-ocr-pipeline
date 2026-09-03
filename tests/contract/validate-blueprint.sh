#!/usr/bin/env bash
# Validates blueprint/platform.yaml against the neutral contract schema
# (see docs/architecture.md §4). Once platform-contracts exists, this
# should pull the pinned schema version from there instead of checking
# structure ad hoc.
#
# Usage: validate-blueprint.sh <blueprint.yaml>
set -euo pipefail

blueprint="${1:?path to blueprint yaml required}"

if [[ ! -f "$blueprint" ]]; then
  echo "blueprint file not found: $blueprint" >&2
  exit 1
fi

for key in application compute network operations; do
  if ! yq -e ".$key" "$blueprint" >/dev/null 2>&1; then
    echo "blueprint is missing required top-level key: $key" >&2
    exit 1
  fi
done

echo "blueprint contract check passed: $blueprint"
