# Unmasked translated null versus the conservative 10% batch

This batch was explicitly requested as an experimental comparison despite the
unmasked Ruby BRDF fit failing its uncertainty check. It contains six translated
ENVI pairs: OLI-like and OLI-2-like outputs for Ruby, Gordon and Goldhill.

## Current files

Rasters, matching `.hdr` files, and per-product `__translation.json` records:

`archive/local/drone-calibration-translation/2026-11-19/unmasked-null-products/{site}/`

```text
ruby_20230814_unmasked_null_micasense_translated_to_oli_envi.img
ruby_20230814_unmasked_null_micasense_translated_to_oli2_envi.img
gordon_20230814_unmasked_null_micasense_translated_to_oli_envi.img
gordon_20230814_unmasked_null_micasense_translated_to_oli2_envi.img
goldhill_20230814_unmasked_null_micasense_translated_to_oli_envi.img
goldhill_20230814_unmasked_null_micasense_translated_to_oli2_envi.img
```

The separate ten-band `*_unmasked_null_corrected_micasense_envi` pairs are retained
as pre-translation backing products. All products remain EXPERIMENTAL with the
inherited HYPOTHETICAL_UNVERIFIED radiometric status. Ruby retains BRDF INVALID;
Gordon/Goldhill retain their original BRDF VALID model status. No failed QA record
has been relabeled as a pass. Datastore destination (separate from the 10% batch):

`/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_micasense_landsat_unmasked_null_20261119_v1`

Completion is recorded in `datastore_upload_complete.json` locally and remotely.
The upload includes the six translated pairs/sidecars, comparison table, complete
failed-QA records, native application evidence, registry and reproduction scripts.
The large native backing rasters remain local. Every payload file is verified by
full SHA-256 remote readback and server checksum before a completion manifest is
published. The existing 10% collection is not overwritten.

## What differs from the 10% comparison arm

The null uses the already reproduced **baseline unmasked fits**, rather than
applying the masked fit to a larger footprint. The brightness exclusion is NONE
in both fitting and application. Original footprint, camera/terrain geometry,
source NoData, topographic validity and numerical exclusions still apply.
Consequently, unmasked does not mean every raster cell receives a finite value.

We reuse the same raw prepared sources, frozen SCS+C/BRDF mathematics, camera
kernel design, reference geometry, AOP-derived fractional translation registry,
five target bands and final fraction×1000 encoding as the masked arm. Decode
stored reflectance with multiplier **0.001** (100%=1000). There is no SWIR
extrapolation, refitting of translation coefficients, clipping of tails, or
identity substitution.

All ten baseline SCS+C fits pass. The baseline Ruby BRDF has full-rank finite
coefficient estimates but fails the reference 1.96-SE criterion at native650 and
668nm. The null deliberately applies those diagnostic estimates. It waives
BRDF uncertainty acceptance only: finite, positive predictions above numerical
roundoff are still required for the reference and application denominator.
The original failed fit records remain in `{site}/baseline_brdf_qa.json`, with a
compact failure summary in translated metadata. Rank-deficient/missing estimates
are refused. Normal approved-library/correction processing is unchanged.

## Compare at the translated stage

`translated_null_vs_10percent.csv` contains 30 site/sensor/band comparisons:

- finite pixel counts for each arm;
- shared pixels and pixels available only in either arm;
- mean/median difference and RMSE on **shared finite pixels**, in fractional
  reflectance units, with difference defined as **null minus 10%**.

Compare shared pixels to assess changes in translated values, and separate
coverage counts to assess restored observations. Shared-pixel differences include
changes in fitted SCS+C and BRDF parameters, not only removal of a display mask.
The two arms need not have nested valid-pixel sets because topographic fit
uncertainty/support changes with the fit population. This is a processing
sensitivity comparison, not an independent accuracy or significance test.

## Verification and reproduction

From the repository root in the project environment:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/run_unmasked_drone_translation_null.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/verify_unmasked_drone_translation_null.py
```

To upload the verified null batch, use an environment with `python-irodsclient`
and the existing user iRODS configuration:

```bash
python examples/upload_unmasked_drone_translation_null.py
```

The uploader reuses the masked batch's transfer/readback implementation, refuses
changed verified products or differing existing remote objects, and writes a
completion manifest only after all payload readbacks pass. The new null payload
contains 34 files plus the separately verified completion manifest.

The runner reuses valid native checkpoints and translated products by signature,
verifies all translated pixels against the fractional affine equation, compares
grids, verifies original source/model hashes and tests translation reuse. The
independent verifier checks 1,920 original-value×SCS+C×BRDF calculations across
30 native site-bands, reads standard GDAL metadata, checks current product hashes,
and verifies that every existing 10% translated artifact is unchanged.

`verification.json` lists current products and checksums. Per-site
`native_application_qa.csv` reports finite output and numerical exclusions by
chunk/band. `native_complete.json` stores source/model/code identity and corrected
output hashes. `independent_algebra_checks.csv` reports the separate native
algebra checks. Software regression tests cover experimental invalid-QA opt-in,
retained INVALID status, missing uncertainty evidence, unknown coefficient-unit
rejection, direct ratio arithmetic, source NoData and nonpositive denominators.
