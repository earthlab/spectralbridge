# Figure 4 — plant functional types across three Landsat-mode products

This folder is the complete **figure reproduction handoff**. Copy it anywhere. It
contains the publication PDF, a 300-dpi PNG, annotated plotting code, local CSV
inputs, supporting statistical evidence, a caption, and source/checksum metadata.
It is an ordinary script folder, not an installable Python package. No repository
checkout, SpectralBridge installation, raster downloads, account or network
connection is needed to run the figure after installing the plotting dependencies.

## Run just this figure

Use Python 3.12 (the recorded run used Python 3.12; exact patch and library versions
are in `provenance.json`). Open a terminal in this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_figure_4.py
python plot_figure_4.py
```

On Windows activate with `.venv\Scripts\activate` instead. `python` refers to the
activated environment in all remaining commands. Matplotlib includes the DejaVu
Serif font used here. The script uses a headless backend, so no display is needed.

Outputs, written into this folder by default:

- `figure_4_plant_functional_types.pdf`: vector publication figure with embedded fonts.
- `figure_4_plant_functional_types.png`: 300-dpi preview, 4,800 × 2,850 pixels.

The script finds inputs relative to itself, so it also runs from another working
directory. To keep a new rendering separate:

```bash
python plot_figure_4.py --output-dir new_rendering
python plot_figure_4.py --check
```

Dependency installation requires internet or an existing wheel cache. Rendering
and validation operate offline. Exact dependency pins reproduce the recorded
software stack; they are not a promise of compatibility with every Python version.
PDF timestamps may change, so file hashes of rerenders need not match even when
the plotted values and visual appearance are identical.

## What to send to the publisher or team

Send this entire folder or its sibling ZIP, not only the plotting script. Include
`figure_4_caption.md` with the figure: it defines the table values, dagger marks,
recall ordering, shaded interquartile range, and scientific limitations. The
`supported` count is not a binary classification of an entire PFT as separable.

| File or directory | Purpose |
| --- | --- |
| `plot_figure_4.py` | Standalone renderer, validation and optional spectral aggregation |
| `data/spectral_medians_and_interquartile_ranges.csv` | Actual plotted medians, quartiles and sample counts |
| `data/spectral_observations_by_footprint.csv` | Compact pre-normalization footprint spectra; no pixel archive required |
| `data/pft_separability_and_identifiability.csv` | Numeric panel B evidence and explicit unavailable/untested statuses |
| `evidence/` | Archived pair tests, exploratory Landsat patch predictions and drone predictions |
| `DATA_DICTIONARY.md` | Column meanings, units, missing values, valid statuses and aggregation |
| `figure_4_caption.md` | Complete manuscript-ready methods and interpretation text |
| `check_figure_4.py` | Standard-library test runner; no pytest needed |
| `requirements.txt` | Exact three-library plotting environment |
| `provenance.json` | Source paths relative to original repository, hashes, versions and limits |
| `SHA256SUMS.txt`, `refresh_checksums.py` | Integrity manifest and explicit refresh/verification commands |
| `LICENSE.txt`, `NOTICE.txt`, `software_citation.cff` | Retained code license/notices and upstream software citation |

## Update the numbers

Work on a copy and keep the previous dated folder or ZIP as a frozen version.
Use a CSV-aware editor; keep identifiers as text and retain full numeric precision.
Headers and the sensor/category labels must match `DATA_DICTIONARY.md` exactly.

### A. You already have new medians and quartiles

Update `data/spectral_medians_and_interquartile_ranges.csv`. Keep one row per
sensor × PFT × band (105 rows). Medians and quartiles must be calculated **after
normalizing each footprint** by its own B1–B5 sum. Counts are independent footprint
counts, not pixels or annual observations. Leave all drone B6/B7 values blank.

If you update summaries without replacing observations, explicitly record in
`provenance.json` that those observations are historical and no longer back the
new summaries. The observation-to-summary consistency test will intentionally
fail until they agree; do not treat that as a rendering failure or silently
rewrite the historical observations.

### B. You have new footprint spectra

Replace `data/spectral_observations_by_footprint.csv` with the same schema and run:

```bash
python plot_figure_4.py --recalculate-spectra
```

This **overwrites the summary CSV** and renders the updated figure. Each row must
already represent one independent footprint: one Landsat cell; one NEON polygon
with repeat years averaged; or one drone polygon with pixel bands summarized by
medians. The script does not perform those upstream aggregations for you.
It removes incomplete spectra and spectra with nonpositive B1–B5 sum, reports
exclusions, normalizes each retained spectrum, then calculates category medians
and linear 25th/75th percentiles. The calculation_dtype column preserves source arithmetic precision (original drone float32, Landsat/NEON float64); set it to the precision appropriate to replacement data. It does not exclude finite negative values just
because they are negative. Site counts are not rebalanced. Pairwise gap strips
are recalculated from the new medians automatically.

### C. You have new separability or identifiability results

Update `data/pft_separability_and_identifiability.csv`, then render normally.
Use numeric fractions for recall (0.64, not `64%`); leave unavailable values blank.
Replace the corresponding `evidence/` tables, update their provenance and revise
`figure_4_caption.md` whenever cohorts, protocols or interpretations change.
New table numbers must come from your statistical analysis: **the plotting script
does not fit classifiers, permute labels, or infer support from curve differences**.

The Landsat table uses the expanded nominal 95% HLS footprint-cover cohort:
496 cells in 24 spatial patches. All ten NPC pairs are testable; each category
reports supported comparisons out of four. `held_out_patch_recall` is a single
class recall with correct/total counts. The extra 120 m source-area screen is a
separate sensitivity. Both panels use the same expanded HLS L30 NBAR reference cohort. A summarizes
normalized cell spectra, while B evaluates direct-reflectance patch medians.

After any update:

```bash
python check_figure_4.py
python plot_figure_4.py
python refresh_checksums.py --write
python refresh_checksums.py --verify
```

Inspect the PDF visually, especially long labels and small-sample classes. Update
the date, versions, source hashes, cohort description and any new identifiers in
`provenance.json`. Writing checksums records changed bytes; it does not establish
scientific validity. To change PFTs, sensors, colors or band availability, edit the
small configuration section at the top of `plot_figure_4.py` and update validation,
inputs, caption and dictionary together.

## Scientific scope and limitations

- Shading is the **interquartile range**, not variance in squared units, standard
  deviation or a confidence interval. Lines are medians.
- Both real-Landsat panels use the same 496 HLS L30 NBAR cells in 24 patches.
  Labels remain provisional, especially older-lidar evergreen support. Three pooled
  pairs meet current-family Holm; held-patch prediction is 21/24. Reference
  definition materially affects results. No Collection 2 spectra remain plotted.
- AOP is the retained synthetic OLI-like table. Drone uses five native MicaSense
  band proxies; no drone SWIR or OLI-2-specific convolution is manufactured.
- Drone results are exploratory evaluation at two calibration sites. A missing
  training class gives unavailable held-site recall, not an estimated 0% recall.
  NEON and drone classification protocols differ; recall is not a controlled
  model comparison. See the caption for full definitions.
- The folder reproduces the figure and its spectral summaries. Raw imagery,
  field mapping, and upstream model/test pipelines are outside this compact
  handoff. Supporting evidence is included to trace the supplied results.

## Citation, rights and FAIR reuse

The figure title and filenames identify **Figure 4** locally; `provenance.json`
records source identity and software versions. CSV, Markdown, JSON, PDF and PNG
are open, human-readable or widely readable formats. Checksums identify the exact
shared snapshot. These support findability, accessibility, interoperability and
reuse, but no DOI, repository deposition or independent scientific validation has
been created by packaging this folder.

Plotting code is derived from SpectralBridge and retains **GPL-3.0-or-later**;
retain `LICENSE.txt` and `NOTICE.txt` when redistributing it. `software_citation.cff`
is the upstream **software** citation, not an invented article or Figure 4 DOI.
Cite the manuscript as assigned by its authors and cite the software when used.
No new license is asserted for the source observations or derived scientific
results: original provider/author terms remain applicable. The team should record
its chosen data/figure reuse license and any publication-specific credit before
public repository deposition; code licensing alone does not grant data rights.
For long-term public FAIR archiving, deposit the frozen ZIP plus caption in the
team's chosen repository, add the assigned persistent identifier and confirmed
data license to this README/provenance, and preserve the version and checksums.

## Current Panel B source: expanded HLS L30 v2

The table uses **496 nominal-95%-cover HLS cells in 24 spatial patch groups**.
The extra full-source-area screen remains a sensitivity (161 cells/13 patches).
Four new shrub patches and one rock patch were reviewed before reading their
spectra; all new photo-cover passes were retained through unchanged HLS QA.
Current numeric inputs are `data/pft_separability_and_identifiability.csv` and
`evidence/landsat_hls_figure_table_summary.csv`. The generic
`landsat_exploratory_*` evidence now contains this expanded HLS analysis.
Previous C2/normalized/strict-only files are retained as explicit historical or
sensitivity evidence, not current main-table inputs.

All ten NPC pairs are testable; three pass Holm and class counts are 1/4,0/4,
1/4,3/4,1/4. Held-patch recall counts are 4/5,3/3,5/5,6/7,3/4 in plot order.
The caption distinguishes pooled significance, predictive recall, the separate
pairwise BA diagnostic, sensitivity selection and provisional reference labels.

Panel A now uses these same HLS cells, with normalized cell medians/IQR/counts
and recomputed HLS–AOP/HLS–drone strips. Previous C2 spectra are historical only.
The complete current analysis and reference provenance are included in evidence.

## Refresh the HLS spectral panels offline

The current sensor key is `HLS L30 NBAR` in both spectral and statistical inputs.
The old `Landsat 9 OLI-2` key is not selected by the renderer. To reconstruct A
from the included primary HLS observations (without raster access):

```bash
python update_hls_spectral_inputs.py
python check_figure_4.py
python plot_figure_4.py
```

The update script replaces the real-Landsat footprint rows, normalizes each HLS
cell by its B1–B5 sum, recomputes medians/IQR/counts and updates the shared sensor
name in B. It does not fit statistics or alter NEON/drone input values. If the
reference cohort itself changes, rerun statistical analysis and replace B's
evidence too; standalone checks verify plotted HLS input hashes, identities and
values against the exact cohort behind B's archived predictions.
`hls_spectral_update_manifest.json` records the shared source and output hashes.
`historical_c2_spectral_*` files preserve the superseded Niwot inputs, outside
the plotted data. The canonical Figure4 renderer is this folder's
`plot_figure_4.py`; the repository's older `landsat_pft_panel.py` is a historical
C2 prototype and does not reproduce the current HLS handoff.

The legend and table display the full label **Landsat HLS L30 NBAR**. The
internal CSV sensor key remains `HLS L30 NBAR` to keep input identities stable.
