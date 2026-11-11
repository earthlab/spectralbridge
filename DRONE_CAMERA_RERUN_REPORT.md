# Gordon, Goldhill and Ruby camera rerun — 5 November 2026

The three sites were rerun using the newly supplied camera locations. Seven experimental corrected GeoTIFFs and matching ENVI products were produced. Gordon and Goldhill completed all correction branches; Ruby completed topographic correction, while its BRDF branches failed the unchanged prediction-uncertainty checks. This completes the requested conditional rerun, not scientifically approved production processing.

| Site | Topographic only | BRDF only | Combined |
| --- | --- | --- | --- |
| Gordon | Experimental output | Experimental output | Experimental output |
| Goldhill | Experimental output | Experimental output | Experimental output |
| Ruby | Experimental output | Unsupported | Unsupported |

## Products and evidence

Final large products are under `archive/local/drone-camera-rerun/2026-11-05/photo_clock_v1/<site>/<branch>/`. Branch names are `topographic_only`, `brdf_only`, and `combined`. The [product catalog](provenance/drone-camera-rerun/2026-11-05/product_catalog.json) lists the seven accepted experimental GeoTIFFs, exact paths and SHA256 hashes. Ruby diagnostic directories can contain invalid or partial ENVI files; these are inspection artifacts, not accepted corrected products. The preliminary geometry run outside `photo_clock_v1` is not the final result.

The [illustrated PDF](output/pdf/drone-camera-rerun-2026-11-05.pdf) contains stage comparisons, camera coverage, support maps and quantitative results. [Compact evidence and executable scripts](provenance/drone-camera-rerun/2026-11-05/) preserve inputs, geometry, models, metrics and verification. Original rasters, camera CSVs, previous products and the shared field manifest were not overwritten. No production upload, approved library or translation was performed.

## Source and geometry decisions

- Camera tables came from `/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023/`, within the Gordon, Goldhill and Ruby ExportPackage folders. Remote checksums and local hashes are recorded in `current_remote_inputs.json`.
- All 16,440 camera PhotoIDs uniquely matched original photo metadata: Gordon 572 positions/5,720 band records; Goldhill 565/5,650; Ruby 507/5,070. Photos support 15 August 2023 for all three, including Ruby despite the field manifest's 16 August date. Solar geometry used matched-photo midpoint times: Gordon 20:58:39.5, Goldhill 19:53:12.5, Ruby 18:53:05.5. UTC is an explicitly unverified clock scenario, not a newly certified timestamp convention.
- Goldhill's CSV declares EPSG:5070. Original processing-report and footprint evidence independently support direct EPSG:26913 interpretation. The override and evidence are explicit; the CSV was not modified. Gordon and Ruby declare EPSG:26913.
- The newly supplied parent folder has 25 cm terrain derivatives. These were rejected for the 10 cm imagery. Six slope/aspect sidecars retrieved from `output/summer-2023-10cm-10k` exactly match earlier verified terrain hashes; aligned DEM identities and all grids were checked.
- Original-source fixed-range preparation was reused: 10 cm float32 imagery, `stored = original_DN * 10000 / 65535`, with zero offset and no image min/max stretch. This storage convention does not establish physical calibration. Correction retains the previously documented DN/32768 hypothesis, equivalent to `conditional_fraction = stored * 0.0001999969482421875`. Every corrected header remains `HYPOTHETICAL_UNVERIFIED` and `EXPERIMENTAL`.
- The existing Goldhill research adapter uses the shared correction driver, RossThick/LiDenseR kernels and conditioned SCS+C policy. Nadir rectangular footprints and center-weighted mixtures of individual camera kernels remain explicit scenarios. Camera rotation matrices are validated and retained, but pose convention, actual mosaic contributors/blending and vertical datum are not independently established. Evaluation polygons plus a 2 m Manhattan buffer were excluded from fitting; uncertainty uses 20 m spatial groups. No defaults or guards were relaxed to obtain success.

Geometry covers 5,898,343 Gordon, 6,683,905 Goldhill and 1,993,472 Ruby ground pixels. Respectively 58, 39 and zero source pixels lack terrain. Ruby uses the available clipped original orthomosaic; cameras outside the crop remain potential contributors.

## Scientific results and limits

Ruby's BRDF-only models reject 444, 475, 650 and 668 nm; combined correction rejects 650 and 668 nm. The recorded reason is nonpositive or cancellation/uncertainty-dominated model prediction. At combined 650 nm the fit has rank 3, condition number 464.44 and reference prediction 0.012294 with spatial-cluster standard error 0.009395 across 60 groups. The uncertainty does not resolve a positive reference. Millions of pixels do not supply millions of independent observations. No identity image, alternative tuning or partial-band output was presented as a successful BRDF correction.

Goldhill still has large correction tails. In conditional fractional units its combined native maxima are 2.424336 at 650 nm and 1.771414 at 717 nm, with a maximum 650 nm multiplier of 21.545017. On shared all-ten-band support the maxima are 1.556842 and 0.689487. This population change is not proof of scientific improvement. Gordon combined maxima are 0.949671 and 0.495208; Ruby topographic-only maxima are 1.021902 and 0.515393. No analytical values were clipped. The evidence includes native and common-support metrics and 140 bounded extreme-source records with exact source row/column and product identity.

The established **302 half-diameter polygons** and 200,363 pixel memberships are preserved. The 10,360 polygon-band summaries are experimental diagnostics, not an approved physical spectral library. Per-stage support differs. Ruby's shared support covers only raw and topographic products.

## Verification and reproduction

The seven GeoTIFFs exactly match their ENVI values: **395,908,190 finite values** checked in bounded windows, plus missing-data positions, affine grids, CRS and wavelengths. Raw working candidates exactly match the prepared TIFFs. Input, implementation and output hashes were verified. Geometry and correction restart runs reused valid checkpoints only after signature/hash checks. Every experimental header was rejected by the approved-library gate. **49 focused camera, geometry and correction regression tests passed.** This is not a claim that the unrelated full release suite is green.

Run from the repository root with the existing scientific environment and authenticated GoCommands client. The scripts freeze their explicit sources and reuse checkpoints:

```bash
.venv/bin/python provenance/drone-camera-rerun/2026-11-05/stage_camera_inputs.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/prepare_rerun.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/reconstruct_sites.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/run_corrections.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/build_qa.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/compare_support.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/drone-camera-rerun/2026-11-05/verify_rerun.py
```

These are local research scripts, not a portable production notebook: they depend on the hashed original preparation, cached DEMs and previously preserved research adapter documented in their input manifests. Next work is to establish calibration/contributor evidence and resolve Ruby's BRDF reference uncertainty without weakening acceptance checks. Goldhill's extreme corrections still require scientific review before approved downstream use.
