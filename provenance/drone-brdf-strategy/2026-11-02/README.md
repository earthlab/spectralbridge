# Three-flight identifiability and correction strategy

The [investigation](../../../docs/dev/drone-brdf-identifiability-investigation.md) links seven real-data figures, measured angular and polygon tables, limitations and source references. The [production plan](../../../docs/dev/drone-correction-production-plan.md) is a proposal; no package correction policy or production artifact was changed.

Run from the repository root with the scientific environment:

```bash
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python provenance/drone-brdf-strategy/2026-11-02/analyze.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python provenance/drone-brdf-strategy/2026-11-02/figures.py
.venv/bin/python provenance/drone-brdf-strategy/2026-11-02/report.py
```

`make_pdf.py` uses Python with reportlab (the Codex bundled Python was used here); render the PDF with `pdftoppm` for visual verification. `metadata_audit.py` records the six retrieved image CSVs and explicit remote origins. Fetch these read-only with `gocmd get <remote_origin> <path>` if restaging; local paths and SHA-256 hashes are preserved in its JSON. No credentials are recorded.

Inputs are the P148/P154 spatially repaired three-flight H5/ENVI products and P160 recovered TIFFs; their original Data Store origins are in the earlier scale/reprocessing manifests. `analyze.py --work /new/experimental/path` selects the large isolated output directory. The default is `/private/tmp/drone-brdf-strategy-20261102`. `manifest.json` lists full source paths and hashes. Source files are never opened for modification; old outputs and coefficients remain immutable.

`polygon_spectra.csv` is compact (one spectrum per polygon/branch); no ordinary pixel-scale bulk table is created. `*_display_samples.npz` are explicitly coarse display samples, not analytical inputs to the full-scene rank calculation. Experimental full raw/topographic arrays are outside the repository. Topographic panels are numerical DN sensitivity only, with unverified illumination; valid BRDF and combined branches remain UNSUPPORTED. The historical Goldhill artifact appears only as an invalid diagnostic in Figure 3.

`evaluate_polygons(frame)` can rerun compact statistical summaries independently from the large-image pass. Use the saved `polygon_spectra.csv`; 1,999 permutations and the fixed seed reproduce the final tables. This helper does not reread rasters or change source files.
