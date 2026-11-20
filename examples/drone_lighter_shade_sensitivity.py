"""Fixed lighter-mask refits for Ruby; cross-site check of a retained candidate.

A sensitivity search, not confirmatory validation or an exact optimal cutoff.
All six Ruby trials are retained, including failures. Original runs are immutable.
"""

import argparse
import json

import pandas as pd
import rasterio
from rasterio.windows import Window

import drone_shade_excluded_refit as refit
from drone_shade_mask_preview import (
    classify,
    file_sha256,
    visible_indices,
    ROOT,
)
from spectralbridge.envi import hdr_to_dict
from spectralbridge.bulk.provenance import write_json_atomic

DEST = (
    ROOT
    / "provenance/drone-calibration-translation/2026-11-19/lighter-shade-sensitivity"
)
MASKS = (
    ROOT / "archive/local/drone-calibration-translation/2026-11-19/lighter-shade-masks"
)
THRESHOLDS = [0.05, 0.075, 0.09, 0.095, 0.0975, 0.099]
VARIANTS = [
    "cutoff_5pct",
    "cutoff_7p5pct",
    "cutoff_9pct",
    "cutoff_9p5pct",
    "cutoff_9p75pct",
    "cutoff_9p9pct",
]
POLICY = refit.POLICY | dict(
    variants=VARIANTS,
    thresholds=THRESHOLDS,
    selection="All six Ruby variants; least tested full-ten-band passing threshold checked at Gordon/Goldhill. Report all trials, no guarantee of monotonic response or independent validation.",
    prior_experiment="shade-excluded-refit-v2; baseline numerically reproduced at each site",
    exact_optimum_claimed=False,
)


def prepare_masks(site, variants):
    DEST.mkdir(parents=True, exist_ok=True)
    MASKS.mkdir(parents=True, exist_ok=True)
    policy = json.loads(json.dumps(POLICY))
    path = DEST / "experiment_policy.json"
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Frozen lighter-mask design changed")
    if not path.exists():
        write_json_atomic(path, policy)
    parent = DEST.parent / "shade-review"
    counts = pd.read_csv(parent / "candidate_exclusion_counts.csv")
    normalizer = float(
        counts.loc[counts.site.eq(site), "normalization_p95_native_units"].iloc[0]
    )
    source_info = next(
        x
        for x in json.loads((parent / "source_provenance.json").read_text())["sources"]
        if x["site"] == site
    )
    source = ROOT / source_info["source"]
    if file_sha256(source) != source_info["source_sha256"]:
        raise ValueError("Original brightness source changed")
    stem = {
        "ruby": "AOP_Ruby_20230814",
        "gordon": "AOP_GORDON_20230814",
        "goldhill": "AOP_GOLDHILL_20230814",
    }[site]
    indices = visible_indices(hdr_to_dict(source.with_suffix(".hdr"))["wavelength"])
    inventory_path = DEST / f"{site}_mask_inventory.json"
    inventory = (
        json.loads(inventory_path.read_text())
        if inventory_path.exists()
        else dict(mask_sha256={}, records=[])
    )
    with rasterio.open(source) as src:
        profile = dict(
            driver="GTiff",
            count=1,
            width=src.width,
            height=src.height,
            crs=src.crs,
            transform=src.transform,
            dtype="uint8",
            nodata=255,
            compress="deflate",
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )
        for variant, threshold in zip(VARIANTS, THRESHOLDS):
            if variant not in variants:
                continue
            mask_path = MASKS / refit.mask_filename(stem, threshold)
            prior = next(
                (r for r in inventory["records"] if r["variant"] == variant), None
            )
            if mask_path.exists() and prior:
                if file_sha256(mask_path) != inventory["mask_sha256"][mask_path.name]:
                    raise ValueError("Mask changed")
                continue
            valid = excluded = 0
            with rasterio.open(mask_path, "w", **profile) as dst:
                for row in range(0, src.height, 256):
                    window = Window(0, row, src.width, min(256, src.height - row))
                    mask, _ = classify(
                        src.read(window=window),
                        indices,
                        normalizer,
                        threshold,
                        src.nodata,
                    )
                    dst.write(mask, 1, window=window)
                    valid += int((mask != 255).sum())
                    excluded += int((mask == 1).sum())
                dst.update_tags(
                    status="EXPLORATORY_BRIGHTNESS_SCREEN",
                    relative_visible_threshold=str(threshold),
                    source_sha256=source_info["source_sha256"],
                )
            inventory["mask_sha256"][mask_path.name] = file_sha256(mask_path)
            inventory["records"].append(
                dict(
                    site=site,
                    variant=variant,
                    threshold=threshold,
                    valid_pixels=valid,
                    excluded_pixels=excluded,
                    excluded_fraction=excluded / valid,
                    source_sha256=source_info["source_sha256"],
                    normalization_p95=normalizer,
                )
            )
            write_json_atomic(inventory_path, inventory)
    return inventory_path


def run(site, variant=None):
    selected = VARIANTS if site == "ruby" and variant is None else [variant]
    if any(v not in VARIANTS for v in selected):
        raise ValueError("Select an explicit cross-site candidate")
    inventory = prepare_masks(site, selected)
    refit.DEST = DEST
    refit.MASKS = MASKS
    refit.POLICY = POLICY
    refit.run(site, mask_inventory_path=inventory, variants=selected)


def summarize():
    """Retain all six Ruby outcomes and the original 0/10% comparisons."""
    from drone_shade_refit_summary import band_support

    rows = []
    parent_counts = pd.read_csv(
        DEST.parent / "shade-review/candidate_exclusion_counts.csv"
    )
    conservative_fraction = float(
        parent_counts.loc[
            parent_counts.site.eq("ruby") & parent_counts.threshold.eq(0.1),
            "excluded_fraction",
        ].iloc[0]
    )
    records = json.loads((DEST / "ruby_mask_inventory.json").read_text())["records"]
    prior = DEST.parent / "shade-excluded-refit-v2/ruby"
    cases = [
        ("baseline", 0.0, prior / "baseline"),
        *[(v, t, DEST / "ruby" / v) for v, t in zip(VARIANTS, THRESHOLDS)],
        ("conservative", 0.1, prior / "conservative"),
    ]
    baseline_training = json.loads((prior / "baseline/summary.json").read_text())[
        "training_pixels"
    ]
    for variant, threshold, folder in cases:
        if not (folder / "completed.json").exists():
            raise ValueError(f"Incomplete: {variant}")
        model = json.loads(
            next((folder / "combined").glob("*brdf_model.json")).read_text()
        )
        topo = json.loads((folder / "conditioned_scsc_model.json").read_text())
        info = json.loads((folder / "summary.json").read_text())
        support = band_support(model)
        red = next(f for f in model["validation"]["fits"] if f["band"] == 5)
        mask = next((r for r in records if r["variant"] == variant), None)
        rows.append(
            dict(
                site="ruby",
                variant=variant,
                cutoff_fraction_of_p95=threshold,
                retained_training_pixels=info["training_pixels"],
                training_excluded_fraction=1
                - info["training_pixels"] / baseline_training,
                all_source_pixels_excluded_fraction=mask["excluded_fraction"]
                if mask
                else (0.0 if threshold == 0 else conservative_fraction),
                valid_combined_bands=support["valid_bands"],
                full_combined_fit_support=support["full_band_pass"]
                and all(f["status"] == "VALID" for f in topo["fits"]),
                red_668_status=red["status"],
                red_668_reference_margin=red.get("reference_prediction_lower_margin"),
                red_668_reference_prediction=red.get("reference_prediction"),
                red_668_reference_standard_error=red.get("reference_standard_error"),
            )
        )
    pd.DataFrame(rows).to_csv(DEST / "ruby_lighter_mask_results.csv", index=False)
    write_json_atomic(
        DEST / "result_manifest.json",
        dict(
            csv_sha256=file_sha256(DEST / "ruby_lighter_mask_results.csv"),
            code_sha256=file_sha256(__file__),
            passing_lighter_variants=[
                r["variant"]
                for r in rows
                if r["cutoff_fraction_of_p95"] < 0.1 and r["full_combined_fit_support"]
            ],
            exact_minimum_claimed=False,
            independent_validation=False,
            other_sites="No new cross-site candidate run: no lighter Ruby candidate passed; historical unmasked Gordon/Goldhill already pass.",
        ),
    )
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=["ruby", "gordon", "goldhill"])
    parser.add_argument("--variant", choices=VARIANTS)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        summarize()
    elif args.site:
        run(args.site, args.variant)
    else:
        parser.error("Specify --site or --summarize")
