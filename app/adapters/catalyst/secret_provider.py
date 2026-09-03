"""SecretProvider implemented against AppSail environment variables.

Per the original architecture doc's service-mapping table: "Secrets |
Catalyst environment/config facilities" — Catalyst doesn't have a
separate secret-manager SDK component (see the Python SDK component
list in iac/vendor-native/catalyst/README.md), so env vars set in each
service's app-config.json are the mechanism. Only environment variable
*names* belong in Git, never values — see docs/architecture.md.
"""

from __future__ import annotations

import os


class CatalystEnvSecretProvider:
    def get(self, name: str) -> str:
        try:
            return os.environ[name]
        except KeyError as exc:
            raise KeyError(f"secret '{name}' not set in this AppSail service's environment") from exc
