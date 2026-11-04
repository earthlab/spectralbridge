# RC2 preparation evidence - 2026-11-04

Read the repository-root `RC2_RELEASE_READINESS.md` for the decision, scope,
commands, exceptions and exact remaining maintainer actions. No remote release,
publication, merge or tag was performed. Current preparation edits are on
`codex/prepare-2.3.0rc2`, uncommitted for review.

- `release-baseline.json`, branch/tag/history text and `integration-history.json`:
  source comparison against the October 13 RC1 preparation (not a release tag).
- `source-tests.xml`, `source-test-summary.json`: 946 pass / 9 documented skips.
- Browser and full-mode polygon XML: 2 and 4 additional passing cases.
- `offline-campaign.json`: 40 fresh deterministic software checks, not physical validation.
- `neon-regression.json`, control models and `neon_control.py`: fixed real NEON
  data, new scratch path, exact equality to the prior two 3.6-million-value outputs.
- `runtime-payload-parity.json`: final wheel and sdist share 143 identical runtime files.
- `candidate-revision.json` and candidate-1 checksum/audit records: first sdist retired for the corrected release-helper default; the original wheel is unchanged.
- `distribution-audit.json`, `SHA256SUMS`, `source-manifest.json`: exact local
  candidate bytes, build inputs, package contents and source freeze.
- `installed-artifact-results.json`: the same wheel on Python 3.10/3.11/3.12 and
  the sdist on separate Python 3.10, all outside checkout with network blocked.
- Installed optional XML: 40 existing regressions, with tiny fixture/example
  files copied outside checkout; only the built wheel provides package code.
- Environment freeze files record base environments separately from later extras.
- `preserved-provenance.json`: 3,220 prior tracked research evidence files match
  baseline bytes. Prompt/work-queue logs are the only authorized exceptions.
- Build/docs/CLI/test logs retain exact output, warnings and scope.

The local artifacts are in Git-ignored
`archive/local/release-rc2/2026-11-04/dist/`. Run
`python provenance/release-rc2/2026-11-04/audit_distributions.py` to recheck those
bytes without rebuilding. This directory contains compact evidence; it is pruned
from installation payloads. The approved hosted release workflow must validate
and publish its own single immutable candidate, preserving its checksums; never
substitute an untested rebuild for either candidate.

Citation authorship and actual trusted-publisher/environment protections remain
maintainer decisions, not facts inferred by this preparation. Physical drone
calibration and true contributor uncertainties remain documented research scope,
not release-blocking software defects.
