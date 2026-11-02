"""Reproduce the saved red/green BRDF fits from their exact eligible source pixels."""

from pathlib import Path
import json
import sys
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.corrections import (  # noqa: E402
    calc_volume_kernel,
    calc_geom_kernel,
    _resolve_scene_solar_zenith,
)

F = Path(
    "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products/2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814"
)
EVIDENCE = Path(__file__).resolve().parent
model = json.loads((F / (F.name + "__brdf_model.json")).read_text())
report = []
with h5py.File(F / (F.name + "__working.h5")) as h:
    group = next(iter(h.values()))["Reflectance"]
    data = group["Reflectance_Data"]
    m = group["Metadata"]
    scene_zn = _resolve_scene_solar_zenith(
        np.deg2rad(m["Solar_Zenith_Angle"][()].astype("float32"))
    )[0, 0]
    for band in [3, 4]:
        positions = []
        responses = []
        for start in range(0, data.shape[0], 128):
            block = data[start : start + 128, :, band]
            rr, cc = np.where(np.isfinite(block) & (block >= 0) & (block <= 2))
            positions.extend(zip((rr + start).tolist(), cc.tolist()))
            responses.extend(block[rr, cc].tolist())
        sa = np.deg2rad(
            np.asarray(
                [m["Solar_Azimuth_Angle"][r, c] for r, c in positions], dtype="float32"
            )
        ).reshape(1, -1)
        sz = np.full_like(sa, scene_zn)
        zero = np.zeros_like(sa)
        kv = calc_volume_kernel(sa, sz, zero, zero, kernel_type="RossThick")
        kg = calc_geom_kernel(
            sa, sz, zero, zero, kernel_type="LiDenseR", b_r=10.0, h_b=2.0
        )
        design = np.column_stack(
            [np.ones(kv.size, dtype="float32"), kv.ravel(), kg.ravel()]
        ).astype("float64")
        solution, residuals, rank, singular = np.linalg.lstsq(
            design, np.asarray(responses, dtype="float64"), rcond=None
        )
        actual = np.asarray(
            [model[key][0][band] for key in ["iso", "vol", "geo"]], dtype="float32"
        )
        expected = solution.astype("float32")
        report.append(
            {
                "band": band + 1,
                "training_pixels": len(responses),
                "rank": int(rank),
                "parameters": 3,
                "singular_values": singular.tolist(),
                "saved_coefficients": actual.tolist(),
                "reconstructed_coefficients": expected.tolist(),
                "coefficient_exact_match": bool(np.array_equal(actual, expected)),
                "eligible_source_row_col": positions,
            }
        )
        assert np.array_equal(actual, expected)
(EVIDENCE / "fit_reconstruction.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        [
            {k: v for k, v in r.items() if k != "eligible_source_row_col"}
            for r in report
        ],
        indent=2,
    )
)
