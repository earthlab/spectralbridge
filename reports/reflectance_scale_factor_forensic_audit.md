# SpectralBridge Reflectance Scale-Factor Forensic Audit

Audit date: 2026-10-02  
Repository: earthlab/spectralbridge  
Audited revision: 06998790f4c0572e1dd5a2ecd71f0dad8db5d6f8  
Scope: NEON reflectance scaling in BRDF and topographic correction  
Confidence labels: HIGH means directly established by executable source, git history, a retained prompt, or an inspected artifact; MEDIUM means strongly implied by multiple facts; LOW means inference only.

## Executive summary

The September 2026 change discovered by the coworker is the repair point, not the origin.

The divisor-versus-multiplier defect entered SpectralBridge on 2025-12-05 in commit 37207cff669e6eeece1bea7b0b2bbadf87d4b327, merged through pull request 235. That change first moved BRDF and topographic correction into a nominally unitless reflectance domain, but it implemented:

    unitless = stored_value * Scale_Factor

The inspected NEON R10C HDF5 file stores integer-like reflectance counts and has Scale_Factor = 10000. Its correct interpretation is:

    unitless = stored_value / 10000

For example, stored 1172 means physical reflectance 0.1172. The defective implementation produced 11,720,000. Absolute reflectance gates of 1.2 and later 2.0 then rejected nearly every ordinary positive NEON value from BRDF fitting.

This was not inherited from the exact HyTools revision named in HYTOOLS_PROVENANCE.md. HyTools commit 31286d64541791a9815d29443a33726fa4d54031 reads and corrects the stored HDF5 values directly; its NEON correction path does not read or divide by Scale_Factor.

The continuous SCS+C and multiplicative BRDF mathematics are largely invariant to a consistent constant scaling. The defect became scientifically consequential because pixel selection, validity gates, tolerances, offsets, and persisted model interpretation are not scale-invariant. The repository contains direct real-scene evidence: a pre-repair R10C validation artifact has all 426 volumetric and geometric BRDF coefficients equal to zero, while isotropic coefficients are only zero or one. That is the expected fingerprint of a fit that excluded positive reflectance and retained initialized defaults.

Commit 0985382583f74fc8fcf2ef402b60b771220103d9 on 2026-07-22 reduced the conspicuous symptom by preserving input data and treating invalid BRDF factors as neutral. It did not repair scaling. After that point, affected products could look plausible and retain valid pixels while BRDF was effectively a no-op and scale-invariant topographic correction still produced small changes.

Commit c511efe110176a8bee980c87d4acbed3625dae5f on 2026-09-17 repaired the convention by treating values greater than one as storage divisors and fractional values as multipliers. It added direct coverage for Scale_Factor = 10000.

Updating the package alone does not repair existing products. Restart-safe processing may reuse a stale BRDF model and every descendant derived from it. Models made before c511efe from real NEON divisor-style data should be considered presumptively affected until provenance and coefficients show otherwise. The minimum safe response is an inventory and targeted regeneration beginning at the BRDF model, not an indiscriminate redownload or rerun of all raw data.

No production code, tests, existing documentation, or data were modified for this audit.

## Key findings

1. HIGH — The inspected NEON file uses Scale_Factor = 10000 as a divisor. A sampled 662.221008 nm band has median stored value 1172, meaning 0.1172 physical reflectance.
2. HIGH — QA normalization entered first, on 2025-10-29 in commit 0687735992607cde87a627a7305d69bfd7093b67, using a median-greater-than-1.5 heuristic to divide display data by 10000.
3. HIGH — Scientific correction scaling entered later, on 2025-12-05 in commit 37207cff669e6eeece1bea7b0b2bbadf87d4b327, and used the wrong direction for real NEON metadata.
4. HIGH — Tests added with the December change used only the fractional convention Scale_Factor = 1e-4, so they validated the implementation’s assumption rather than the real file convention.
5. HIGH — HyTools at the exact audited upstream revision operates on stored reflectance and never divides NEON Reflectance_Data by 10000 before BRDF or topographic correction.
6. HIGH — The correction equations can be scale-invariant, but absolute gates are not. Under the historical conversion, a synthetic scene admitted zero of 126 valid observations per band to BRDF fitting.
7. HIGH — A committed pre-repair R10C artifact shows complete volumetric and geometric coefficient collapse across 426 bands.
8. HIGH — The July 2026 fix stopped many valid pixels from becoming -9999 but left the wrong conversion intact; it made the failure less visible.
9. HIGH — The September 2026 coworker change c511efe is the repair. Its retained prompt records an intent to rerun Yellowstone flight lines and look for better BRDF correction.
10. HIGH — Cached models and descendants are the principal current operational risk. Acquisition year alone cannot identify affected products; generation revision and provenance are required.

## What HyTools actually does

The exact source revision named by SpectralBridge provenance was inspected:

    31286d64541791a9815d29443a33726fa4d54031

The executable trace is:

    NEON Reflectance_Data
        -> hytools/io/neon.py open_neon
        -> HyTools.load_data and get_band/get_chunk/get_line
        -> topographic and BRDF fitting on stored values
        -> multiplicative correction factors applied to stored values
        -> scripts/image_correct.py writes float ENVI values

Specific findings:

- src/hytools/io/neon.py lines 26-72 binds Reflectance_Data directly and does not read Scale_Factor.
- src/hytools/base.py lines 127-142 builds the no-data mask from the stored dataset. load_data at lines 219-222 reads the HDF5 array directly.
- Band, chunk, and line accessors retrieve stored values and then apply configured corrections.
- src/hytools/topo/scsc.py lines 60-79 and src/hytools/topo/c.py lines 45-79 fit topographic coefficients against the values returned by the reader.
- SCS+C application multiplies those values by a geometric ratio; it does not divide by 10000 first.
- src/hytools/brdf/flex.py fits kernel coefficients against the values returned by the reader and applies a modeled nadir-to-observed ratio to those values.
- src/hytools/masks/calc_apply.py contains normalized-difference and ancillary masks that are scale-invariant. Generic absolute band thresholds would be scale-sensitive if a configuration used them.
- scripts/image_correct.py lines 79-125 writes corrected float values without a physical-unit conversion or a reflectance scale-factor round trip.

The upstream path therefore does not support the hypothesis that SpectralBridge inherited stored-times-10000 behavior from HyTools.

Side-by-side:

| Stage | HyTools 31286d6 | Current SpectralBridge | Classification |
|---|---|---|---|
| HDF5 read | Stored values | Stored values in NeonCube | Same representation |
| Scale_Factor read | Not used in correction | Read and retained | Representational difference |
| Topo fit | Stored values | Physical unitless values | Mathematically equivalent when gates and tolerances agree |
| Topo apply | Ratio times stored values | Convert to physical, apply ratio, convert back | Mathematically equivalent under a consistent scale |
| BRDF fit | Stored values, subject to configured masks | Physical values with rho_min/rho_max fit gate | Potentially consequential because gates differ |
| BRDF apply | Ratio times stored values | Convert, apply ratio, convert back | Mathematically equivalent for a valid equivalent model |
| Correction order | Later configured corrections can see earlier corrections | BRDF model is fitted before topo application | Potentially scientifically consequential and separate from scaling |
| ENVI write | Float corrected values without scale round-trip metadata | Stored-scale values plus reflectance scale factor | Representational and downstream-contract difference |

The use of physical unitless reflectance in current SpectralBridge is not inherently wrong. It is a deliberate departure from HyTools representation that can be mathematically equivalent. The historical bug was the wrong interpretation of metadata combined with absolute physical gates.

## What SpectralBridge currently does

At audited revision 06998790, the normal NEON path is:

1. src/spectralbridge/io/neon.py:_extract_scale_factor, lines 133-152, reads the raw metadata value.
2. src/spectralbridge/io/neon.py:reflectance_to_unitless_multiplier, lines 155-177, maps 10000 to 1/10000, maps 1e-4 to 1e-4, and maps 1 to 1.
3. stored_to_unitless, lines 180-184, multiplies the stored array by that normalized multiplier.
4. unitless_to_stored, lines 187-193, divides by the same multiplier.
5. src/spectralbridge/neon_cube.py:NeonCube retains raw stored values and records scale_factor; build_envi_header records reflectance scale factor.
6. src/spectralbridge/corrections.py:fit_scs_c_coefficients, beginning at line 454, converts chunks to physical reflectance before fitting.
7. apply_topo_correct, beginning at line 557, converts to physical reflectance, applies the topographic factor, and converts back at line 692.
8. fit_and_save_brdf_model, beginning at line 1005, converts the full fitting reflectance at lines 1075-1077 and applies rho_min/rho_max, with current default rho_max = 2.0.
9. apply_brdf_correct, beginning at line 700, converts each chunk at line 819, applies the reference-to-pixel factor, and converts back at line 988.
10. src/spectralbridge/brdf_topo.py:apply_brdf_topo_core writes corrected stored-scale float data and adds the raw scale value to the ENVI header near line 338.
11. src/spectralbridge/pipelines/pipeline.py:convolve_resample_product, beginning at line 892, convolves those stored-scale values linearly and propagates the source header scale.
12. src/spectralbridge/parquet_export.py:_process_chunk_to_dataframe, beginning at line 281, reshapes raster samples directly; it does not convert them to physical reflectance before writing Parquet.
13. src/spectralbridge/qa/stages.py:_scale_factor, beginning at line 129, and src/spectralbridge/qa_plots.py:_unit_reflectance_cube, beginning at line 2339, interpret the ENVI scale factor as a divisor for physical QA.

Important current limits:

- Active QA is correct for ordinary NEON header value 10000, but it does not share the convention-aware helper. A header containing literal multiplier 1e-4 would be divided by 1e-4 and misinterpreted.
- src/spectralbridge/envi.py still contains the older median-greater-than-1.5 heuristic, but repository-wide caller search found no active callers. It does not currently double-divide the normal pipeline.
- read_neon_reflectance_unitless exists in io/neon.py but has no current production caller; the streaming cube path uses the paired conversion helpers.
- MAX_UNITLESS_REFLECTANCE = 1.2 remains declared in corrections.py line 52, while current BRDF fitting defaults to rho_max = 2.0. The constant is not active in that path.
- Parquet and bulk computations receive stored-scale values unless another workflow explicitly transforms them.
- The optional brightness offset is unit-sensitive because it is applied after correction in stored units.
- Drone TIFF-to-HDF bridging uses scale factor 1.0. Drone translation is a separate affine model with count-scale compatibility checks and is not part of the normal NEON correction path.

## Historical timeline

| Date | Commit and attribution | Files and change | Apparent reason and prompt | Scope | Confidence |
|---|---|---|---|---|---|
| 2025-10-27 | b5969f5b7fa55bba8a365c1b6a8f82497b1eba61; Git author and committer Ty Tuff; PR 124, Codex branch | Added src/cross_sensor_cal/corrections.py. Corrections consumed stored values. | Add a NEON-only correction module. No retained prompt. | Scientific correction, no explicit scale conversion | HIGH |
| 2025-10-28 | 328922b22aef5c067659f43818e4fab78a3676a6; author and committer Ty Tuff; PR 133 | Changed corrections.py and pipeline.py; persisted BRDF coefficients. | Persist and reuse model. No retained prompt. | Scientific correction, still native scale | HIGH |
| 2025-10-29 16:33 -06:00 | 0687735992607cde87a627a7305d69bfd7093b67; author and committer Ty Tuff; PR 166 | Changed qa_plots.py, QA CLI, tests, docs. Added median above 1.5 then divide by 10000 for display. | PR states conversion of the QA spectral panel to unitless reflectance. | QA and visualization only | HIGH |
| 2025-10-29 17:05 -06:00 | 856b9f1abb8c2a015e0c21b95148b789e379aa44; author and committer Ty Tuff; PR 167 | Changed brdf_topo.py and qa_plots.py. Added independent raw/corrected unit detection, ratio plots, and guards. | Improve diagnostics and protect correction. No retained prompt. | Scaling change remained QA-only | HIGH |
| 2025-10-29 evening | 5b5e9032fe64cf7b2e02c5813147455205cfaff7, b62c5c4b93fb3f4e572d52f53c075bcca401bed7, 909f4c0a223a816683462b181d51d569a9492f9e | Hardened spectra handling, added QA metrics, and moved ENVI helpers. | QA expansion. No retained prompt. | QA only | HIGH |
| 2025-11-01 | 98a259026a467570f4b0e92481341e4ee51454db | QA rewrite removed active use of the heuristic, leaving the helper without current callers. | QA metrics and brightness documentation. | QA only | HIGH |
| 2025-12-05 09:36 -07:00 | 37207cff669e6eeece1bea7b0b2bbadf87d4b327; author and committer Ty Tuff; merged as 01e87458d6beb75218b525da1278902c42dccc41 through PR 235, Codex branch | Changed brdf_topo.py, corrections.py, envi_writer.py, io/neon.py, neon_cube.py, tests/test_brdf_scale.py, and docs. Added stored times scale conversion, 1.2 gate, scale header propagation, and tests only for 1e-4. | PR title says strengthen regression coverage; public body emphasizes shape and type. No 2025 prompt survives. | First scientific scaling; defect introduced | HIGH |
| 2025-12-10 00:10 -07:00 | 4a4df5e560f9ab02f843d26b3e9eeae333dd8f1b; author and committer Ty Tuff; PR 246, Codex branch | Major corrections.py refactor: SCS+C, NDVI bins, BRDF reference/pixel factor, rho_max 2.0; retained wrong conversion. | Clarify algorithm and defaults. No retained prompt. | Scientific correction | HIGH |
| 2026-07-22 17:41 -06:00 | 0985382583f74fc8fcf2ef402b60b771220103d9; author and committer Aashish75, Cursor co-author | Changed brdf_topo.py, corrections.py, pipeline and diagnostic scripts. Preserved input and neutralized invalid factors; retained wrong conversion. | Retained July 13 prompt reports raw 87 becoming -9999 and asks for root cause and tests. | Scientific symptom mitigation | HIGH |
| 2026-08-15 | 21514d1798563ec52cbfa5b29f59cde2c99321f6; author and committer Ty Tuff | Added pipeline validation and safer numeric behavior. A committed R10C artifact was later generated from pre-repair code. | Validation work. | Validation, defect still present | HIGH |
| 2026-09-17 13:01 -06:00 | c511efe110176a8bee980c87d4acbed3625dae5f; author and committer Aashish75, Cursor co-author | Added convention-aware helpers, direct 10000 tests, docs and P79; also contained unrelated half-route work. | Retained prompt asks to correct the issue and rerun Yellowstone lines for better BRDF. | Scientific repair | HIGH |

The scientifically relevant eras are:

| Era | Behavior | Expected product signature |
|---|---|---|
| 2025-10-27 through 2025-12-04 | Native stored-scale fitting; earliest BRDF output formulation did not preserve magnitude | No divisor bug, but separate early BRDF correctness risk |
| 2025-12-05 through 2025-12-09 | Wrong multiplication and 1.2 fit/application expectations | Collapsed fits and possible widespread -9999 |
| 2025-12-10 through 2026-07-21 | Wrong multiplication, 2.0 fit gate, improved output formula | Collapsed BRDF fit; topographic correction may remain active |
| 2026-07-22 through 2026-09-16 | Wrong multiplication plus neutral fallback and input preservation | Plausible coverage, frequently topo-only or BRDF no-op |
| 2026-09-17 onward | Convention-aware conversion | Coherent 10000 and 1e-4 round trip, provided stale artifacts are not reused |

## Prompt and authorship reconstruction

The provenance record is incomplete by design. PROMPT_LOG.md was created in March 2026 and explicitly says older prompts were not backfilled. There is no surviving prompt for the December 2025 conceptual decision.

For the December origin:

- Git attributes 37207cff to Ty Tuff as author and committer.
- The pull request was opened by account ttuff from a Codex-named branch and carried a Codex task label.
- The public pull-request description emphasizes regression shape and type, while the diff also changes the scientific unit domain and adds an absolute gate.
- No surviving evidence establishes whether the multiplier convention was directly requested by a human, inferred by an agent, or introduced during review.

The defensible language is therefore: the defect entered the repository in a Codex-associated pull-request workflow attributed by Git to Ty Tuff. Intent cannot be assigned.

The retained failure-and-repair sequence is:

    2026-07-13 prompt
        "raw=    87.00  corr= -9999.00"
        "We need to figure this part out before running the entire pipeline."
        "Can we run some some comprehensive tests for this stage and diagone the root cause"
            |
            v
    2026-07-22 commit 0985382
        preserve input values and neutralize invalid correction factors
        but retain stored times Scale_Factor
            |
            v
    observed later
        corrected products preserve coverage but BRDF coefficients can remain collapsed
            |
            v
    2026-09-17 prompt
        "okay lets correct this and push all the chnages to github."
        "I will pull spectralbrdige and run the pipeline again for those yellow stone flightlines."
        "LEts see if we get better BRDF correciton"
            |
            v
    2026-09-17 commit c511efe
        convention-aware scaling and tests for Scale_Factor = 10000

The closest retained prompt before c511efe says “correct this” and presupposes an earlier diagnosis that is not itself in the prompt log. The next prompts switch to bulk results, drone calibration, and documentation; they do not supply additional scaling rationale.

AI metadata:

- July 2026 commit: Git names Aashish75; commit records Cursor co-authorship. The prompt log entry itself predates mandatory AI-system fields, so model is not recorded.
- September 2026 repair: prompt log records AI system Cursor Agent and Model: Not recorded.
- December 2025 origin: Codex branch/task metadata exists, but no prompt or model record survives.

## When QA scaling entered the project

QA scaling entered on 2025-10-29 in 0687735992607cde87a627a7305d69bfd7093b67.

The decisive logic was conceptually:

    if median reflectance > 1.5:
        display_reflectance = reflectance / 10000

The purpose documented by the pull request was physical interpretation in the QA spectral panel. Commit 856b9f1 then applied unit detection independently to raw and corrected data and added ratio diagnostics. Later commits hardened the helper and moved ENVI utilities.

This establishes:

- QA recognized count-scale NEON reflectance before scientific correction did.
- The heuristic conversion was initially a presentation and interpretation concern.
- The QA helper did not directly migrate through a rename into corrections.py.
- A separate December implementation introduced explicit scale metadata and scientific conversion.

The proposed narrative “QA divided by 10000, then that exact helper migrated into correction” is therefore too strong. The evidence supports conceptual proximity, not a direct code lineage. There is no source-level evidence that the QA function was copied into the correction implementation.

The old heuristic remains in src/spectralbridge/envi.py, but current caller search found only its definition/export and no active production use. It cannot currently interact with the newer helper in the normal pipeline, so no present double division was found.

## When scaling entered scientific correction

Scientific scaling entered in 37207cff669e6eeece1bea7b0b2bbadf87d4b327 on 2025-12-05.

The decisive conversion was:

    data_unitless = data * scale_factor

and the reverse conversion was:

    data_stored = data_unitless / scale_factor

That pair is correct if scale_factor is the physical multiplier 1e-4. It is wrong if scale_factor is the storage divisor 10000.

The same commit introduced:

- _extract_scale_factor;
- read_neon_reflectance_unitless;
- scale_factor on the cube;
- reflectance scale factor in ENVI headers;
- unitless-domain correction fitting and application;
- MAX_UNITLESS_REFLECTANCE = 1.2;
- tests that create stored data as unitless divided by 1e-4.

This is the first commit where Scale_Factor changes BRDF and topographic scientific processing rather than QA display. Confidence is HIGH.

The December 10 refactor retained the conversion and raised the default fit ceiling to 2.0. Since ordinary stored positive values multiplied by 10000 still far exceed 2.0, that change did not repair the model-selection failure.

## Why the change appears to have happened

The likely technical goal was scientifically defensible: put reflectance-dependent fitting, validation, and thresholds in a physical unitless domain while preserving the existing stored-scale ENVI contract. That is supported by function names, comments, the new unitless maximum, metadata propagation, and round-trip tests.

The implementation failure was representational:

- some remote-sensing formats express scaling as a multiplier such as 0.0001;
- the actual inspected NEON file exposes Scale_Factor = 10000 as a divisor;
- tests modeled only the multiplier convention;
- no real-header fixture asserted that stored 5000 becomes physical 0.5.

The historical evidence does not establish that QA code directly caused the correction change. It does show that physical 0-to-1 interpretation was already present in QA and that the later correction work adopted the same conceptual physical domain with a new implementation.

Conclusion on causal narrative:

- HIGH — QA normalization preceded scientific normalization.
- HIGH — scientific normalization was implemented independently and incorrectly for real NEON metadata.
- MEDIUM — familiarity with QA’s physical-unit interpretation may have influenced the correction design.
- LOW — the QA helper itself was copied or mechanically migrated into correction. No evidence supports that stronger claim.

## Numerical pipeline trace

Representative input:

    stored reflectance = 5000
    raw Scale_Factor metadata = 10000
    physical reflectance = 0.5

### HDF5 to NeonCube

src/spectralbridge/io/neon.py extracts 10000. src/spectralbridge/neon_cube.py retains the pixel as 5000 and scale_factor as 10000. No division occurs at ingestion.

### Raw ENVI

NeonCube.build_envi_header records:

    reflectance scale factor = 10000

The raw ENVI pixel remains 5000. Pixel and metadata agree under divisor semantics.

### Topographic fitting

fit_scs_c_coefficients calls:

    stored_to_unitless(5000, 10000) -> 0.5

The fit sees 0.5. The literal operation is multiplication by the normalized multiplier 0.0001, which is equivalent to division by 10000.

### BRDF fitting

fit_and_save_brdf_model also converts stored values to physical values. The representative 0.5 passes current 0 to 2.0 fit selection. Model coefficients are fitted in physical-reflectance units.

Current SpectralBridge fits the BRDF model before applying topographic correction. That order differs from a sequential HyTools configuration in which a later fit can see earlier corrections.

### Topographic application

apply_topo_correct converts 5000 to 0.5, applies topographic factor T, then calls unitless_to_stored:

    0.5 times T -> 5000 times T

The reverse is multiplication by 10000, implemented as division by normalized multiplier 0.0001.

### BRDF application

apply_brdf_correct receives the topo-corrected stored value 5000 times T, converts it to 0.5 times T, applies BRDF factor B, and converts back:

    0.5 times T times B -> 5000 times T times B

### Corrected ENVI

apply_brdf_topo_core writes the corrected stored-scale float value and retains reflectance scale factor 10000 in the header. A configured brightness offset is applied after correction in the stored representation, so its numeric unit must match that representation.

### Convolution

convolve_resample_product performs a linear weighted spectral integration on stored-scale values. Its result is:

    convolution of 5000 times T times B

and the output header retains the scale factor. Linear convolution commutes with a uniform scale. The important contract is that downstream readers must still honor the header.

### Drone translation

Normal NEON processing does not route through drone translation. The drone TIFF bridge assigns scale factor 1.0. src/spectralbridge/drone_translation.py applies affine relationships trained for its recorded numeric range and rejects incompatible fractional ranges. Applying these count-scale coefficients to newly unitless NEON values would be wrong, but no such normal route was found.

### Spectral-library and Parquet extraction

parquet_export.py reads the raster block and writes the reshaped values directly. It does not divide by the ENVI header scale. Polygon extraction and bulk spectral-library analysis likewise consume the supplied table or raster values. For a standard NEON corrected raster, a Parquet value near 5000 times T times B remains in stored-count units.

This is not necessarily an implementation error, but the unit contract must be explicit. The physical value is obtained by division by 10000.

### QA

qa/stages.py and qa_plots.py mask no-data, read the header factor, and divide the valid array by 10000. QA sees:

    0.5 times T times B

The current active path therefore has one conversion into physical units during correction, one conversion back for storage, and a separate conversion by QA for interpretation.

### Double-scaling and mismatch audit

| Risk | Finding |
|---|---|
| Double division | No active current path found. The legacy median heuristic has no callers. |
| Failure to multiply back | Not found in current topo or BRDF application; both call unitless_to_stored. |
| Pixel/header disagreement | Not found in the normal current NEON round trip. Raw, corrected, and convolved outputs remain stored-scale with header 10000. |
| Heuristic applied to unitless data | No active caller found. Future reuse remains a maintenance risk. |
| Convolution in unexpected units | It receives stored units by design and propagates scale metadata. |
| Parquet in unexpected units | Plausible consumer risk: values remain stored-scale and table columns do not intrinsically perform header conversion. |
| QA scale misinterpretation | Correct for divisor-style 10000; wrong for multiplier-style 1e-4 headers because QA uses divisor semantics rather than the shared policy. |

## Scale-invariance analysis

Let physical reflectance be rho and stored reflectance be s:

    s = k rho

For the inspected file, k = 10000.

### Continuous topographic correction

SCS+C fits:

    rho = a x + b
    C = b / a

Under scaling by k:

    s = k a x + k b
    C_stored = k b / k a = C

The application factor depends on geometry and C and multiplies reflectance. With the same selected pixels, the corrected stored result equals k times the corrected physical result. The continuous topographic equation is scale-invariant.

Exceptions include absolute tolerances such as np.isclose(a, 0), numeric precision, clipping, and any scale-dependent pixel gate.

### Continuous BRDF correction

For a linear kernel model:

    rho = beta_iso + beta_vol K_vol + beta_geo K_geo

Uniform scaling multiplies every beta by k. Both modeled reference and modeled pixel reflectance scale by k, so:

    R_ref / R_pixel

is unchanged. Multiplying observed reflectance by this ratio is scale-invariant when fitting, validation, and application use a consistent representation.

### Normalized masks

NDVI and other normalized differences are invariant:

    (k A - k B) / (k A + k B) = (A - B) / (A + B)

Ancillary geometry masks are independent of reflectance scale.

### Non-invariant decisions

| Operation | Intended unit | Scale sensitivity |
|---|---|---|
| rho_min and rho_max | Physical unitless reflectance | Directly changes fit membership |
| MAX_UNITLESS_REFLECTANCE = 1.2 | Physical unitless reflectance | Directly changes validity if used |
| QA plausible_max = 1.2 | Physical unitless reflectance | Changes diagnostic classification, not correction |
| Absolute band-mask limits | Whatever domain configuration assumes | Directly changes mask |
| np.isclose on fitted slope or denominator | Numeric domain of operand | Can choose a different fallback after scaling |
| Additive brightness offset | Stored units in current pipeline | Cannot be reused unchanged in physical units |
| Epsilon and denominator floors | Function-specific domain | Can change factor rejection |
| No-data equality | Stored sentinel | Must be applied before conversion |
| Translation intercepts | Training-data units | Affine models are not scale-invariant unless coefficients transform |

Therefore outcome 1 from the brief is only partly true: the conversion round trip is neutral for the continuous correction mathematics. Outcome 2 is true for the historical implementation because absolute selection logic saw the wrong domain and changed the fitted scientific model.

## Experimental comparison

Temporary, untracked analysis scripts used current production functions. No production code was modified.

The synthetic scene contained two bands, varied illumination and BRDF geometry, and physical reflectance levels:

    0.01, 0.05, 0.20, 0.50, 0.90, 1.10, 1.30

Variants:

- A — current SpectralBridge: stored counts, metadata 10000, convention-aware conversion, correction, conversion back.
- B — native physical scale: metadata 1, same continuous correction, gates disabled.
- C — native stored scale: metadata 1, with the physical 2.0 ceiling converted to the equivalent stored ceiling 20000.

Fit membership:

| Variant | Band 1 | Band 2 |
|---|---:|---:|
| A current | 126 of 126 | 126 of 126 |
| B native physical | 126 of 126 | 126 of 126 |
| C native stored with equivalent gate | 126 of 126 | 126 of 126 |
| Historical stored times 10000 with rho_max 2.0 | 0 of 126 | 0 of 126 |

Topographic coefficients:

| Variant | Band 1 C | Band 2 C |
|---|---:|---:|
| A current | -29.5235405 | 22.1558838 |
| B and C equivalent native | -29.5235081 | 22.1558876 |

After normalizing coefficient units, the maximum BRDF coefficient difference was approximately 8.28e-8.

Output agreement between correct variants:

| Metric | Value in stored counts |
|---|---:|
| MAE | 0.0003403 |
| RMSE | 0.0006568 |
| Maximum absolute difference | 0.0029296875 |
| Correlation | approximately 0.99999999999999 |

The current BRDF factors ranged approximately from 0.97309 to 1.02747 in this synthetic scene.

With a correctly converted physical gate of 1.2, the deliberately bright 1.3 row was excluded from one band: 108 of 126 observations remained. This is expected threshold behavior and is separate from the convention defect.

A simulated historical neutral BRDF model differed from the fully fitted correction by RMSE 103.88 stored counts, or 0.010388 physical reflectance, with maximum difference 363.08 counts, or 0.036308 physical. These values characterize only the synthetic fixture and must not be interpreted as a production effect estimate.

An edge-case test with no-data, negative, zero, and physical reflectance above 2.0 confirmed:

- no-data remains no-data;
- current rho_max affects fitting membership;
- negative, zero, and above-2 values are not globally clipped during application;
- current and equivalently gated native-scale outputs agree within floating-point error.

Focused repository tests:

    tests/test_brdf_scale.py
    tests/test_brdf_topo_streamlined.py

Result:

    19 passed

## Scientific consequences

### Topographic correction

The core SCS+C coefficient C and multiplicative factor are scale-invariant. Historical wrong scaling therefore did not necessarily destroy the topographic correction. It could still fail through absolute tolerance branches or invalid-data handling, but it was much less vulnerable than BRDF fitting.

### BRDF correction

BRDF continuous mathematics is scale-invariant; BRDF model selection was not. The wrong conversion placed normal positive values far above rho_max. The dominant consequence is not a uniformly too-bright or too-dark output. It is a missing, default, or neutral BRDF model.

### Combined output

After July 2026, an affected corrected raster can:

- preserve nearly all valid pixels;
- remain close in magnitude to raw reflectance;
- show small topographic changes;
- carry apparently reasonable scale metadata;
- nevertheless lack the intended BRDF adjustment.

This makes visual inspection alone insufficient.

### Downstream products

Convolution is linear and will not repair or amplify a pure constant scale mismatch if metadata is honored. It will faithfully propagate the spatial and spectral consequences of a missing BRDF correction.

Parquet and spectral-library products derived from an affected corrected raster inherit that scientific result. Their numeric magnitudes normally remain count-scale. Drone/NEON comparisons can be biased by missing BRDF normalization, especially where view geometry differs, even if the downstream drone translation itself is not part of the failing code path.

### Real artifact evidence

The file:

    docs/validation/artifacts/r10c-l002-20210915/qa/stages/02_correction_parameters/stage_qa.json

records a pre-c511efe generating revision d88e8d... and summarizes 426 bands:

| Coefficient | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Volumetric | 0 | 0 | 0 |
| Geometric | 0 | 0 | 0 |
| Isotropic | 0 | 0 | 1 |

That is direct evidence of complete real-scene BRDF coefficient collapse.

The paired correction QA reports slope approximately 1.000028 and ninety-ninth percentile absolute physical change approximately 0.003894. This is consistent with neutral BRDF plus modest topographic correction. It does not establish that BRDF worked.

## Expected fingerprints in existing results

The most diagnostic fingerprints are:

1. BRDF model JSON with all or nearly all volumetric and geometric coefficients equal to zero.
2. Isotropic coefficients concentrated exactly at zero and one.
3. Missing or zero fit counts by band or NDVI bin.
4. Corrected/raw ratios close to one except for topographic spatial structure.
5. Valid-pixel coverage preserved in post-July products despite trivial BRDF coefficients.
6. Expanded -9999 regions in December 5-9 products or older code paths that converted invalid factors to no-data.
7. Weak dependence of corrected/raw ratio on view zenith or relative azimuth despite geometry that should support a BRDF signal.
8. Flightline seams correlated with view geometry after mosaicking, because angular normalization was absent or neutral.
9. Bright-target loss from fitting when a correct physical 1.2 gate was active, distinct from total fit collapse under the convention bug.
10. Convolved Landsat-like and MicaSense-like products retaining the same spatial correction fingerprint at their broader bands.

Diagnostics that do not require rerunning all 43 flights:

- Parse every persisted BRDF JSON and summarize coefficient minima, medians, maxima, zero fractions, and fit counts.
- Read ENVI headers and classify reflectance scale factor and generating provenance.
- Sample raw/corrected paired windows and calculate valid fraction, slope, bias, corrected/raw quantiles, and dependence on solar/view geometry.
- Inspect existing stage 02 and stage 03 QA JSON before opening full rasters.
- Query Parquet samples for raw and corrected spectral columns, remembering they are count-scale, and compare ratios by flight line.
- Compare a small number of flight lines spanning geometry, brightness, acquisition year, and processing era.

Overall brightness alone is a weak diagnostic. A neutral BRDF model deliberately preserves brightness. Coefficient structure and angular residuals are stronger.

## Risk to the 2023/2024 production outputs

Acquisition year does not identify the processing code. A 2023 or 2024 flight processed after September 2026 may be correct; a 2021 flight processed before the repair may be affected.

### Outputs that are not altered by this specific defect

- original HDF5;
- raw stored reflectance;
- raw ENVI arrays written directly from HDF5;
- wavelength, geolocation, and ancillary geometry;
- polygon definitions and indexes;
- pre-December-5 products with respect to this specific convention bug, though early BRDF application had a separate magnitude problem.

### Outputs at risk

- BRDF model JSON;
- corrected ENVI;
- convolved sensor ENVI derived from corrected ENVI;
- full and polygon Parquet derived from those rasters;
- merged Parquet;
- QA generated from affected corrected products;
- bulk translation and spectral-library summaries based on affected corrected data.

### Era-based severity

- 2025-12-05 through 2025-12-09: highest risk of both fit collapse and no-data expansion.
- 2025-12-10 through 2026-07-21: high risk of collapsed BRDF fitting; output validity depends on factor handling.
- 2026-07-22 through 2026-09-16: high risk of visually plausible topo-only or BRDF-neutral output.
- 2026-09-17 onward: corrected implementation, but only if the run regenerated rather than reused the model and descendants.

### Practical regeneration decision

Do not rerun everything before inventory.

Treat a flight as presumptively affected if all are true:

- its source has divisor-style Scale_Factor near 10000;
- its BRDF model was generated before c511efe or has unknown provenance;
- the model was reused after the code update or its coefficients show the collapse signature.

If all 43 production flights meet those conditions, all 43 model-and-descendant chains need regeneration. Raw HDF5 and valid raw ENVI do not.

If models contain substantial finite nondefault coefficients and provenance proves generation under the fixed conversion, no rerun is needed for this issue.

## Was the change scientifically justified?

The answer depends on which change is being evaluated.

### Converting stored reflectance to physical reflectance

Scientifically justified and often preferable. Thresholds such as 1.2 or 2.0 have meaningful interpretation only in a declared physical domain. A correct conversion does not materially change the continuous scale-invariant correction mathematics.

### The December 2025 implementation

Likely erroneous for real NEON data and definitely scientifically consequential under the observed Scale_Factor = 10000 convention. It reversed the metadata meaning and caused absolute fit gates to reject normal observations.

### Departure from HyTools

Defensible in principle but insufficiently validated. HyTools’ stored-unit behavior is not automatically more physically correct; it simply avoids this particular conversion mistake. SpectralBridge’s physical-domain approach can be clearer if unit boundaries and thresholds are explicit.

### Current September 2026 implementation

Correct and necessary for the inspected NEON convention. It restores mathematical equivalence while keeping physical gates meaningful. It does not, by itself, repair cached artifacts or resolve the separate scientific questions of fit ceiling and correction order.

### QA versus scientific transformation

The project historically used physical normalization first for QA. The current correction design is not merely QA formatting: it establishes the internal scientific domain. That is legitimate. The weakness is duplicated conversion policy: correction accepts multiplier and divisor conventions, while QA currently assumes a divisor. Those boundaries should share one policy.

## Recommended conceptual design

The cleanest design is option B internally with a stable storage boundary:

1. Preserve source HDF5 values and metadata exactly for provenance.
2. Convert once at the correction-engine boundary using one convention-aware function.
3. Keep all BRDF and topographic fitting and application in physical unitless reflectance.
4. Express rho gates, tolerances, and additive adjustments in documented physical units.
5. Convert once at the corrected ENVI writer if backward-compatible stored-scale output remains the public contract.
6. Make QA use the same conversion-policy implementation rather than its own divisor assumption or median heuristic.
7. Explicitly mark Parquet columns as stored counts or physical reflectance.
8. Record raw scale value, interpreted convention, conversion-policy version, gates, source revision, and configuration hash in each persisted model.
9. Automatically invalidate models whose unit-policy provenance is incompatible with current code.

This is preferable to keeping native stored values throughout because native units make absolute physical thresholds and cross-product comparisons harder to reason about. It is preferable to ad hoc temporary conversions around individual functions because those invite duplicated policies.

Output choice can remain conservative:

- raw ENVI: original stored values plus original scale metadata;
- correction engine: physical reflectance only;
- corrected ENVI: stored values plus scale metadata, if required for compatibility;
- QA: physical reflectance obtained through the same shared policy;
- Parquet: choose one representation and state it in schema metadata and column naming.

## Minimum validation needed before changing or rerunning anything

### Inventory first

For each flight line, collect:

- source identifier and acquisition date;
- source Scale_Factor and no-data value;
- BRDF model path, timestamp, hash, coefficient summary, and generation revision;
- corrected raster path, timestamp, header scale, and valid fraction;
- dependent convolved, Parquet, merged, QA, and bulk artifacts.

### Classify without full rerun

Flag models with:

- pre-c511efe or unknown generation revision;
- all-zero volumetric and geometric coefficients;
- isotropic values only zero and one;
- no or near-zero fit observations;
- real NEON Scale_Factor = 10000.

Sample paired raw/corrected windows for flagged and unflagged flights. Calculate:

- valid-pixel retention;
- physical raw and corrected quantiles;
- corrected/raw ratio quantiles;
- angular residual before and after correction;
- spectral continuity;
- coefficient and fit-count distributions.

### Minimum rerun experiment

Select at least:

- one flight with the collapse fingerprint;
- one bright-target flight;
- one flight with strong across-track view-angle range;
- one apparently unaffected control.

For each, delete or relocate only the model and dependent corrected products in a recoverable test copy, then regenerate with current code. Compare old versus new models and products. Do not redownload source data.

### Rerun boundary if affected

Regenerate:

1. BRDF model;
2. corrected ENVI;
3. convolved or resampled ENVI;
4. per-flight Parquet;
5. merged Parquet containing that flight;
6. dependent QA, bulk, and spectral-library summaries.

Retain original HDF5 and any verified raw ENVI.

### Acceptance checks

- stored 5000 with scale 10000 is reported as physical 0.5;
- fit counts are nonzero and scientifically plausible across bands and bins;
- coefficients are finite and not uniformly default;
- corrected valid fraction does not collapse;
- corrected ENVI and header scale agree;
- physical QA independently reproduces the stored/header conversion;
- native-scale and physical-scale sampled reference calculations agree within floating-point tolerance;
- provenance records the conversion policy so restart reuse is safe.

## Evidence table

| Claim | Evidence | File | Lines/commit | Confidence |
|---|---|---|---|---|
| Real NEON metadata uses divisor semantics | Scale_Factor 10000, valid range 0-10000, sampled median 1172 = 0.1172 | NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5 | Dataset attributes and 662.221008 nm sample | HIGH |
| Initial correction used stored scale | Direct cube values in fit/application | historical src/cross_sensor_cal/corrections.py | b5969f5b7fa55bba8a365c1b6a8f82497b1eba61 | HIGH |
| QA physical scaling appeared first | Median above 1.5 caused division by 10000 | historical qa_plots.py | 0687735992607cde87a627a7305d69bfd7093b67 | HIGH |
| 856b9f1 did not put scaling into scientific fitting | Its scaling changes are in QA; correction changes are guards | historical brdf_topo.py and qa_plots.py | 856b9f1abb8c2a015e0c21b95148b789e379aa44 | HIGH |
| Scientific convention defect began December 5 | New stored-times-scale helper, physical gate, and 1e-4-only tests | historical io/neon.py, corrections.py, tests/test_brdf_scale.py | 37207cff669e6eeece1bea7b0b2bbadf87d4b327 | HIGH |
| December 10 retained defect | Wrong conversion remained with rho_max 2.0 | historical corrections.py | 4a4df5e560f9ab02f843d26b3e9eeae333dd8f1b | HIGH |
| July fixed -9999 propagation but not scale | Input preservation and neutral factor; conversion unchanged | corrections.py and brdf_topo.py | 0985382583f74fc8fcf2ef402b60b771220103d9 | HIGH |
| September is the repair | Reciprocal for scale values above one and tests for 10000 | src/spectralbridge/io/neon.py and tests/test_brdf_scale.py | c511efe110176a8bee980c87d4acbed3625dae5f | HIGH |
| Pre-repair real BRDF model collapsed | All 426 vol/geo zero; iso only zero or one | docs/validation/artifacts/r10c-l002-20210915/qa/stages/02_correction_parameters/stage_qa.json | generated under d88e8d... | HIGH |
| HyTools never divides by 10000 in correction | NEON reader and correction accessors operate on stored dataset | hytools/io/neon.py, base.py, topo, brdf, image_correct.py | HyTools 31286d64541791a9815d29443a33726fa4d54031 | HIGH |
| Topographic C is scale-invariant | Algebra and synthetic coefficient agreement | corrections.py fit_scs_c_coefficients | Current experiment | HIGH |
| BRDF ratio is scale-invariant only with equivalent selection | Algebra; correct variants agree; historical gate admitted 0 of 126 | corrections.py fit_and_save_brdf_model | Current experiment | HIGH |
| No active double division was found | Legacy heuristic has no callers; active correction and QA paths are separate | src/spectralbridge/envi.py, qa/stages.py, qa_plots.py | audited revision 06998790 | HIGH |
| Parquet retains raster numeric scale | Raster blocks are reshaped and written without header conversion | src/spectralbridge/parquet_export.py | _process_chunk_to_dataframe, build_parquet_from_envi | HIGH |
| Exact December intent is unrecoverable | Prompt log does not backfill 2025; PR body omits convention decision | PROMPT_LOG.md and PR 235 metadata | historical provenance | HIGH |
| Cached artifacts remain hazardous | Restart-safe reuse plus P79 instruction to delete old models and outputs | FEATURE_REQUESTS.md and pipeline behavior | P79, c511efe era | HIGH |
| QA may mishandle multiplier-style headers | Active QA divides by header value; correction normalizes both conventions | qa/stages.py, qa_plots.py, io/neon.py | current lines 129, 2339, 155 | HIGH |

## What we know, strongly suspect, and cannot yet resolve

### Known

- The divisor-versus-multiplier defect originated on 2025-12-05, not in the recent coworker repair.
- The actual inspected NEON file uses 10000 as a divisor.
- HyTools does not divide by 10000 before correction at the audited revision.
- Correctly normalized physical and equivalently configured native-scale correction agree to floating-point precision in the synthetic experiment.
- Historical absolute gates make the wrong conversion scientifically consequential.
- A real pre-repair R10C model shows total volumetric and geometric coefficient collapse.
- The July 2026 change masked destructive output symptoms without fixing scaling.
- The September 2026 change fixes the metadata convention for new model generation.
- Stale model reuse can preserve the old result after a code update.

### Strongly suspected

- Many real NEON products generated from 2025-12-05 through 2026-09-16 have ineffective BRDF correction.
- Post-July affected products are often topo-only in effect and may look superficially valid.
- Downstream convolved, Parquet, merged, and bulk results inherit the missing BRDF normalization where they derive from affected corrected rasters.
- If the Yellowstone models mentioned in P79 were not deleted and regenerated, they remain affected regardless of the installed code version.

These are MEDIUM-to-HIGH confidence product-level hypotheses supported by source, experiments, and one real artifact. They are not a substitute for inventorying each model.

### Unresolved

- No surviving evidence identifies who made or requested the conceptual multiplier decision in December 2025.
- The total number of affected 2023/2024 production flights and descendants is not yet known.
- The flight-specific effect size cannot be inferred from the synthetic RMSE.
- The intended scientific fit ceiling, 1.2 versus 2.0 or another policy, remains unsettled.
- The preferred BRDF-versus-topographic fitting order remains a separate scientific question.
- The public unit contract for Parquet reflectance is not explicit enough to determine whether stored counts are intentional for every consumer.
- QA’s behavior for multiplier-style ENVI headers remains inconsistent with the shared correction policy.

The evidence is sufficient to locate the historical origin and explain the mechanism. It is not sufficient to declare every historical product invalid without inspecting its model provenance and coefficient fingerprint.
