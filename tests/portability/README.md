# tests/portability

Periodic drills, not CI-on-every-PR: deploy the same container to a
second provider, run the same contract tests, restore a database export,
and diff the result against the primary (Catalyst) deployment. See §10
and §12 ("false portability confidence") of the architecture doc — the
point of this suite is to catch drift between "looks portable" and "is
portable" before an actual migration is forced.

Nothing implemented yet. Suggested first drill: deploy to Catalyst and
one OpenTofu adapter, run tests/contract and tests/smoke against both,
diff.
