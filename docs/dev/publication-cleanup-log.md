# Publication Cleanup Log

Date: 2026-06-02

This log records repository cleanup decisions made before publication review.
The goal was to reduce ambiguity without changing scientific assumptions,
Parquet behavior, chunking, or restart-safe pipeline contracts.

## Completed Decisions

| Feature request | Outcome |
| --- | --- |
| FR-001 generated artifacts | Moved tracked `.DS_Store` and Python bytecode files to `deprecated/generated_artifacts/2026-06-02/` with original paths preserved. Added ignore rules so new local artifacts stay untracked. |
| FR-002 large deprecated data | Kept deprecated Megan unmixing data for provenance, documented its status, and excluded `deprecated/` plus root `gocmd` from source distributions through `MANIFEST.in`. |
| FR-003 distribution contents | Added `MANIFEST.in` to include package data/docs/tests intentionally and exclude root staging data, deprecated archives, generated docs reports, and container-only helpers. |
| FR-004 root scripts | Kept root helper scripts because container and remote-storage workflows call them from unusual mount roots. Documented them in `docs/dev/container-workflows.md`. |
| FR-005 docs source of truth | Archived stale root draft pages with `FILLME` markers to `deprecated/docs/publication_cleanup_2026-06-02/` and updated README links to current MkDocs pages. |
| FR-006 docs tooling | Updated `scripts/check_docs_links.py` to scan nested docs, ignore generated `_build` output, and make `FILLME` failure opt-in via `--fail-on-fillme`. |
| FR-007 README QA placeholder | Removed the “coming soon” placeholder and linked the checked-in workflow diagram that includes QA reports in the output contract. A renderer-produced QA PNG was not generated locally because this environment lacks `matplotlib`; QA fixture rendering remains covered by tests/CI. |
| FR-008 MicaSense tutorial | Rewrote the tutorial around the supported `run_drone_pipeline` local-H5 API and drone-native output names. |
| FR-009 stale reference examples | Rewrote `docs/reference/extending.md` around current extension points and archived the stale root `docs/validation.md` CSV-first draft. |
| FR-011 top-level orchestration exports | Added lazy top-level exports for `go_forth_and_multiply` and `process_one_flightline`, plus smoke coverage. |
| FR-012 generated docs drift reports | Moved tracked `docs/_build/` reports to `deprecated/generated_docs/2026-06-02/` and ignored future generated `_build` output. |
| FR-013 duplicated data locations | Documented root `data/` as examples/local staging and `src/spectralbridge/data/` as authoritative package data. |
| FR-014 publication checklist | Refreshed checklist items to reflect completed packaging, docs, tests, Ray, and cleanup work. |

## Notes

- Unrelated external-repo PRISM artifacts were removed earlier in this cleanup
  because the user confirmed they belonged to a different repository.
- Ray is required and remains the default parallel engine. Thread and process
  engines remain explicit alternatives for runs that should avoid Ray
  initialization.
- Parquet remains the authoritative tabular output. CSV files, when present,
  are convenience sidecars only.
- Root `CONTRIBUTING.md` was refreshed alongside MkDocs contributor guidance so
  public community files use current SpectralBridge naming and commands.
