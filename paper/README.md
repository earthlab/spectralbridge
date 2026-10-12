# Manuscript and publication sources

Edit `paper.md`, `paper.bib`, `supplement.md`, `supplement.bib` and `figures/`.
These are the canonical human-edited JOSS/manuscript sources. The main paper
explains the software's purpose; the supplement records technical/historical
evidence. Current operational instructions belong in `docs/`, not the supplement.

| Location | Classification | Editing / preservation policy |
| --- | --- | --- |
| Main/SI Markdown and BibTeX | Canonical source | Reconcile author/coworker edits here before building |
| `figures/` | Author-supplied assets | Original crops/table-page images retained; do not invent scientific figure content |
| `archive/` | Immutable source snapshots | Supplied PDFs and extracted text/printed references; checksums preserve their provenance |
| `generated/` | Derivatives and checks | Official JOSS preview, intermediate SI HTML, source fingerprint, export DOCX and audit/verification JSON; regenerate rather than edit prose |
| `generated/google-docs/` | Collaboration exports | Import-ready editable files; reconcile returned edits to canonical Markdown; no independent source fork |
| `docs/validation/supplement*` | Generated website record/downloads | Generated from SI/BibTeX/assets; published as an evidence record, not a tutorial |

Generated website assets and existing review exports remain version controlled
for offline website builds, reviewer downloads and provenance. Their source hashes
and completeness contracts are checked. No Google Docs have been uploaded/shared.
The source PDF download is explicitly the original author-supplied 44-page snapshot,
not a claim that it was rebuilt from the later Markdown edits.

## Build and verify

Install the docs/test environment (`pip install -e '.[docs,tests]'`) and start
Docker. The build uses a pinned Open Journals/Pandoc image, with network disabled:

```bash
bash scripts/build_publication.sh all
python scripts/check_joss_submission.py --output paper/generated/submission-checks.json
python scripts/generate_supplement_docs.py --check
pytest -q tests/test_joss_submission.py tests/test_supplement_docs.py
mkdocs build --strict
```

The main JOSS PDF is `generated/paper.pdf`. Its build manifest is regenerated
automatically, with visual review marked pending for the new exact PDF. Record
review only after inspecting it; prior review is never carried over implicitly. The script prepares the SI fingerprint,
renders `generated/supplement.html`, then regenerates the website's supplement,
source bundle and assets. Source/BibTeX changes require a new render; `--check`
rejects a stale fingerprint or changed generated download.

An optional `bash scripts/build_publication.sh supplement-pdf` produces a new SI
PDF through Pandoc. Its table/equation/page layout must be inspected before sharing;
it is distinct from the immutable author-supplied source snapshot. Existing DOCX
exports reflect their recorded conversion boundary, including the documented
physical-row reconstruction of PDF tables. Refresh/reconcile them after substantive
source edits rather than editing a generated copy in parallel.

Use `check_joss_submission.py --ready` only after authors complete funding, COI,
consent and AI review/design declarations. The normal source check validates
structure and citations and cannot certify editorial eligibility or consent.
See [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for remaining author actions.
The PDF draft watermark and placeholder publication metadata are expected.

## Evidence and migration

`generated/bibliography-audit.json` records DOI/metadata normalization; extracted
printed references remain under `archive/`. `generated/verification.json` records
conversion boundaries. `generated/build-verification.json` records official build
inputs. The migration ledger in `provenance/cleanup/2026-10-12/moves.json` preserves
original paths and checksums; pinned historical manuscript citations are unchanged.
