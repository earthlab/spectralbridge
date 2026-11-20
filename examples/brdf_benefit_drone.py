"""Compact matched BRDF ablation on original calibration polygon grids.

Apply only the frozen topographic stage in128-row windows, compare with immutable
archived topo+BRDF outputs. Translation is the SAME fractional affine in each arm.
No new rasters, fits, masks or production approvals. Unmasked Ruby remains failed QA.
"""

import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
import rasterio
from threadpoolctl import threadpool_limits
import drone_shade_excluded_refit as refit
from drone_shade_mask_preview import MASKS, file_sha256
from spectralbridge.drone_translation import load_drone_translation_plans
from spectralbridge.envi import hdr_to_dict, memmap_bsq

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "provenance/brdf-benefit-audit/2026-11-19/drone"
BASE = ROOT / "archive/local/drone-calibration-translation/2026-11-19"
REGISTRY = (
    ROOT
    / "provenance/drone-calibration-translation/2026-11-19/aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
)
BANDS = [f"B{i}" for i in range(1, 6)]


def translate(values, plan):
    return np.column_stack(
        [
            values[:, b.native_source_band_index - 1] * b.slope + b.intercept
            for b in plan.bands
        ]
    )


def run():
    REPORT.mkdir(parents=True, exist_ok=True)
    checkpoint = REPORT / "completed.json"
    signature = {"code": file_sha256(Path(__file__)), "registry": file_sha256(REGISTRY)}
    if checkpoint.exists():
        old = json.loads(checkpoint.read_text())
        if (
            old["signature"] == signature
            and all(file_sha256(REPORT / p) == h for p, h in old["outputs"].items())
            and all(file_sha256(ROOT / p) == h for p, h in old["sources"].items())
        ):
            print("Verified drone compact reuse", flush=True)
            return
    started = time.monotonic()
    driver = refit.setup()
    configs = json.loads((refit.PRIOR / "site_inputs.json").read_text())
    summaries = []
    coverage = []
    audit = []
    sources = {
        str(Path(module.__file__).relative_to(ROOT)): file_sha256(Path(module.__file__))
        for module in [driver, driver.support]
    }
    for p in [
        Path(refit.__file__),
        refit.FROZEN / "source_topographic.py",
        refit.FROZEN / "source_corrections.py",
        refit.PRIOR / "site_inputs.json",
    ]:
        sources[str(p.relative_to(ROOT))] = file_sha256(p)
    for config in configs:
        site = config["site"].lower()
        raw, design, geometry, footprint, domain, training, groups, transform, crs = (
            refit.cube_inputs(driver, config)
        )
        for p in [
            refit.BASE / site / "candidate_stored.npy",
            refit.BASE / site / "geometry.npy",
            refit.BASE / site / "center_design.npy",
            Path(config["solar_arrays"]),
            Path(config["prepared"]),
            *[Path(p) for p in config["terrain_ancillary"].values()],
        ]:
            sources[str(p.relative_to(ROOT))] = file_sha256(p)
        labels = pd.read_parquet(
            config["polygon_index"],
            columns=["GlobalID", "cover_category", "row", "col", "x", "y"],
        ).reset_index(drop=True)
        rows = labels.row.to_numpy()
        cols = labels.col.to_numpy()
        x, y = transform * (cols + 0.5, rows + 0.5)
        np.testing.assert_allclose(x, labels.x, atol=1e-7, rtol=0)
        np.testing.assert_allclose(y, labels.y, atol=1e-7, rtol=0)
        if labels.duplicated(["row", "col"]).any():
            raise ValueError("Overlapping label memberships")
        plan = load_drone_translation_plans(
            REGISTRY,
            source_wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
            target_sensors=["Landsat_9_OLI-2"],
        )[0]
        source_pixels = np.asarray(raw[rows, cols], float) * driver.SCALE
        for variant in ["conservative", "baseline"]:
            models = refit.DEST / site / variant
            topo_path = models / "conditioned_scsc_model.json"
            brdf_path = next((models / "combined").glob("*brdf_model.json"))
            topo = json.loads(topo_path.read_text())
            brdf = json.loads(brdf_path.read_text())
            retain = domain.copy()
            if variant == "conservative":
                mask_path = MASKS / refit.mask_filename(config["flight_stem"], 0.1)
                sources[str(mask_path.relative_to(ROOT))] = file_sha256(mask_path)
                expected = json.loads((models / "completed.json").read_text())[
                    "identity"
                ]["mask_sha256"]
                if sources[str(mask_path.relative_to(ROOT))] != expected:
                    raise ValueError("Fit/application mask differs")
                with rasterio.open(mask_path) as mask:
                    retain &= mask.read(1) == 0
                img = next(
                    (BASE / "conservative-refitted-products" / site).glob(
                        "*EXPERIMENTAL.img"
                    )
                )
            else:
                img = (
                    BASE
                    / "unmasked-null-products"
                    / site
                    / f"{site}_20230814_unmasked_null_corrected_micasense_envi.img"
                )
            header = hdr_to_dict(img.with_suffix(".hdr"))
            corrected = memmap_bsq(img, header)
            # Native corrected archives use their ORIGINAL conditional stored units.
            scale = float(header.get("physical reflectance multiplier", driver.SCALE))
            if (
                scale != driver.SCALE
                or float(header.get("physical reflectance offset", 0)) != 0
            ):
                raise ValueError(
                    "Native archive radiometry differs from frozen topo source"
                )
            after = np.asarray(corrected[:, rows, cols], float).T * scale
            cube = driver.support.Cube(
                raw, retain, geometry, scale=driver.SCALE, footprint=footprint
            )
            apply = driver.support.isolated(driver.support.topo.apply_conditioned_scs_c)
            before = np.full((len(labels), 10), np.nan)
            with threadpool_limits(limits=1):
                for start in range(0, cube.lines, 128):
                    ix = np.flatnonzero((rows >= start) & (rows < start + 128))
                    if not len(ix):
                        continue
                    end = min(start + 128, cube.lines)
                    values = apply(
                        cube,
                        np.asarray(raw[start:end], np.float32),
                        start,
                        end,
                        0,
                        cube.columns,
                        model=topo,
                    ).values
                    before[ix] = values[rows[ix] - start, cols[ix]] * driver.SCALE
            left = translate(before, plan)
            right = translate(after, plan)
            keep = (
                np.isfinite(left).all(axis=1)
                & np.isfinite(right).all(axis=1)
                & retain[rows, cols]
            )
            rawtranslated = translate(source_pixels, plan)
            for gid, g in labels.groupby("GlobalID", sort=True):
                ix = g.index.to_numpy()
                selected = ix[keep[ix]]
                category = g.cover_category.unique()
                if len(category) != 1:
                    raise ValueError("Conflicting label")
                coverage.append(
                    dict(
                        identity=gid,
                        site=site,
                        variant=variant,
                        source_pixels=len(ix),
                        paired_pixels=len(selected),
                    )
                )
                if not len(selected):
                    continue
                for arm, values in [
                    ("no_brdf", left),
                    ("brdf", right),
                    ("raw", rawtranslated),
                ]:
                    summaries.append(
                        dict(
                            identity=str(gid).strip("{}").lower(),
                            site=site,
                            category=category[0],
                            variant=variant,
                            arm=arm,
                            n_pixels=len(selected),
                            **dict(
                                zip(
                                    BANDS,
                                    np.median(values[selected], axis=0),
                                    strict=True,
                                )
                            ),
                        )
                    )
            for b in range(5):
                delta = right[keep, b] - left[keep, b]
                audit.append(
                    dict(
                        site=site,
                        variant=variant,
                        band=BANDS[b],
                        paired_pixels=int(keep.sum()),
                        median_abs_reflectance_change=float(np.median(abs(delta))),
                        p95_abs_reflectance_change=float(np.quantile(abs(delta), 0.95)),
                        brdf_valid_bands=sum(
                            f["status"] == "VALID" for f in brdf["validation"]["fits"]
                        ),
                        brdf_status=brdf["validation"]["status"],
                        scene_source_pixels=int(domain.sum()),
                        scene_retained_pixels=int(retain.sum()),
                    )
                )
            for p in [
                topo_path,
                brdf_path,
                img,
                img.with_suffix(".hdr"),
                Path(config["polygon_index"]),
            ]:
                sources[str(p.relative_to(ROOT))] = file_sha256(p)
            print(site, variant, "shared labelled pixels", int(keep.sum()), flush=True)
    frame = pd.DataFrame(summaries)
    frame.to_csv(REPORT / "all_stage_polygon_spectra.csv", index=False)
    for variant in ["conservative", "baseline"]:
        frame[(frame.variant == variant) & frame.arm.isin(["no_brdf", "brdf"])].to_csv(
            REPORT / f"{variant}_polygon_spectra.csv", index=False
        )
    pd.DataFrame(coverage).to_csv(REPORT / "coverage.csv", index=False)
    pd.DataFrame(audit).to_csv(REPORT / "correction_magnitudes.csv", index=False)
    checkpoint.write_text(
        json.dumps(
            dict(
                signature=signature,
                sources=sources,
                outputs={p.name: file_sha256(p) for p in REPORT.glob("*.csv")},
                elapsed_seconds=time.monotonic() - started,
                attribution="Incremental BRDF conditional on same topo fit, mask and affine translation; experimental historical radiometry; unmasked Ruby failed QA",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    run()
