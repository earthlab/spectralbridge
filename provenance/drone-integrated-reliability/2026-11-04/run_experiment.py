# ruff: noqa: E402
"""Prespecified source-independent fits and actual driver correction products."""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import binary_dilation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment_support import (
    ROOT,
    WORK,
    write,
    load_cube,
    isolated,
    topo,
    drone,
)  # noqa:E402
from spectralbridge.envi_writer import EnviWriter  # noqa:E402


def main():
    cube, design, digest, maps, profile = load_cube()
    raw = cube.data
    shape = raw.shape[:2]
    rr, cc = np.indices(shape)
    groups = (rr // 200) * 100 + (cc // 200)
    cfg = json.loads(
        (ROOT / "provenance/goldhill-end-to-end/2026-11-03/branches.json").read_text()
    )
    index = pd.read_parquet(cfg["polygon_index"])
    evaluation = np.zeros(shape, bool)
    evaluation[index.row, index.col] = True
    training = ~binary_dilation(evaluation, iterations=20)
    np.save(WORK / "training_mask.npy", training)
    np.save(WORK / "spatial_groups.npy", groups.astype("int32"))
    write(
        "prespecified_plan.json",
        dict(
            policy="SCS+C OLS; slope>=5deg; positive local incidence; physical0-2; spatial20mclusters; Fieller95%interval; entire numerator/denominator interval positive; no gain cap",
            BRDF="C center simulated kernels; evaluation polygons plus2m buffer excluded from fitting; unchanged shared reference/kernels/precision/prediction checks",
            cases=[
                "raw",
                "P173_BRDF_and_combined_baseline",
                "conditioned_topography",
                "controlled_OLS_BRDF",
                "controlled_cluster_BRDF",
                "conditioned_combined_OLS",
                "conditioned_combined_cluster",
            ],
            PFT_parameter_tuning=False,
            calibration="HYPOTHETICAL_UNVERIFIED",
            actual_contributors="NOT_RECOVERED",
            topographic_stage_required=True,
        ),
    )
    print("CONDITIONED SCS+C FIT", flush=True)
    model = isolated(topo.fit_conditioned_scs_c)(
        cube,
        policy=topo.SCSCPolicy(),
        uncertainty_groups=groups,
        fitting_mask=training,
        provenance={
            "fit_mask": "source-only training pixels; all researcher polygons plus2mbuffer excluded",
            "clusters": "20m x20m raster blocks, not independent pixel count",
            "calibration": "conditionalDN/32768",
            "geometry": "inherited slope/aspect/solar, datum unverified",
        },
    )
    write("conditioned_scsc_model.json", model)
    print(
        "SCS+C",
        model["validation_status"],
        [(r["band"], r["status"], r["C"], r["C_interval"]) for r in model["fits"]],
        flush=True,
    )
    # Actual driver consumes an explicit physical candidate working ENVI. It is
    # a new output of this experiment, never an overwrite of the source imagery.
    rawstem = WORK / "candidate_working"
    writer = EnviWriter(rawstem, cube.build_envi_header())
    for y in range(0, cube.lines, 128):
        writer.write_chunk(np.asarray(raw[y : y + 128], np.float32), y, 0)
    writer.close()
    cases = [
        ("conditioned_topography", False, model, None),
        ("controlled_OLS_BRDF", True, None, None),
        ("controlled_cluster_BRDF", True, None, groups),
        ("conditioned_combined_OLS", True, model, None),
        ("conditioned_combined_cluster", True, model, groups),
    ]
    records = []
    for name, brdf, tm, uncertainty in cases:
        print("ACTUAL DRONE DRIVER", name, flush=True)
        folder = WORK / name
        folder.mkdir(exist_ok=True)
        stem = folder / name
        try:
            img, hdr, audit = isolated(drone.apply_drone_corrections, design, digest)(
                cube=cube,
                envi_img=rawstem.with_suffix(".img"),
                envi_hdr=rawstem.with_suffix(".hdr"),
                corrected_stem=stem,
                apply_topo=tm is not None,
                apply_brdf=brdf,
                topographic_model=tm,
                brdf_fitting_mask=training if brdf else None,
                brdf_fitting_provenance={
                    "strategy": "exclude evaluation polygons plus2m buffer",
                    "geometry_source": "P173 center-weighted simulated kernels; contributors unverified",
                    "uncertainty": "20m spatial clusters"
                    if uncertainty is not None
                    else "conditional OLS computational uncertainty",
                }
                if brdf
                else None,
                brdf_uncertainty_groups=uncertainty,
            )
            status = "EXECUTED_EXPERIMENTAL"
            reason = None
        except Exception as exc:
            img = stem.with_suffix(".img")
            hdr = stem.with_suffix(".hdr")
            audit = getattr(exc, "audit", None)
            status = "UNSUPPORTED"
            reason = str(exc)
        models = list(folder.glob("*_brdf_model.json"))
        if models:
            (HERE / (name + "_model.json")).write_bytes(models[0].read_bytes())
        record = dict(
            branch=name,
            status=status,
            reason=reason,
            audit=audit,
            source_calibration="HYPOTHETICAL_UNVERIFIED",
            actual_contributors="NOT_VERIFIED",
            image_created=status == "EXECUTED_EXPERIMENTAL",
            envi=str(img),
            header=str(hdr),
        )
        if record["image_created"]:
            with rasterio.open(img) as src:
                output = np.lib.format.open_memmap(
                    WORK / (name + ".npy"), mode="w+", dtype="float32", shape=raw.shape
                )
                profile.update(
                    count=10,
                    dtype="float32",
                    nodata=np.nan,
                    compress="deflate",
                    predictor=3,
                    tiled=True,
                    blockxsize=256,
                    blockysize=256,
                )
                profile.pop("photometric", None)
                tif = WORK / (name + "_EXPERIMENTAL.tif")
                with rasterio.open(tif, "w", **profile) as dst:
                    for b in range(10):
                        values = src.read(b + 1)
                        output[..., b] = values
                        dst.write(values, b + 1)
                        dst.set_band_description(b + 1, str(cube.wavelengths[b]) + "nm")
                    dst.update_tags(
                        STATUS="EXPERIMENTAL_NOT_VALIDATED",
                        CALIBRATION="HYPOTHETICAL_UNVERIFIED",
                        GEOMETRY="P173 center-weighted simulated kernels; contributors unverified",
                        TOPOGRAPHY=topo.POLICY_VERSION
                        if tm is not None
                        else "NOT_REQUESTED",
                        PRODUCTION_APPROVED="false",
                    )
                output.flush()
                record.update(image=str(tif), array=str(WORK / (name + ".npy")))
        records.append(record)
        write("pipeline_results.json", records)
        print(name, status, reason, flush=True)
    # Full per-band status map: preserve unsupported separately from missing.
    quality = np.lib.format.open_memmap(
        WORK / "topographic_status.npy", mode="w+", dtype="uint8", shape=raw.shape
    )
    for y in range(0, cube.lines, 128):
        end = min(y + 128, cube.lines)
        result = isolated(topo.apply_conditioned_scs_c)(
            cube,
            np.asarray(raw[y:end], np.float32),
            y,
            end,
            0,
            cube.columns,
            model=model,
        )
        quality[y:end] = result.status
    quality.flush()
    qprofile = dict(profile, dtype="uint8", nodata=None, predictor=1)
    with rasterio.open(
        WORK / "conditioned_topographic_status.tif", "w", **qprofile
    ) as dst:
        for b in range(10):
            dst.write(quality[..., b], b + 1)
        dst.update_tags(
            STATUS_CODES="0 missing/invalid source or geometry;1 unsupported illumination/model;2 corrected",
            SCIENTIFIC_VALIDATION="EXPERIMENTAL",
        )
    write(
        "topographic_coverage.json",
        [
            dict(
                band=b,
                wavelength_nm=float(cube.wavelengths[b]),
                missing=int(np.sum(quality[..., b] == 0)),
                unsupported=int(np.sum(quality[..., b] == 1)),
                corrected=int(np.sum(quality[..., b] == 2)),
            )
            for b in range(10)
        ],
    )
    print("EXPERIMENT COMPLETE", flush=True)


if __name__ == "__main__":
    main()
