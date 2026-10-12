# JOSS cleanup migration plan

Audit boundary: HEAD `b105c2e7a57e7d33466a649a0e993c6497b733ff`, 12 October 2026.
The inventory covers 689 tracked files plus local/untracked artifacts (705 total),
87 Markdown documentation pages, all seven workflows and package/test configuration.
Reference lists are text mentions, not proof that a path is safe to remove.

## Safe changes

1. Move canonical `drafts/joss` manuscript Markdown, BibTeX and figure assets to
   `paper/`. Classify PDFs/extracted source records as immutable `paper/archive/`,
   renders/DOCX/check outputs as `paper/generated/`. Keep all supplied bytes.
   Generated website assets remain committed deliberately for offline builds;
   they are derived from canonical paper sources, never independent edit targets.
2. Move named historical campaign notebooks, supplied bulk bundle, root polygon
   layers and forensic report/PDF to descriptive archive/provenance locations.
   Preserve all notebook cells, recorded output and source snapshots. Keep active
   Drone/Raster notebook interfaces and tested transfer-module interfaces until
   their callers are migrated; archive large files with explicit working-directory
   conventions and compatibility paths where necessary.
3. Preserve the prompt log under provenance with its old root interface retained
   as a symlink. Keep FEATURE_REQUESTS.md and HYTOOLS_PROVENANCE.md at stable paths
   because agent/release/attribution interfaces explicitly depend on them.
4. Retain deprecated/vendor source and historic data rather than imply that
   external notebook users and pinned manuscript URLs no longer need them.
5. Replace the committed Linux-only gocmd executable with a portable launcher
   over installed GoCommands; preserve the exact original locally with checksum.
   Keep CyVerse arguments/authentication behavior and test forwarding; install
   guidance points to the official CyVerse platform-specific distribution.
6. Move all 16 unreferenced literature PDFs out of docs to an ignored local reading
   archive. None is required for the build. Keep bibliography/DOI links and a
   per-file rights-evidence inventory. Do not assert legal redistribution rights.
7. Fix test HDF5 fixtures to use the actual in-memory driver with backing store
   disabled. Preserve the existing accidental HDF5 file locally before removing
   its root placement. No production I/O changes.

## Documentation and scientific messaging

- Keep existing URLs and advanced pages, but organize navigation into Home,
  Understand, Use, Validate, Reference and Develop.
- Add a beginner explanation of reflectance, bands, response, geometry and spatial
  support, then an offline first example and a workflow-choice guide.
- Shorten README; retain detailed behavior in canonical workflow/reference pages.
- Replace novice-facing physical-chain language with common framework,
  sensor-specific treatment. Configured Landsat-like products do not demonstrate
  agreement with independently measured Landsat observations.
- Put the complete SI under publication evidence, after concise validation pages;
  retain its historical scientific limits and source revision boundaries.
- Preserve intentionally historical audits, placeholders and evidence. Flag
  author-only declarations and archival uncertainties rather than fabricate them.

## CI ownership

`docs.yml` becomes checks only (strict build, source consistency, internal links,
browser smoke). `gh-pages.yml` is the only deployment owner using the official
Pages artifact flow and requiring those checks. Drift auditing remains a separate
source-contract heuristic; it must not copy temporary reports into public docs.
JOSS and release workflows retain their distinct source/render/exact-artifact roles.
External network checking remains best-effort and is not a publication gate.

## Human review / risky actions deferred

- Confirm rights before restoring any literature PDF to public redistribution.
- Confirm provenance/licensing and desired external hosting of research datasets;
  no data deletion, git history rewrite or remote migration in this cleanup.
- Confirm the historically used gocmd version and replay against a real CyVerse
  campaign; do not invent a tested upstream version from binary size/date.
- Complete manuscript author consent, funding, COI and AI review declarations.
- Confirm platform Pages settings before live deployment; no public push here.

## Verification

Baseline and final full pytest; Ruff across src/tests/scripts; strict MkDocs;
JOSS source checks and official PDF build; supplement source/content consistency;
generated AI/validation checks; installed/public import and console help smoke;
existing browser tests plus novice navigation and publication-evidence checks;
checksummed move manifest; internal Markdown and rendered HTML anchors/assets;
post-migration search distinguishing valid pinned historical references.
