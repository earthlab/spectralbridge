"""Build the experiment's Markdown report from measured result tables."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    s = json.loads((HERE / "experiment_summary.json").read_text())
    c = pd.read_csv(HERE / "constant_geometries.csv")
    v = pd.read_csv(HERE / "spatial_geometries.csv")
    b = pd.read_csv(HERE / "baseline_polygon_spectra.csv")
    sep = pd.read_csv(HERE / "separability.csv")
    p = json.loads((HERE / "preservation.json").read_text())
    delta = (
        (
            c[c.view_zenith_degrees.eq(15)].set_index(
                ["flight", "relative_azimuth_degrees"]
            )[["RossThick", "LiDenseR"]]
            - c[c.view_zenith_degrees.eq(10)].set_index(
                ["flight", "relative_azimuth_degrees"]
            )[["RossThick", "LiDenseR"]]
        )
        .abs()
        .max()
    )
    constraints = []
    for name, f in s["flights"].items():
        path = (
            Path("/private/tmp/photogrammetry-metadata-20261102") / f"{name}_report.pdf"
        )
        constraints.append(
            dict(
                flight=name,
                processing_report=str(path),
                sha256=sha(path),
                reported_flying_altitude_m=f["flying_altitude_report_m"],
                focal_length_mm=5.5,
                pixel_pitch_um=3.75,
                sensor_pixels=[1280, 960],
                nominal_horizontal_half_field_deg=f["horizontal_half_fov_deg"],
                nominal_vertical_half_field_deg=f["vertical_half_fov_deg"],
                nominal_corner_off_nadir_deg=f["diagonal_half_fov_deg"],
                nominal_ground_footprint_width_m=2
                * f["flying_altitude_report_m"]
                * (1280 * 0.00375 / 2)
                / 5.5,
                scope="Nominal pinhole bounds, not calibrated rays. Distortion, attitude, canopy distance, actual tracks, source selection/blending and exact project-to-export link unavailable.",
            )
        )
    (HERE / "scenario_provenance.json").write_text(
        json.dumps(
            dict(
                reports=constraints,
                scenario_definitions={
                    "symmetric_footprints": "Repeated across-grid pinhole footprints; signed cross-track arctan offset/H, arbitrary 90/270 degree absolute directions. Spacing/origin synthetic.",
                    "alternating_strips": "Constant 15 degree zenith and alternating 0/180 absolute azimuth at half-footprint strip width. Tracks/directions synthetic.",
                    "mosaic_edges": "0 to25 degree zenith from normalized distance to mosaic center; radial assumed azimuth.",
                    "smooth_map": "5 to25 degree zenith across columns; hypothetical smooth absolute azimuth from row and column coordinates.",
                    "smooth_map_reflected": "Same illustrative formula with cross-grid coordinate reflected; equally unsupported alternative.",
                },
                azimuth_convention="Clockwise absolute sensor azimuth; relative = circular(sensor minus solar). Constant cases convert absolute=(solar+relative) modulo360. Grid patterns do not reconstruct true-North camera directions; no actual track/north-convergence inference is made.",
                all_maps="SYNTHETIC: none replaces H5 metadata",
            ),
            indent=2,
        )
        + "\n"
    )
    pairrows = []
    for row in sep[sep.status.eq("DESCRIPTIVE_CONDITIONAL_TEST")].itertuples():
        g = b[b.flight.eq(row.flight) & b.cover_category.isin([row.first, row.second])]
        mixed = g.groupby("spatial_block").cover_category.nunique()
        g = g[g.spatial_block.isin(mixed[mixed == 2].index)]
        a = g[g.cover_category.eq(row.first)][
            [f"b{i}" for i in range(1, 11)]
        ].to_numpy()
        z = g[g.cover_category.eq(row.second)][
            [f"b{i}" for i in range(1, 11)]
        ].to_numpy()
        a1, a3 = np.percentile(a, [25, 75], axis=0)
        z1, z3 = np.percentile(z, [25, 75], axis=0)
        den = np.maximum(a3, z3) - np.minimum(a1, z1)
        over = np.divide(
            np.maximum(0, np.minimum(a3, z3) - np.maximum(a1, z1)),
            den,
            out=np.full(10, np.nan),
            where=den > 0,
        )
        angle = float(
            np.asarray(
                __import__("analyze").prior.angle_degrees(
                    np.median(a, axis=0), np.median(z, axis=0)
                )
            )
        )
        pairrows.append(
            dict(
                flight=row.flight,
                first=row.first,
                second=row.second,
                first_polygons=len(a),
                second_polygons=len(z),
                mean_band_IQR_intersection_over_union=float(np.nanmean(over)),
                class_median_spectral_angle_degrees=angle,
                scope="Raw source-DN descriptive overlap; not classification error or calibrated spectral agreement",
            )
        )
    pd.DataFrame(pairrows).to_csv(HERE / "baseline_pair_overlap.csv", index=False)
    # List actual required metrics with explicit unknowns, never factor-one placeholders.
    metrics = []
    for n in s["flights"]:
        for approach in [
            "constant_assumed_fit",
            "synthetic_spatial_assumed_fit",
            "independent_coefficient_transfer",
        ]:
            metrics.append(
                dict(
                    flight=n,
                    approach=approach,
                    correction_status="NOT_APPLIED",
                    factor_quantiles=None,
                    extreme_gain_count=None,
                    invalid_predictions=None,
                    corrected_nonfinite_count=None,
                    corrected_valid_coverage=None,
                    corrected_spectral_discontinuity=None,
                    within_PFT_change=None,
                    between_PFT_change=None,
                    class_overlap_change=None,
                    spectral_index_change=None,
                    reason="No supported physical fit; no response fit to invented geometry; no eligible independent coefficient set.",
                )
            )
    (HERE / "correction_comparison_status.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    table = "\n".join(
        f"| {r.flight.title()} | {r.scenario.replace('_', ' ')} | {r.rank} | {r.condition_number:.3g} | {'Pass angular-only' if r.angular_numerical_gate else 'Fail'} |"
        for r in v.itertuples()
    )
    groups = b.groupby("flight").agg(
        polygons=("GlobalID", "size"), memberships=("pixels", "sum")
    )
    gt = "\n".join(
        f"| {n.title()} | {int(r.polygons)} | {int(r.memberships):,} |"
        for n, r in groups.iterrows()
    )
    txt = f"""# Can Assumed Viewing Angles Rescue Drone BRDF Correction?

2026-11-03. **Read-only experiment on real Gordon, Goldhill and Ruby 2023 imagery.**
No source angles, production coefficients, rasters or libraries were changed.

## Direct result

**A constant 10° or 15° view does not rescue the current fit.** Across all
**93 requested constant-relative-angle cases**, zero pass the current angular
rank/conditioning gate. In exact constant-relative geometry there is one distinct
kernel row and only one identifiable coefficient combination, not three.
Float32 absolute-angle conversion gives nominal rank three in {int((c["rank"] == 3).sum())}
cases, but this is numerical noise: the best constant-case condition number is
**{c.condition_number.min():.3g}**, versus the package limit **2896**.

**Synthetic maps can manufacture numerical support:** 12/15 pass the angular-only
gate, with condition numbers about {v[v.angular_numerical_gate].condition_number.min():.1f}–{v[v.angular_numerical_gate].condition_number.max():.1f}.
None establishes physical observation information or a scientifically valid fit.

**Fixed-coefficient transfer is not evaluated:** 13 candidate files include six
computationally VALID synthetic fixtures, four unsupported/invalid records and
three historical unvalidated models. No independently validated, radiometrically,
spectrally and ecologically applicable NEON coefficient set was found in the
bounded repository/cache search. No coefficients were manufactured or fitted to
invented drone geometry. Consequently, correction-factor distributions and changes
to PFT metrics are **unknown / NOT_EVALUATED**, not zero and not evidence of improvement.

![Actual encoded baseline versus constant and synthetic assumptions](figure1_geometry.png)

*Figure 1. Schematic, not recovered cameras. The original H5 zero views are
placeholders traced by P162; actual camera-to-target observations remain unavailable.*

## 1. Sources, spatial integrity and the raw baseline

Repository revision: `{p["revision"]}`. The working tree contains earlier pending
documentation changes; exact source hashes and its initial status are retained in
`input_manifest.json`. The experiment uses the current package equations,
RossThick/LiDenseR (`b/r=10`, `h/b=2`, scene solar), not the defective historical
kernel. `preservation.json` records **{len(p["inputs_before"])} input/source files**
with matching SHA-256 before/after.

The old temporary working H5s, normalized TIFFs and corrected rasters were partly
absent locally. Three archived working H5s were retrieved **read-only into a new
temporary directory**, and all three match their November 2 recorded hashes
exactly. Recovered-DN TIFF hashes also match. Missing earlier files are listed,
not recreated or claimed newly verified. The three recovered-DN arrays equal
those TIFFs at every band/pixel, including NaNs. Their source-valid masks match
the original H5 imagery. Source grids remain north-up **EPSG:26913 at 0.1 m**.
The prior spatial repair is preserved; no resampling, geographic relabelling or
polygon geometry change occurs here.

Primary spectra are **uncorrected recovered source DN — physical units unverified**.
No SCS+C output enters this experiment. We preserve all researcher `GlobalID`,
`species` and `cover_category` values, including Non-vegetated & dead.
Rasterized pixel centers are independently checked against the actual polygons.

| Flight | Researcher polygons with valid raw pixels | Polygon-pixel memberships |
| --- | ---: | ---: |
{gt}

The total is **301 polygons / 198,562 memberships** after explicitly requiring positive
source alpha as well as finite H5 values. The finite-H5-only audit contains
302 polygons / 200,320 memberships, including **1,758 transparent-background
memberships** across seven polygons. One Goldhill shrub polygon has only
transparent support and is excluded from spectral summaries; its original ID and
label remain in `source_alpha_audit.csv`. Alpha zero means no source image
contribution, not a bright measured surface. No source alpha, raster, polygon or
H5 mask is rewritten. Fractional positive alpha is retained without an arbitrary
coverage cutoff; physical interpretation of resampled edges still needs review.

Angular experiments preserve full finite-H5 support to reproduce the actual
encoded design. PFT summaries and raw displays separately require positive source
alpha to avoid treating background DN as observed spectra. P161 used a different
common raw/topographic population (301 / 198,309); its counts are historical, not
an improvement benchmark for this raw-only experiment. All 301 retained polygons
remain distinct under the prior outcome-blind overlap-component rule. Pixels
within a polygon are not independent plants.

The known bandwise inverse normalization is reused only as a numerical
representation. The 10 cm original-export border differences documented by
P159/P160 remain unresolved; DN is not physical reflectance or reconstructed
native camera samples. No DN/32768 or DN/10000 calibration is asserted.

## 2. Constant assumptions: correct conventions and full-scene design

We test view zenith **0, 5, 10, 15, 20, 25 and 30°**. At nonzero zenith we test
relative azimuth **0, 45, 90, 135 and 180°**. Nadir contributes **one** case;
its azimuth is undefined and is not counted as several observations. There are
31 cases per flight, 93 total.

The package accepts clockwise **absolute** solar and sensor azimuths. For a
specified relative azimuth we construct
`absolute_sensor = (absolute_solar + relative) % 360`.
The opposite signed convention gives the same symmetric Ross/Li kernels, but we
do not substitute a relative angle directly as an absolute compass direction.
The actual working-H5 solar arrays are used; zenith is reduced to the actual
source-valid scene mean exactly as in the current package. Acquisition-time
uncertainty remains, especially Ruby's manifest August 16 versus August 15 CSVs
and August 14 notes. This experiment does not repair timestamps.

Each design is evaluated by the **actual `_brdf_design` implementation**. Constant
cases are reduced exactly by the distinct stored solar azimuths and their
full-scene multiplicities; weighted SVD reproduces the singular values of the
full repeated design without making a pixel table. Rank uses the original
population-size tolerance. This is not a sampled-rank estimate.

![Kernel responses to constant assumed view angles](figure2_kernel_response.png)

*Figure 2. Actual package kernels at each real flight's scene solar zenith;
angles are imposed, not measured. Nadir is shown once per curve solely to connect
responses, never as additional fitting support. Kernel values are dimensionless;
no coefficients or normalized reflectance are estimated.*

In exact constant-relative geometry, all pixels supply the same three-element
row `[1, Kvol, Kgeo]`. A different constant changes that row but not its independent
information. Subtracting float32 absolute azimuths can introduce tiny apparent
variations: across all constant cases the largest within-case ranges are
**1.19e-7 in RossThick and 3.10e-6 in LiDenseR**. Those numerical variations can
increase reported algebraic rank without useful precision. The conditioning
gate rejects every case. All 30 band fits remain unsupported, separately from
the unresolved physical units. No reflectance fit was attempted to these angles.

An extra **24 fixed-absolute-compass checks** (10°/15° at 0/90/180/270°) allow the
actual small solar-azimuth variation to change relative azimuth. All 24 also
fail angular conditioning. That variant does not recover real camera diversity.

![Rank and conditioning of constant and synthetic designs](figure3_identifiability.png)

*Figure 3. Full-source-valid support. Dashed line is the existing float32-based
condition limit. Numerical rank by itself is insufficient; no gate is relaxed.*

## 3. Spatially varying assumptions

Reports document flying altitudes **117 m Gordon, 123 m Goldhill and 114 m Ruby**,
with nominal **1280×960 pixels, 3.75 μm pitch and 5.5 mm focal length**. A simple
pinhole calculation gives horizontal/vertical half-angles about **23.57°/18.12°**
and a diagonal half-angle about **28.61°**. These are illustrative bounds,
not calibrated rays. Source report hashes and exact calculations are in
`scenario_provenance.json`. Lens distortion, actual attitudes, terrain/canopy
range, flight-track azimuth, source selection and blend weights are unavailable.
Reports are project snapshots, not verified exact final-export recipes.

Five maps are tested on **each entire source-valid footprint**:

1. Repeated symmetric across-footprint zenith from the nominal pinhole width,
   with assumed opposite azimuths; origin/spacing/direction are synthetic.
2. Alternating nominal flight strips, constant 15° and 0/180° absolute azimuth.
3. Mosaic-edge zenith increasing from 0 to 25°, with hypothetical radial azimuth.
4. Smooth 5–25° zenith and a hypothetical smoothly varying absolute azimuth.
5. A reflected version of that smooth field, an equally unsupported alternative.

Grid coordinates parameterize these illustrative fields; they do not establish
actual true-North source-camera bearings or flight tracks. No H5 dataset is
written. Streaming QR/SVD uses all supported rows and retains only compact
statistics. Full-population extrema and means are exact; reported spatial kernel
quantiles use every 97th supported cell within each 128-row strip and are labelled
as deterministic samples. Display images use every eighth source pixel.

| Flight | Synthetic scenario | Numerical rank | Condition number | Angular-only gate |
| --- | --- | ---: | ---: | --- |
{table}

All 15 nominal ranks are three. The alternating two-direction maps remain
ill-conditioned (about 8.2e5–6.7e6): only two nominal view directions plus tiny
solar/numeric variation do not provide three well-supported terms. The other
12 have finite well-conditioned designs. **No physical fit is approved:** those
kernel variations were imposed rather than observed with the measured spectra.
Unknown radiometry and missing view provenance remain independent failures.
The separate `alpha_positive_design_audit.json` repeats all 93 constant and 15
spatial cases on finite, positive-source-alpha support: the same **0/93** and
**12/15** angular-only outcomes hold. Transparent H5 background does not drive
these conclusions.

![Invented angle and kernel maps over the actual Goldhill footprint](figure4_synthetic_maps.png)

*Figure 4. Synthetic fields only, with shared color limits across scenarios.
The real footprint/mask is retained; there are no corrected images. An attractive
full-rank map is not recovered Metashape geometry.*

## 4. Fixed independent coefficients: a stopped branch, not a hidden substitute

`coefficient_inventory.json` records 13 candidate paths, sizes, hashes,
computational/radiometry status, kernel/reference records and rejection reasons.
A separate historical real-NEON R10C QA record is also inspected: all 426
volumetric and geometric terms are zero in that pre-repair artifact. Its summary
does not supply a validated transferable coefficient set. The source path, hash
and exact statistics are recorded as auxiliary evidence in the inventory.
The bounded search covers the repository (including archived evidence) and named
local investigation caches, depth ≤9 and coefficient/model JSON filenames.
It is not a claim that validated NEON coefficients do not exist elsewhere.

Six VALID files are explicitly synthetic installed-artifact fixtures, including
NEON-shaped file names. Four are unsupported/invalid and three are legacy
unvalidated records. No candidate establishes all of: independent empirical
validation, matching wavelengths/spectral responses, the current kernels and
reference, physical units, vegetation/canopy/illumination domain and stable
application support. Historical Goldhill coefficients are invalid and cannot be
ported to repaired kernels. A synthetic neutral or arbitrary anisotropic model
would not answer the user's transfer question, so none is substituted.

With an eligible model the required ratio would be:

```text
normalized = observed_DN *
    (f_iso + f_vol*Kvol_reference + f_geo*Kgeo_reference) /
    (f_iso + f_vol*Kvol_assumed   + f_geo*Kgeo_assumed)
```

Physical calibration would still be unverified, so even that calculation would
be a DN sensitivity, not calibrated reflectance. Existing source/calibration,
positive/finite prediction, uncertainty, kernel, reference and applicability
checks must remain. The current production application also binds models to
source identity/radiometry; this experiment does not add an external bypass.

**No fixed-coefficient application was performed.** Factor quantiles, extreme
gains/losses, invalid predictions, corrected coverage/nonfinite values,
discontinuities, spectral-angle changes, indices, within-PFT changes and
between-PFT/class-overlap changes are null/NOT_EVALUATED in
`correction_comparison_status.json`. They are not assigned zero, identity or
invented confidence bounds. Actual raw-data statistics are available separately.

![Coefficient evidence and missing correction-factor branch](figure5_coefficient_boundary.png)

*Figure 5. A missing eligible model means no correction-factor distribution
exists. The six VALID fixtures demonstrate software behavior, not empirical
NEON-to-drone applicability.*

## 5. Goldhill, RGB and source spectral structure

![Uncorrected Goldhill red band and native transect](figure6_goldhill.png)

*Figure 6. Actual 650 nm source DN, no topographic processing. The native transect
uses row 921, columns 840–1120, and marks the previous historical factor boundary
at column 980. No 10°/15° correction curve exists. The map uses a declared
0–20,000 DN graphical range; all values remain in the analysis. The prior
historical BRDF streak remains a confirmed downstream failure, not evidence of
an upstream seam or improvement in this experiment.*

![Three actual uncorrected mosaics on one RGB scale](figure7_raw_rgb.png)

*Figure 7. RGB 650/560/475 nm with a single pooled source-DN channel stretch for
all flights. Masks and orientation are unchanged. Graphical limits are recorded
in `display_limits.json`; clipping affects display only. No per-panel stretch,
BRDF, topography or physical reflectance claim is involved.*

Per-polygon ten-band median spectra, within-polygon variation and spectral angles,
numerical NDVI/NDRE/GNDVI, and all original category labels are retained in
`baseline_polygon_spectra.csv`. Indices are wavelength-driven numerical ratios
with denominator checks; bounded values do not establish physical validity.
Non-vegetated & dead remains a separate cover comparator.

One polygon median is the primary analysis unit. The existing outcome-blind
connected-overlap identity rule is reused; here all 301 retained identities remain distinct.
Within-category metrics require at least five polygon spectra. Between-category
inference retains 100 m blocks containing both labels, then requires five
polygons per class. The reused package `spectral_separability` uses equal weights
on the ten measured wavelengths, 1,999 seeded permutations and Holm correction
across all 17 supported comparisons; five additional pairs lack support.
There are seven adjusted raw associations at p<0.05. They do **not** establish
classification accuracy, causal correction benefit or independent calibration.
Spatial exchangeability remains an assumption and neighboring polygons can share
unmodelled environmental effects.

`within_class_metrics.csv`, `bandwise_class_metrics.csv`, `polygon_class_angles.csv`
and `separability.csv` record raw dispersion, angles, standardized contrasts and
existing identifiability tests. `baseline_pair_overlap.csv` adds empirical central
50% interval overlap (intersection/union averaged over bands) and class-median
spectral angle on the same supported polygon sets. This descriptive overlap is
not a predictive error rate. No pixel train/test split, fabricated corrected class
or before/after improvement p-value is used.

![Within-PFT and between-PFT source-DN baseline](figure8_pft_baseline.png)

*Figure 8. Raw baseline only. Variance/CV are descriptive DN metrics; class
spectral differences are not classification accuracy. Without a defensible
correction there is no independent comparison of corrected PFT quality.*

The imposed kernel–raw-red Spearman associations are recorded separately in
`imposed_geometry_associations.csv` for each synthetic field. They are descriptive
spatial confounding diagnostics, **not a response regression or BRDF fit**.
Imposed geometry can align with vegetation patterns by construction; optimizing
variance or visual smoothness would risk removing biology.

## 6. How sensitive are 10° and 15° assumptions?

Across the tested constant cases, RossThick spans **{c.RossThick.min():.4f} to {c.RossThick.max():.4f}**
and LiDenseR **{c.LiDenseR.min():.4f} to {c.LiDenseR.max():.4f}**. Changing only 10°→15°
at matched relative azimuth changes the kernel by up to **{delta.RossThick:.4f}**
(RossThick) and **{delta.LiDenseR:.4f}** (LiDenseR). Thus those angles are not
interchangeable basis assumptions. These are measured equation responses on the
actual scene solar geometry, **not evidence of a particular reflectance gain**.

![Sensitivity of kernels to assumed angles and azimuths](figure9_sensitivity.png)

*Figure 9. Kernel envelopes/spans across relative azimuth, not correction-factor
confidence intervals. Without applicable `f_iso/f_vol/f_geo`, gain sensitivity,
robustness and preservation of PFT spectra cannot be quantified. No “best angle”
is selected from appearance or variance.*

## 7. Scientific recommendation and seven answers

| Approach | Classification | Reason |
| --- | --- | --- |
| Fit three coefficients with a constant assumed angle | **Unsupported** | One ideal kernel row; every encoded constant case fails conditioning; physical units remain unverified |
| Use spatially varying invented geometry | **Numerically feasible but unvalidated** for 12/15 angular designs; **unsupported** as a physical correction | Algebraic information is imposed, not observed; no response fit performed |
| Alternating two-direction strip scenario | **Unsupported** | Nominal rank three is ill-conditioned and not physically observed |
| Transfer independent NEON coefficients | **Not evaluated** | No suitable independently validated coefficient set found; no bypass or surrogate |
| Preserve source imagery and omit unsupported BRDF | **Supported as an interim preservation strategy** | Does not claim calibrated physical reflectance or approval of the current libraries |

1. **Can a constant assumed angle identify this three-parameter fit?** No tested
   angle does; 0/93 pass. One fixed geometry identifies only one coefficient
   combination. Roundoff-generated numerical rank does not rescue it.
2. **Can synthetic variation produce rank without genuine physical information?**
   Yes: 12/15 imposed fields pass angular-only checks while none recovers observations.
3. **Can independently estimated coefficients yield stable corrections here?**
   Not evaluated; the necessary validated/applicable coefficient set is unavailable.
4. **Are those corrections robust across assumed angles?** Unknown. Kernels change
   substantially, but no eligible model exists to quantify correction sensitivity.
5. **Do they preserve or improve PFT structure?** Not established. Actual polygon
   baselines are quantified; corrected differences and independent quality tests do not exist.
6. **Is any assumed-angle approach defensible for production libraries?** No
   evidence supports promotion. Physical calibration and viewing applicability remain missing.
7. **Is skipping BRDF still the best interim strategy?** Yes: preserve the verified
   spatial grid and uncorrected numerical data, explicitly omit BRDF, and keep
   physical/library approval separate. Do not reintroduce unapproved topography.

The next useful inputs are a real empirically validated, wavelength/response-matched
coefficient model with kernel/reference/radiometry/canopy-domain evidence, **or**
actual calibrated same-target source-photo observations with camera geometry.
Neither a plausible constant nor a synthetic full-rank angle map replaces them.
Recover physical calibration and authoritative timestamps in either case. No
production metadata replacement, coefficient change or library regeneration is warranted.

## Reproduction and evidence

Run from repository root using the scientific environment:

```bash
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python provenance/assumed-viewing-angles/2026-11-03/inventory_coefficients.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/assumed-viewing-angles/2026-11-03/analyze.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python provenance/assumed-viewing-angles/2026-11-03/audit_masks.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/assumed-viewing-angles/2026-11-03/audit_angular_support.py
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python provenance/assumed-viewing-angles/2026-11-03/figures.py
.venv/bin/python provenance/assumed-viewing-angles/2026-11-03/write_report.py
# make_pdf.py uses the bundled Python with reportlab, followed by pdftoppm review.
```

`input_manifest.json` gives restored Data Store origins and exact hashes. Large
working files remain in the isolated `/private/tmp/assumed-viewing-angles-20261103`
workspace; no full pixel-scale Parquet cache or corrected raster is created.
Design processing streams 128-row QR reductions; compact per-scenario kernel
maps are temporary in memory and display samples are coarsened. No production
performance claim is made. `gate_contract_control.json` is a separately labelled
small synthetic unknown-radiometry API control, not a fit to the flights.

Prior evidence, read with P162's superseding provenance account:

- [Goldhill artifact diagnosis](../../goldhill-correction-diagnosis/2026-10-30/README.md).
- [Numeric scaling](../../drone-scale-confirmation/2026-10-30/README.md).
- [Radiometric recovery](../../../docs/dev/drone-radiometric-recovery-experiment.md).
- [BRDF/PFT/topographic strategy](../../../docs/dev/drone-brdf-identifiability-investigation.md).
- [P162 photogrammetry provenance](../../../docs/dev/photogrammetry-metadata-investigation.md).
- [Shared physical/model audit](../../radiometry-brdf/2026-10-30/README.md).

Limitations include unknown physical radiometry, timestamp/solar provenance,
unavailable true contributors/camera rays, non-independent nearby vegetation,
original export residuals and absence of transferable independent coefficients.
The negative constant-angle result is quantitative; the stopped coefficient branch
is explicitly incomplete evidence rather than a claim that all possible external
models would fail.
"""
    (HERE / "report.md").write_text(txt)
    print(
        "Integrated report, source constraints and explicit null correction metrics saved."
    )


if __name__ == "__main__":
    main()
