"""Additional raw-defined homogeneous fitting experiment, no classifier selection."""

import json
from pathlib import Path
import sys
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment_support import WORK, write, load_cube, isolated, drone  # noqa:E402


def main():
    cube, design, digest, maps, profile = load_cube()
    raw = cube.data
    training = np.load(WORK / "training_mask.npy", mmap_mode="r")
    groups = np.load(WORK / "spatial_groups.npy", mmap_mode="r")
    valid = cube.mask_no_data & np.isfinite(raw).all(-1)
    weight = uniform_filter(valid.astype("float32"), size=31)
    hom = (
        valid
        & (weight > 0.99999)
        & ((raw[..., 9] - raw[..., 4]) / (raw[..., 9] + raw[..., 4] + 1e-20) > 0.5)
    )
    for b in [4, 9]:
        v = np.where(valid, raw[..., b], 0)
        mean = uniform_filter(v, size=31) / np.maximum(weight, 1e-20)
        variance = np.maximum(
            uniform_filter(v * v, size=31) / np.maximum(weight, 1e-20) - mean * mean, 0
        )
        hom &= np.sqrt(variance) / np.maximum(abs(mean), 1e-20) < 0.15
    selection = training & hom
    np.save(WORK / "homogeneous_fitting_mask.npy", selection)
    write(
        "homogeneous_full_plan.json",
        dict(
            criterion="RawNDVI>.5; complete31x31nativepixel window (~3.1m); red andNIRCV<.15; exclude evaluation-index pixels and20Manhattan-pixel dilation",
            fit_pixels=int(selection.sum()),
            source="uncorrected candidate signal only",
            classifier_tuning=False,
            scientific_status="EXPERIMENTAL",
        ),
    )
    model = json.loads((HERE / "conditioned_scsc_model.json").read_text())
    records = json.loads((HERE / "pipeline_results.json").read_text())
    rawstem = WORK / "candidate_working"
    for name, tm in [
        ("homogeneous_BRDF", None),
        ("homogeneous_conditioned_combined", model),
    ]:
        print("HOMOGENEOUS ACTUAL DRIVER", name, flush=True)
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
                apply_brdf=True,
                topographic_model=tm,
                brdf_fitting_mask=selection,
                brdf_fitting_provenance={
                    "strategy": "raw-defined NDVI and neighbourhood homogeneity; no class labels or corrected images used",
                    "calibration": "conditionalDN/32768",
                    "geometry": "center-weighted inferred kernels; contributors unknown",
                },
                brdf_uncertainty_groups=groups,
            )
            record = dict(
                branch=name,
                status="EXECUTED_EXPERIMENTAL",
                reason=None,
                audit=audit,
                image_created=True,
                envi=str(img),
                header=str(hdr),
            )
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
                path = WORK / (name + "_EXPERIMENTAL.tif")
                with rasterio.open(path, "w", **profile) as dst:
                    for b in range(10):
                        values = src.read(b + 1)
                        output[..., b] = values
                        dst.write(values, b + 1)
                        dst.set_band_description(b + 1, str(cube.wavelengths[b]) + "nm")
                    dst.update_tags(
                        STATUS="EXPERIMENTAL_NOT_VALIDATED",
                        CALIBRATION="HYPOTHETICAL_UNVERIFIED",
                        GEOMETRY="inferred center-weighted kernels; contributors unverified",
                        TOPOGRAPHY="scsc-fieller-spatial-v1"
                        if tm is not None
                        else "NOT_REQUESTED",
                        PRODUCTION_APPROVED="false",
                    )
                output.flush()
                record.update(image=str(path), array=str(WORK / (name + ".npy")))
        except Exception as exc:
            record = dict(
                branch=name,
                status="UNSUPPORTED",
                reason=str(exc),
                image_created=False,
                audit=getattr(exc, "audit", None),
            )
        models = list(folder.glob("*_brdf_model.json"))
        if models:
            (HERE / (name + "_model.json")).write_bytes(models[0].read_bytes())
        records = [r for r in records if r["branch"] != name]
        records.append(record)
        write("pipeline_results.json", records)
        print(name, record["status"], record.get("reason"), flush=True)


if __name__ == "__main__":
    main()
