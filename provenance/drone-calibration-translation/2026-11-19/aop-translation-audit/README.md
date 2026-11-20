# AOP-derived MicaSense-to-Landsat translation audit

19 November 2026. The user correctly identified the intended model: AOP full
extractions generate MicaSense-passband and Landsat-passband products; the
regression maps the former to the latter. It is intended to translate corrected
MicaSense observations into Landsat-like band responses. AOP origin is not a
reason to reject that intended use. Independent drone radiometric accuracy is
a separate question.

## Exact provenance and numerical verification

The archive represents 12 flightlines at NIWO, WREF and YELL and 96, 016, 835
selected observations. All 18 packaged site-balanced pair-band coefficients match
the original candidate artifact exactly. Reaggregating the original 216 compact
moment records using stable hierarchical site-balanced merging reproduces all 18
slopes and intercepts. Source is MicaSense-like; target is Landsat-like:

`Landsat-like = slope × MicaSense-like + intercept`

Ten rows support OLI/OLI-2 B 1–B 5, using native MicaSense 444/475/560/668/842 nm.
Eight support TM/ETM+ B 1–B 4. No SWIR bands are invented. Per-site/flightline,
leave-one-site-out and attention flags remain source evidence. This is an
AOP-derived response mapping, not an independently fitted drone/Landsat campaign
calibration. It captures the actual processed training products, including their
recorded correction/brightness-processing provenance.

## Unit issue resolved from actual archived headers

The original compact candidates/moments have no physical-unit declaration;
this was not solely a registry-import omission. Read-only authenticated CyVerse
retrieval recovered **all 72 exact-named training-product headers**, covering 84
remote locations including duplicates. Duplicate headers agree byte-for-byte,
remote checksums are checked where available, and each selected header's band
count/grid dimensions matches the training catalogue. Every header explicitly
states `reflectance scale factor = 10000` on source and target products.

The original bulk catalogue retains combined source-signature hashes, not
separate historical header bytes. Thus current archived header contents are
verified against exact names, training dimensions and agreeing duplicates; this
is not a claim of a new byte-for-byte historical-raster reconstruction.

For stored variables M/L and fractions m/l:

```text
M = 10000*m
L = a + b*M
l = L/10000 = b*m + a/10000
```

The separate derived registry is
`aop_derived_micasense_to_landsat_fractional_reflectance_registry.json`.
Slopes, weighting, R², statuses, counts and dimensionless evidence are unchanged.
Intercepts, RMSEs and training ranges are converted to fractional units, with
original values and header-audit hashes retained. This is a change of units,
not a new fit. All 18 predictions are algebraically equivalent in both unit
systems. All four sensor plans load with `physical_reflectance_v1`.
The original packaged registry and archived coefficients remain unchanged.

## Drone scale is different

The historical drone preparation stored `S = DN*10000/65535`, while its declared
calibrated-integer convention is `reflectance = DN/32768`. Therefore decode that
specific drone representation with `65535/(10000*32768)`, not `/10000`.
The sibling `scale-chain-audit/` verifies all 30 prepared bands and native fitting
arrays exactly, correction-unit round trips and the requested common 1000 scale.

## Remaining input status

The new fractional registry was actually retried against all 3 newly refitted
corrected inputs (six OLI/OLI 2 attempts). Coefficient units now pass loading, but
the existing translation entry point still rejects the `EXPERIMENTAL` corrected
input status. No input status, physical-calibration approval or production guard
was relabelled to bypass that check. The coefficient-unit issue is resolved;
those earlier unit-blocker statements are historical and are superseded here.

## Reproduce and files

From the repository root with the existing environment:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python scripts/build_drone_translation_registry.py archive/research/bulk-calibration --candidate-coefficients candidate_translation_coefficients.parquet-2 --bulk-results-summary bulk_results_summary-2.json --output provenance/drone-calibration-translation/2026-11-19/aop-translation-audit/reproduced_registry.json --overwrite
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/audit_aop_drone_translation.py
# Header retrieval additionally requires python-irodsclient and the user's
# existing iRODS configuration; it reads only headers, never credentials/data rasters:
PYTHONPATH=/tmp/spectralbridge-irods-tools MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/fetch_aop_translation_headers.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/build_physical_aop_translation_registry.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_aop_translation_unit_bridge.py tests/test_drone_translation.py tests/test_drone_translation_registry.py
```

`coefficient_chain_checks.csv` and `audit_results.json` record exact coefficient
and sufficient-statistics verification. `training_product_inventory.csv` retains
original source identities. `training_headers/`, `training_header_retrieval.json`
and `training_header_scale_audit.csv` retain recovered unit evidence and remote
origins; no credentials are recorded. `physical_registry_verification.json`
records the unit-change tests. `translation_preflight_with_physical_registry.json`
records the remaining actual input-status refusal. 27 focused tests and Ruff
pass. Data products, production assumptions and package defaults are preserved.
