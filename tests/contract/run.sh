#!/usr/bin/env bash
# App-level unit test entrypoint, called by the quality-gates job in
# .github/workflows/iac-pipeline.yml.
set -euo pipefail

cd "$(dirname "$0")/../.."
pip install --quiet -r tests/requirements.txt
pytest tests/unit
