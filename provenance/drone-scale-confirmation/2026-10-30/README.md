# Drone 10,000 scaling confirmation

Date: 2026-10-30. Scope: Gordon, Goldhill and Ruby 2023 export packages. This is a read-only numerical/provenance investigation, following the user's clarification that drone imagery was resampled to 10 cm and rescaled to 10,000. No original, working H5, corrected raster or spectral library was modified.

## Conclusion

**The numerical range rescaling is confirmed. Equivalence to NEON's physical-reflectance scale is not established.** The paired exports follow a band-specific affine normalization matching each original band's observed extrema:

```
rescaled = 10000 * (original_DN - original_band_min)
                 / (original_band_max - original_band_min)
```

All ten spectral bands of all three originals have maximum 65,535. Their minima differ:

| Flight | Original minima, spectral bands 1–10 | Resulting normalization |
|---|---|---|
| Gordon | All zero | All spectral bands multiply by `10000/65535`; zero offset. |
| Goldhill | Bands 1–9 zero; band 10 (NIR) **174** | NIR uses `10000*(DN-174)/65361`; other spectral bands use `10000*DN/65535`. |
| Ruby | Band 1 **4**, band 2 **3**, band 10 (NIR) **297**; others zero | Those three bands receive different offsets and multipliers; NIR uses `10000*(DN-297)/65238`. |

This is the map obtained by putting each original band's min/max into 0–10,000. It does not, on its own, identify which number represents 100% reflectance. In particular, it is not evidence for a single common `physical = stored/10000` convention across all bands. Band-specific offsets can affect spectral shape and ratios; a common multiplicative scaling would not have that effect.

## Direct paired-pixel verification

Downloaded originals from `field-data/uas-packages/`, then the corresponding `aligned_orthomosaic.tif` from `output/summer-2023/` and `output/summer-2023-rescale/`. The latter two use identical 25 cm grids, so there is no spatial interpolation ambiguity in this paired comparison.

Across **24,387,540 finite paired spectral values** (three flights, ten bands), the normalization above has maximum absolute discrepancy **0.000780386** on the 0–10,000 output scale. That is below one float32 step at 10,000 and within the declared two-step comparison tolerance. The least-squares affine coefficients independently recover the same slopes/offsets. The original band minima were measured directly from the original UInt16 TIFFs, not guessed from the rescaled histograms.

`evidence.json` records per-band counts, coefficients, residuals, original extrema, grids, file hashes and remote origins. `verified_numeric_mapping.json` contains the invertible *numeric* maps, explicitly marked `PHYSICAL_UNITS_UNVERIFIED`. These are not approved physical calibration records.

The original TIFFs identify band 11 as alpha through their color-interpretation metadata. Comparisons above use the ten spectral bands; the alpha band was not treated as a reflectance channel. These extrema describe the stored original arrays, including their stored background values, not an independently calibrated panel observation.

## Check against the actual 10 cm inputs

Used the immutable cached `summer-2023-10cm-10k` source TIFFs from the preceding three-flight investigation. Their hashes are recorded. The earlier spatial investigation separately established the exact correspondence of their first ten bands with the H5 reflectance arrays used by the pipeline; see the [spatial investigation](../../../docs/dev/drone-spatial-integrity-investigation.md).

Independently warped each original spectral band onto the exact current 10 cm grid with GDAL bilinear resampling, then applied the original-extrema normalization. The current 10 cm products are strongly consistent with this combination. Across the ten bands, the largest median absolute difference was:

| Flight | Largest band median absolute difference | Largest band 99th-percentile absolute difference |
|---|---:|---:|
| Gordon | 0.0000213 | 0.09970 |
| Goldhill | 0.02240 | 0.30873 |
| Ruby | 0.04923 | 0.56076 |

Units here are **stored normalized numbers**, not physical reflectance. This is **not an exact replay** of the unavailable original export implementation: rare border discrepancies are substantially larger, particularly Gordon (maximum about 3,037). Full untrimmed residuals are retained in the JSON; no outlier filtering was used to improve these results. This comparison supports the same normalization convention but does not certify every interpolation or nodata choice.

For Goldhill, reconstructing the 10 cm raster directly from the original works much better than upsampling the 25 cm intermediate: the band-1 RMSE is about **0.221** versus **153.29** when bilinearly upsampling that intermediate. Thus the actual 10 cm image is not adequately described as just an upsampled copy of the archived 25 cm image.

## Physical reflectance: the remaining distinction

[MicaSense's Metashape guidance](https://support.micasense.com/hc/en-us/articles/1500012483982-Analyzing-MicaSense-data-processed-with-Agisoft-Metashape) describes the default calibrated UInt16 encoding as physical reflectance obtained by dividing DN by **32,768**; its 65,535 upper limit permits reflectance near 2. [Agisoft's workflow](https://agisoft.freshdesk.com/support/solutions/articles/31000148780-micasense-rededge-mx-processing-workflow-including-reflectance-calibration-in-agisoft-metashape-pro) distinguishes reflectance calibration from uncalibrated processing and explains the relevant calibration settings.

**Those documents establish a convention, not the settings of these particular projects.** If these originals use that calibrated convention, 32,768 represents 100% reflectance and the new value 10,000 represents approximately 200%, with additional band-specific offsets at lower values. The conditional physical conversion would be:

```
reconstructed_DN = band_min + stored * (65535 - band_min) / 10000
physical_reflectance = reconstructed_DN / 32768
```

The second line must not be applied until the original calibration/export convention is established. A custom export transform, or processing without reflectance calibration, would change its interpretation. No factor of 5,000, 10,000 or 32,768 was stamped into production metadata based solely on the range or vendor defaults.

## Export code and provenance search

- Searched current tracked notebooks, Python and R, the historical `94ef270` tree (including the old drone notebooks and helpers), and selected scaling-related Git history.
- Recovered the Data Store R alignment script at `field-data/To_Correct/macrosystems/dem_to_slope_aspect_and_raster_aligned.R`. It is a template with placeholder paths specifying **25 cm bilinear spatial resampling**, but no numerical reflectance normalization; it is not an execution record. Its source hash is in `provenance_search.json`.
- Examined the original and exported TIFF metadata and available auxiliary statistics. No physical-unit declaration or calibration conversion was exposed.
- The 10 cm collection metadata exposes an `ipc_UUID`, with no scale/offset/export equation record.
- **The exact min/max normalization script and exact 10 cm export implementation were not located.** The equation above is numerically verified from paired data; it is not presented as recovered source code or an execution log.
- The original processing report and exported metadata do not establish the original reflectance-calibration settings. The Metashape project/export configuration or a documented original calibration record remains necessary for absolute physical units.

The old “scale factor = 1” bridge metadata remains inadequate. But replacing it uniformly with a divisor of 10,000 would also make an unsupported claim and miss the observed band-specific offsets. Supporting validated recovery will require a band-aware affine calibration or an equivalent verified conversion from the original source, with nodata/alpha handling checked. This is separate from the mosaic's insufficient viewing-angle support for Ross–Li fitting.

## Reproduce

`verify.py` reads original/source/rescaled/current TIFFs and writes compact JSON evidence. It performs no correction or upload. Its arguments point to the local download root and the previously verified staged-source root:

```bash
python provenance/drone-scale-confirmation/2026-10-30/verify.py \
  --download-root /path/to/downloads \
  --staged-root /path/to/staged_sources
```

Download paths and hashes are listed per file in `evidence.json`. The code asserts identical 25 cm source/rescale grids and a float32-based bound on the paired normalization residual. The independent 10 cm warp discrepancies are reported rather than silently accepted as exact agreement.
