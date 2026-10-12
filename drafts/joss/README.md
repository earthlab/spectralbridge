# Coworker editing drafts

These are mechanical conversions of the author-supplied PDFs revised 12 October
2026. They preserve the draft's claims and unresolved author notes; they do not
update historical evidence to the current repository or certify submission readiness.

## Files

- `main-38.pdf` and `supplement-10.pdf`: unchanged source documents.
- `paper.md`: JOSS-style manuscript, with YAML author/affiliation metadata,
  Pandoc citations, a LaTeX display equation, and three retained figures.
- `supplement.md`: editable SI with matching metadata and its own bibliography.
- `paper.bib` and `supplement.bib`: bibliography drafts reconstructed from the
  printed references. Separate keys preserve the different Earth Lab year suffixes
  used in the two PDFs. Do not interchange these bibliographies.
- `figures/`: original figure crops and SI table-page images for checking layout.
- `*-extracted.txt`: full page-layout text extracted from every source page.
- `*-references-extracted.md`: printed reference entries for bibliography review.
- `verification.json`: checksums and conversion contract checks.

## Google Docs collaboration

Google now documents opening and editing Markdown directly, with comments and
sharing, while retaining the `.md` file type:
https://support.google.com/docs/answer/18289341?hl=en

1. Upload `paper.md` and `supplement.md` to Google Drive.
2. Double-click each file to open it in Google Docs. Check for the `.md` tag
   indicating Markdown Mode, then share with coworkers for edits and comments.
3. Share the source PDFs alongside them for figures and table layout. Local image
   links may not resolve in Drive; the PDFs remain the visual reference.
4. Download the edited Markdown and reconcile it with these repository drafts.
   Check YAML, citation keys, math, image paths, and labels before rendering.

If Markdown Mode is unavailable in your account, import Markdown as a Google Doc
and later use **File > Download > Markdown (.md)**. Google documents that workflow:
https://support.google.com/docs/answer/12014036?hl=en

Keep the `.bib` files and authoritative figure assets in the repository. Google
Docs supports ordinary Markdown, but its help does not promise lossless handling
of JOSS/Pandoc YAML, citations, math, or cross-references. Check those after edits.
No Google documents have been uploaded or shared by this task.

## Submission preparation

The manuscript now has normalized reference metadata, repaired URLs, Pandoc
citations, retained figures, and a numbered equation. DOI records were checked
against Crossref/publisher metadata and the HyTools record against DataCite.
`bibliography-audit.json` records the checks. Printed originals remain available
in the PDFs and extracted reference records.

The official JOSS renderer has compiled `paper.pdf`. Its draft watermark and
placeholder publication metadata are expected. Final author declarations remain
visible in the source and preview; this is not yet a submitted or accepted paper.

See [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for the guideline audit,
remaining author input, and public submission steps. `submission-checks.json`
and `build-verification.json` record validation and exact build inputs.

Run from the repository root (PyYAML is included with the docs environment):

```bash
python scripts/check_joss_submission.py --output drafts/joss/submission-checks.json
pytest -q tests/test_joss_submission.py tests/test_ai_transparency.py
```

Add `--ready` to reject unresolved author-input markers. The validator is a
source-contract check and cannot certify consent or editorial eligibility.

To rebuild locally after starting Docker:

```bash
docker run --rm --network none \
  --volume "$PWD/drafts/joss:/data" \
  --user "$(id -u):$(id -g)" \
  --env JOURNAL=joss \
  openjournals/inara@sha256:a0414b8b72fd8923917ede614d340d98dc7aa3102aabc2e955e9c02a6100fd62 \
  -o pdf paper.md
```

The new `.github/workflows/joss-paper.yml` repeats the official build and uploads
its preview on relevant pushes/PRs. It has not run remotely yet.

SI tables are editable Markdown tables with source-page images. That
supporting material is separate from the short JOSS paper and is not included
in its official build. Review SI mathematical notation and wrapped text against
the source PDF before circulating it as a finished supplement.

## Complete SI on the documentation website

The complete supplement is available from the existing Validation, Technical
reference and Software citation pages. It preserves all SI sections/appendices,
23 tables, two figures, three equations and all 101 printed references. The
website version uses readable author–date citations, native MathML and a linked
contents list. Original table-page images and the complete original PDF remain
available, alongside Markdown, BibTeX and Google Docs import downloads.

To regenerate after editing the SI, render its full HTML with the same pinned
Pandoc runtime, then copy/check the complete content and assets:

```bash
python scripts/generate_supplement_docs.py --prepare-render
docker run --rm --network none --entrypoint pandoc \
  --volume "$PWD:/data" --user "$(id -u):$(id -g)" \
  --workdir /data/drafts/joss \
  openjournals/inara@sha256:a0414b8b72fd8923917ede614d340d98dc7aa3102aabc2e955e9c02a6100fd62 \
  supplement.md --citeproc --bibliography supplement.bib --metadata title= \
  --mathml --toc --standalone --include-before-body supplement-render-header.html \
  --to html5 --output supplement.html
python scripts/generate_supplement_docs.py
python scripts/generate_supplement_docs.py --check
mkdocs build --strict
```

`docs/validation/supplement-coverage.json` records source hashes and completeness
counts. Preserve the `nocite` metadata so references appearing only in printed
provenance tables are included. Reconcile any substantive SI changes with the
Google Docs editing copy before regenerating its downloadable asset.
