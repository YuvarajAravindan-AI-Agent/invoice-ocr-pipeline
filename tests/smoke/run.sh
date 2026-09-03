#!/usr/bin/env bash
# Post-deploy smoke test, called once per provider after apply in
# .github/workflows/iac-pipeline.yml. Replace with real health-check /
# API-contract calls against the just-deployed service.
#
# Usage: run.sh --provider <name>
set -euo pipefail

provider=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) provider="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "TODO: no smoke tests wired up yet for provider '$provider'" >&2
