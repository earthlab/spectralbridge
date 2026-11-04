# Anatomy of a Red Artifact, Part II

**How We Reconstructed the Goldhill Drone BRDF Correction - November 2026**

The completed companion is `Anatomy_of_a_Red_Artifact_Part_II.pdf` (20 pages).
Editable sources are `report.md` and `report_pages.json`; 25 standalone figures
are supplied as PNG and SVG. `numerical_evidence.csv` contains 157 claims with
source hashes, calculations, population definitions and verification status.
`input_manifest.json` binds the available evidence. Prior publications are
preserved, not overwritten.

The report separates encoding, eligibility, fixed-geometry rank, reconstructed
rank-three design and ecological evidence. Candidate reflectance assumes
DN/32768 and is not physically calibrated by this investigation. Contributor
assignments and blending weights are inferred. The newer integrated-reliability
experiment is clearly identified as subsequent engineering work.

From repository root, restore the recorded research inputs and run:

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
.venv/bin/python provenance/brdf-artifact-anatomy-part-ii/2026-11-04/collect_evidence.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/build_publications.py
python provenance/drone-integrated-reliability/2026-11-04/render_pdf.py
```

The figure builder also reads completed integrated-experiment outputs and creates
its separate report. Its README gives their execution order and dependencies.
Large native arrays are in explicitly recorded local scratch, not bundled in the
compact publication. Restore or explicitly remap paths and record a new run when
reproducing elsewhere. ReportLab/Arial are required for rendering.

Histograms/maps can be sampled for display; exact metrics use native masks.
Display saturation is explicit and never alters analysis. Median/IQR spectra
are descriptive; the classifier uses mean spectra. The 6,678,404 controlled fit,
6,683,944 clean zero-view and 6,683,905 reconstructed terrain-valid populations
are distinct. P173 ecology uses 144,406 memberships/157 identities; the newer
integrated common-support evaluation uses 142,637/157. Do not mix the baselines.
