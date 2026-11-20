# Full-resolution conservative-refit application and translation attempts

**Subsequent unit-audit update (19 November 2026):** all72 archived AOP training headers confirm a10000 storage divisor. A separate fractional-reflectance registry now resolves the coefficient-unit issue. See `../aop-translation-audit/README.md` and `../scale-chain-audit/README.md`. Historical refusal records below remain unchanged; experimental input status is a separate remaining gate.

19 November 2026. New corrected products were generated for **Ruby, Gordon and
Goldhill**, applying the saved conservative shade-excluded SCS+C model followed
by the saved combined BRDF model. All ten bands are populated in every product.
These are separate experimental outputs; all original rasters/models remain
unchanged.

## Translation is not complete

The existing OLI and OLI-2 translation entry point was actually called for each
site (six attempts). All six refuse the inputs with:

> Experimental correction is not eligible for an approved spectral library

The corrected headers retain `scientific validation status = EXPERIMENTAL` and
`radiometry status = HYPOTHETICAL_UNVERIFIED`. The original conditional encoding
used to fit these models was not silently promoted to verified calibration.
The packaged coefficient plans independently retain `reflectance_units = None`:
the archive does not supply verified physical-unit provenance for the historical
count-scale fits. Altering a status/header or assuming a scaling divisor would
not resolve those scientific dependencies.

Thus the BRDF *model-support* barrier is cleared for the selected conservative
fits, and full raster application is now completed. Approved physical calibration
and compatible coefficient units remain separate blockers. No translated file
or datastore upload was produced. The preceding fit pass did not establish that
the entire translation workflow was ready.

## Products

Large ENVI image/header pairs are under:

```text
archive/local/drone-calibration-translation/2026-11-19/conservative-refitted-products/
  ruby/AOP_Ruby_20230814__conservative_refitted_topo_brdf_EXPERIMENTAL.img
  gordon/AOP_GORDON_20230814__conservative_refitted_topo_brdf_EXPERIMENTAL.img
  goldhill/AOP_GOLDHILL_20230814__conservative_refitted_topo_brdf_EXPERIMENTAL.img
```

Each has its corresponding `.hdr`. The same conservative pre-correction shade
mask used for fitting is used for application. Excluded shade/NoData pixels stay
missing in every band; retained pixels may additionally lose per-band support
where the unchanged topographic conditioning rules require it. No clipping,
identity fallback, missing-band substitution or coefficient refitting occurs.
Historical spectral labels, including native NIR 862 nm, are retained for
traceability; they are not silently updated during correction application.

## QA and evidence

- All three output grids match source CRS, transform and dimensions exactly.
- All ten output bands contain finite usable pixels at each site.
- A full raster pass confirms excluded pixels remain NoData in all bands.
- Saved input, mask, model and output hashes back the application checkpoints.
- **1,920 independent algebra samples** across 30 bands reproduce the applied
  SCS+C ratio and saved BRDF reference/directional ratio (`rtol=1e-4`,
  `atol=1e-4` in stored units). Original input hashes remain unchanged.
- 33 focused translation/shade tests and Ruff pass. Production guards remain
  unchanged.

`<site>/corrected_band_qa.csv` reports exact per-band finite coverage and maximum
stored-value correction gains. Large gains remain in retained pixels. At650nm,
maximum combined gains are approximately Gordon12.21x, Goldhill16.81x and
Ruby3.36x. A fitted-model pass is not independent validation of these corrections.
Use the CSV values rather than these rounded descriptions for analysis.

`<site>/application_complete.json` records source/model/mask and output hashes.
`<site>/translation_attempt.json` records both actual refusal messages and
coefficient-unit metadata. `independent_algebra_checks.csv` and `verification.json`
record independent application verification. The original model comparisons
remain in the sibling `shade-excluded-refit-v2/` folder.

## Reproduce

From the repository root with the existing environment:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_apply_conservative_refits.py --site ruby
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_apply_conservative_refits.py --site gordon
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_apply_conservative_refits.py --site goldhill
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/verify_drone_refitted_products.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_translation.py tests/test_drone_translation_registry.py tests/test_drone_shade_refit.py tests/test_drone_shade_mask_preview.py
```

Application uses the previously established isolated *research* calibration
boundary and frozen shared correction functions. It never changes production
calibration validation. Raster arrays are read/applied/written in128-line chunks;
the original large inputs are memory mapped. Verified outputs are reused on
restart. Changing source/mask/model identities or application methods requires
a new separately versioned output stage, not modifying these results.
