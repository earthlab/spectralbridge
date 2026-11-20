# Shade-excluded MicaSense to Landsat-like translations — November 19, 2026

Six full-resolution ENVI products were generated: Landsat 8 OLI-like and Landsat 9
OLI-2-like at each of Ruby, Gordon and Goldhill. These are translated drone
observations, not Landsat observations. All products retain EXPERIMENTAL status
and the source HYPOTHETICAL_UNVERIFIED calibration boundary.

## Files and units

Raster/header pairs and per-product translation JSON records are in:

`archive/local/drone-calibration-translation/2026-11-19/translated-products/{ruby,gordon,goldhill}/`

Current delivery names are:

```text
ruby_20230814_micasense_translated_to_oli_envi.img
ruby_20230814_micasense_translated_to_oli2_envi.img
gordon_20230814_micasense_translated_to_oli_envi.img
gordon_20230814_micasense_translated_to_oli2_envi.img
goldhill_20230814_micasense_translated_to_oli_envi.img
goldhill_20230814_micasense_translated_to_oli2_envi.img
```

Each has a matching `.hdr` and `__translation.json` file. The headers retain
standard scale/offset, wavelengths/FWHM, georeferencing, NoData, radiometry and
scientific-status fields. Plain `translation ...` fields expose sensor identity, coefficient version/hash,
source bands, slopes/intercepts, correction order, shade policy and model/mask
hashes to standard GDAL readers. The `translation metadata = json:...` field
(readable with SpectralBridge; some GDAL readers omit prefixed JSON) embeds
source/target identities, input/output scaling, per-band affine coefficients,
registry digest/version, evidence boundary, source/model/mask hashes,
correction order and shade policy. `run_metadata` holds the site-specific details.
The sidecar JSON remains a readable companion; required provenance is not only
encoded in the filename. EXPERIMENTAL status is retained in header metadata.

`verification.json` lists current absolute paths, SHA-256 checksums, selected
native bands, valid pixel counts and full-grid/restart verification. The six
rasters are byte-identical to the earlier long-named products; only names,
headers and provenance records changed. Earlier long-named products remain as
historical artifacts and are not the current upload manifest. Large rasters are
local analysis outputs, not committed package assets.

Each product contains only the five supported OLI/OLI-2 passbands B1–B5. Native
source indices are 1, 2, 4, 6 and 10. There are no invented SWIR bands. Stored
values are fractional reflectance ×1000: **100%=1000**, decoder **0.001**. NaN
remains NoData. The conservative pre-correction shade exclusions remain missing;
finite negative values and high corrected tails are preserved, not clipped.

The original drone prepared scale is decoded using 65535/(10000*32768), followed
by the separately audited fractional AOP-derived affine registry, then one ×1000
output encode. This avoids confusing the drone historical scale with the AOP
training divisor10000. The original packaged count-scale registry is unchanged.

## Reproduce and verify

From the repository root, using the project environment:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/run_shade_masked_drone_translations.py
```

Inputs must remain in `conservative-refitted-products/{site}/` under the same
local archive root. The script explicitly selects the audited fractional
registry under the adjacent `aop-translation-audit/` provenance directory. It
processes bounded windows, reuses completed products by source/plan/policy
signature, verifies all output values and masks against the physical-unit affine
equation, checks grids and source hashes, and tests restart reuse. Reruns rewrite
the compact verification report; existing translated products remain reused.
Changing the input, registry, output scale or rationale invalidates reuse.

## Evidence and limitations

All six products passed full-grid arithmetic/mask checks, source immutability,
grid preservation and restart checks. Site source grids are Ruby1035×1960,
Gordon2088×2948 and Goldhill2238×3165. See the JSON for band-specific finite counts.

The AOP fit provenance and 72 training-header scale proofs are in
`../aop-translation-audit/`; original/prepared drone reconstruction is in
`../scale-chain-audit/`; corrected-input hashes and independent correction
algebra are in `../conservative-refitted-products/`. Source headers omitted the
BRDF schema field; the saved models and prior application records establish
schema2, and supported kernel mathematics/policy are checked during translation.
No source headers or correction models were rewritten.

This run demonstrates consistent conditional translation, not independent
physical calibration accuracy. Same-AOP synthetic passband fits are response
relationships; correction gains and their inherited calibration uncertainty
remain. Default approved-library eligibility checks continue to reject these
experimental products. The datastore delivery is a separate sibling of the November 13 baseline:

`/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_micasense_landsat_translations_20261119_v1`

`examples/upload_shade_masked_drone_translations.py` uploads the current manifest
without overwriting differing remote objects, verifies every byte by remote
SHA-256 readback and records server checksums. A completed upload is evidenced by
`datastore_upload_complete.json` locally and in the remote collection. Earlier
long-named products are excluded. Experimental status and ×1000 decoding must
be retained in downstream brightness-correction work; numerical transfer does
not independently validate physical calibration.
