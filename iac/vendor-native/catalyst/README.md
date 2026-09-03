# iac/vendor-native/catalyst

Copy 1 — the Catalyst-specific implementation. No OpenTofu here; this is
driven by `catalyst-cli` via `../../../scripts/adapters/catalyst.sh`.

Expected contents once implemented:

- `catalyst-config.json` (or `.catalystrc`) — the actual Catalyst
  project/environment configuration.
- `functions/`, `appsail/`, etc. — Catalyst service definitions,
  structured however `catalyst-cli` expects for this project type.

Map every value here back to a requirement in
`../../../blueprint/platform.yaml` — if a Catalyst service doesn't
correspond to a contract capability, it's a Tier 3 (proprietary)
decision per `docs/provider-matrix.md` and should be recorded there,
not left implicit.
