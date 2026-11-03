# Drone findings integrated into permanent documentation

2026-11-02. P163. Documentation, notebook examples, documentation generators and
source docstrings only. No pipeline algorithm, coefficient, production imagery,
spectral library, release identity or deployment changed.

## Organization before and after

| Before | After |
| --- | --- |
| Investigation reports contained the detailed evidence; canonical methods still described the old scale convention and BRDF fallbacks | Existing drone and correction-method pages explain current contracts and link the preserved reports |
| Drone examples requested both corrections without first providing calibration | Local examples require a reviewed calibration file and explicitly omit unapproved corrections; the historical cloud recipe is labelled and guarded |
| No short three-flight status page or central correction decision table | Two pages in existing sections: Understand → Choosing corrections; Validate → Drone findings and limitations |
| Spectral-library, QA and troubleshooting guidance lacked the consolidated three-flight evidence | Existing pages connect spatial/radiometric/angular provenance to labels, spectra, masks and independent validation |

The MkDocs Material framework, existing navigation sections, typography and page
URLs remain. The live public website was inspected read-only and still reflects
an older deployment; these changes were built locally and **not deployed**.

## Pages created or updated

Created:

- [Drone Processing: Validation Findings and Current Limitations](../../../docs/validation/drone-findings.md).
- [Choosing Radiometric, Topographic, and BRDF Corrections](../../../docs/concepts/correction-eligibility.md).

Updated canonical pages:

- Drone processing: complete measurement sequence, state definitions, source-aware spatial check,
  bandwise normalization/inverse, scalar physical contract, photogrammetry and directional information.
- BRDF/topographic methods: current affine boundary, model support/prediction gates, Goldhill case,
  SCS+C stability and three-flight evidence.
- Spectral-library vignette/overview and polygon extraction: membership, physical units, historical
  product status and researcher-polygon validation.
- Troubleshooting: flipped/misaligned rasters, unexpected values, extreme BRDF, mask loss,
  drone–NEON disagreement and upstream seams.
- Reference literature: four verified full titles, author/year/journal details, DOIs, methods and limits.
- Correction/comparison concepts, QA, NEON correction, retained drone/NEON tutorials,
  remote production, notebook catalog, getting started and API examples.
- Homepage and README: concise links to current findings and correction choices.
- Generated validation index: link added through its generator; campaign records/dates unchanged.
- API inventory and two generated module workflow links: current docstrings and correct drone/bulk guides.
- Historical technical reports: website-safe evidence destinations; dated supersession notice on the
  spatial report. Scientific tables/results and earlier PDFs remain intact.
- JOSS manuscript: one factual correction replaces obsolete neutral-BRDF-fallback wording;
  authorship, references, license and release metadata unchanged.

Notebook review covered all four current drone entry-point notebooks. The root
local notebook and vignette 06 use an explicit calibrated/no-topo/no-BRDF template.
The root cloud notebook retains its old recipe and adds a deliberate review guard.
Vignette 10 retains its existing RUN/upload gates and adds scientific-readiness
context. Existing cells and saved outputs were not deleted. A bare path and shell
commands in the old local notebook were marked as comments/Jupyter magics so they
are not invalid Python examples.

## Scientific findings and misleading statements corrected

- Preserved arrays do not imply correct geographic placement: signed row size,
  center/corner and datum conflicts affected polygon selection.
- Stored 0–10,000 values are verified per-band min/max normalization, not proven physical
  reflectance ×10,000. Goldhill/Ruby offsets require band-specific inverse recovery.
- Unknown calibration remains unsupported; neither DN/32768 nor stored/10000 is invented.
- Current RossThick/LiDenseR needs supported rank/conditioning and stable predictions.
  All three mosaics have rank 1/3 and zero supported bands. Zero views trace to explicit
  converter placeholders, not proven loss inside Metashape or current writer defaults.
- Goldhill's red streak is a confirmed downstream historical BRDF failure; reversing scaling
  does not remove it. Independent upstream seam attribution remains hypothetical.
- SCS+C's denominator guard does not guarantee stable gains. 528×/357×/373× maxima and
  4.08%/5.49%/1.49% source-valid mask losses are numerical diagnostics, not physical approval.
- Cleaner RGB, reduced variance, full rank, successful execution and `VALID` computational
  state are insufficient independent scientific validation.
- 301 polygons / 198,309 memberships show mixed descriptive effects; no cross-flight
  reflectance harmonization was established. Historical libraries remain unapproved.
- Metashape estimated camera geometry, but actual calibration/operation flags and matching
  projects remain unrecovered. Duplicate corrections are not established or ruled out.
- NEON geometry and source calibration differ from these drone mosaics; every product and
  correction state still needs review. No blanket invalidation of unrelated NEON libraries.
- Rich stage preflight, automatic bandwise inverse ingest and original-photo correction remain
  planned/conditional; no proposed interface is presented as implemented.

The [evidence map](evidence_map.md) and [JSON map](evidence_map.json) associate each finding
with reports, source locations, destinations and confidence/validation status.

## Figures

Six existing investigation figures were proportionally resized/re-encoded as WebP:
metadata lineage, radiometry, angular support, historical Goldhill stage comparison,
SCS+C stability and literature pipeline alternatives. Two native SVG diagrams show
the measurement workflow and correction decisions. Alt text, status captions and
links to full evidence accompany them. [Manifest](figure_manifest.json) records
source paths, dimensions and sizes; no scientific arrays were changed or added.
Together these eight web assets are under 1 MB. Third-party paper PDFs are not
redistributed in the website build.

## Verification and limitations

See [verification.json](verification.json) for final checks and
[documentation_checks.json](documentation_checks.json) for rendered-reference and
code-syntax counts. Reproduce the main checks from repository root:

```bash
python scripts/generate_api_reference.py --check
python scripts/generate_ai_transparency.py --check
python scripts/check_docs_links.py
python -m mkdocs build --strict --site-dir /private/tmp/spectralbridge-drone-docs-site
python scripts/check_api_reference.py /private/tmp/spectralbridge-drone-docs-site
python provenance/drone-docs-integration/2026-11-02/check_documentation.py /private/tmp/spectralbridge-drone-docs-site
```

Use the installed development environment (`.venv/bin/python` here). Tests cover
radiometry/BRDF contracts, generated API/validation/supplement/scientific docs,
JOSS metadata and transparency. The local drone notebook also executes in dry-run
mode with RUN=False. Data-dependent examples are configuration templates checked
for syntax; they were not run against a fabricated calibration or production data.
The AST check confirms the two edited package modules changed only docstrings.

Browser inspection at 893 px found readable status/eligibility tables, loaded
workflow/provenance images and no document-wide horizontal overflow. Existing
responsive CSS/table scrolling is retained; a handset/device-emulation viewport
was not tested. External DOI/publication metadata was cross-checked against full
paper headers/methods retained from P162; some publisher requests were rate-limited.
Repository links for new evidence become publicly available when these changes
are merged/published; no deployment or release was performed.

Remaining scientific gaps are actual project/export/radiometric settings, calibrated
original images, camera/contributor data, authoritative timestamps (especially Ruby),
terrain-generation history and independent target/angle/cross-sensor validation.
These are data/evidence dependencies, not capabilities supplied by documentation.
