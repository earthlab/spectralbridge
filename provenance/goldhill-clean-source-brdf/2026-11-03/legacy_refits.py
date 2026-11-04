"""Invoke pinned historical fitter on revised populations; never apply its unsupported fits."""

import json
from pathlib import Path
import sys
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import WORK, LEGACY, Cube, load_module, write, sha  # noqa:E402


def main():
    old = load_module("p172_pinned_legacy_refits", LEGACY)
    masks = np.load(HERE / "filter_masks.npz")
    geometry = {}
    for name in ["solar_zn", "solar_az", "slope", "aspect"]:
        with rasterio.open(
            f"/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_{name}.tif"
        ) as src:
            geometry[name] = src.read(1)
    geometry.update(
        sensor_zn=np.zeros(masks["source_valid"].shape, np.float32),
        sensor_az=np.zeros(masks["source_valid"].shape, np.float32),
    )
    audits = json.loads((HERE / "fitting_population_and_rank.json").read_text())
    for name, source, mask in [
        ("C", "old_candidate.npy", "C_revised_prefit"),
        ("D", "clean_candidate.npy", "D_revised_prefit"),
    ]:
        data = np.load(WORK / source, mmap_mode="r")
        cube = Cube(data, masks[mask], geometry, scale=1)
        path = old.fit_and_save_brdf_model(
            cube,
            WORK / f"{name}_pinned_legacy_fit",
            brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        model = json.loads(path.read_text())
        assert all(
            r.get("stable_rank", 0) == 1
            for r in audits[name + "_revised_historical_math"]
        )
        write(
            f"{name}_historical_refit_unsupported.json",
            dict(
                status="UNSUPPORTED",
                actual_function="pinned historical fit_and_save_brdf_model",
                module_sha256=sha(LEGACY),
                calibration_status="HYPOTHETICAL_UNVERIFIED",
                coefficient_status="NON_IDENTIFIABLE_DIAGNOSTIC_ONLY; no image or usable current model",
                diagnostic_legacy_fit=model,
                stable_rank=1,
                source_population=mask,
                model_applied=False,
            ),
        )
        print(
            name,
            "actual historical fit recorded, stable rank1, not applied",
            flush=True,
        )


if __name__ == "__main__":
    main()
