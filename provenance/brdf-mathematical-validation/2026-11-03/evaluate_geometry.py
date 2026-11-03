"""Read-only bounded-window evaluation of genuine NEON and Goldhill geometry."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge import corrections as current  # noqa: E402

OLD = (
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
)
spec = importlib.util.spec_from_file_location("p166_historical", OLD)
historical = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = historical
spec.loader.exec_module(historical)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def scalar_or_slice(dataset, window, shape):
    return (
        np.full(shape, dataset[()], np.float64)
        if dataset.ndim == 0
        else np.asarray(dataset[window], np.float64)
    )


def evaluate(name, path, prefix, solar_prefix, stride):
    with h5py.File(path, "r") as h:
        meta = h[prefix + "/Reflectance/Metadata"]
        sa, sz = (
            meta[solar_prefix + "Solar_Azimuth_Angle"],
            meta[solar_prefix + "Solar_Zenith_Angle"],
        )
        va, vz = meta["to-sensor_Azimuth_Angle"], meta["to-sensor_Zenith_Angle"]
        shape = h[prefix + "/Reflectance/Reflectance_Data"].shape[:2]
        if name == "goldhill":
            band = h[prefix + "/Reflectance/Reflectance_Data"][..., 0]
            base_valid = np.isfinite(band) & (band != -9999)
            solar_degrees = np.asarray(sz)
            scene = float(
                np.mean(
                    solar_degrees[base_valid & np.isfinite(solar_degrees)],
                    dtype=np.float64,
                )
            )
        else:
            base_valid = None
            scene = float(sz[()])
        display = {
            key: np.full(
                ((shape[0] + stride - 1) // stride, (shape[1] + stride - 1) // stride),
                np.nan,
            )
            for key in [
                "solar_zenith",
                "sensor_zenith",
                "sensor_azimuth",
                "solar_azimuth",
                "ross",
                "dense",
                "old_ross",
                "old_dense",
                "difference",
            ]
        }
        moments = {}
        r_factors = {"current": None, "historical": None}
        n = 0
        max_diff = (-1, None)
        for y0 in range(0, shape[0], 128):
            y1 = min(shape[0], y0 + 128)
            win = (slice(y0, y1), slice(None))
            tile_shape = (y1 - y0, shape[1])
            degrees = [scalar_or_slice(ds, win, tile_shape) for ds in [sa, sz, va, vz]]
            valid = np.logical_and.reduce(
                [np.isfinite(a) & (a != -9999) for a in degrees]
            )
            valid &= (
                (degrees[1] >= 0)
                & (degrees[1] < 90)
                & (degrees[3] >= 0)
                & (degrees[3] < 90)
            )
            if base_valid is not None:
                valid &= base_valid[win]
            degrees[1][:] = scene
            radians = [np.deg2rad(a) for a in degrees]
            kv = current.calc_volume_kernel(*radians, kernel_type="RossThick")
            kg = current.calc_geom_kernel(
                *radians, kernel_type="LiDenseR", b_r=10, h_b=2
            )
            old_angles = [a.astype(np.float32) for a in radians]
            old_kv = historical.calc_volume_kernel(*old_angles, kernel_type="RossThick")
            old_kg = historical.calc_geom_kernel(
                *old_angles, kernel_type="LiDenseR", b_r=10, h_b=2
            )
            valid &= np.isfinite(kv) & np.isfinite(kg) & np.isfinite(old_kg)
            fields = dict(
                solar_zenith=degrees[1],
                sensor_zenith=degrees[3],
                sensor_azimuth=degrees[2],
                solar_azimuth=degrees[0],
                ross=kv,
                dense=kg,
                old_ross=old_kv,
                old_dense=old_kg,
                difference=kg - old_kg,
            )
            n += int(valid.sum())
            for key, a in fields.items():
                values = a[valid].astype(np.float64)
                if len(values):
                    rec = moments.setdefault(
                        key,
                        dict(
                            n=0, min=float("inf"), max=-float("inf"), mean=0.0, M2=0.0
                        ),
                    )
                    count = len(values)
                    mean = float(values.mean())
                    m2 = float(np.sum((values - mean) ** 2))
                    delta = mean - rec["mean"]
                    total = rec["n"] + count
                    rec["M2"] += m2 + delta * delta * rec["n"] * count / total
                    rec["mean"] += delta * count / total
                    rec["n"] = total
                    rec["min"] = min(rec["min"], float(values.min()))
                    rec["max"] = max(rec["max"], float(values.max()))
                # Sample actual native centers, never average invalid/background values.
                rows = np.arange(y0, y1)
                keep = rows % stride == 0
                sampled = np.where(valid, a, np.nan)[keep, ::stride]
                display[key][rows[keep] // stride] = sampled
            diff = np.where(valid, np.abs(kg - old_kg), -1)
            index = np.unravel_index(np.argmax(diff), diff.shape)
            if diff[index] > max_diff[0]:
                max_diff = (float(diff[index]), [int(y0 + index[0]), int(index[1])])
            for kind, first, second in [
                ("current", kv, kg),
                ("historical", old_kv, old_kg),
            ]:
                design = np.column_stack(
                    [np.ones(int(valid.sum())), first[valid], second[valid]]
                ).astype(np.float64)
                if len(design):
                    r = np.linalg.qr(design, mode="r")
                    previous = r_factors[kind]
                    r_factors[kind] = (
                        r
                        if previous is None
                        else np.linalg.qr(np.vstack([previous, r]), mode="r")
                    )
            if y0 % 512 == 0:
                print(name, y1, "/", shape[0], "native rows evaluated", flush=True)
        designs = {}
        for kind, r in r_factors.items():
            sv = np.linalg.svd(r, compute_uv=False)
            tol = sv[0] * max(n, 3) * np.finfo(float).eps
            designs[kind] = dict(
                n=n,
                rank=int((sv > tol).sum()),
                singular_values=sv.tolist(),
                rank_tolerance=float(tol),
                condition_number=float(sv[0] / sv[-1]) if sv[-1] > 0 else None,
                condition_limit=float(1 / np.sqrt(np.finfo(np.float32).eps)),
                method="Streaming tall-skinny QR followed by SVD; no normal-equation rank estimate",
            )
        for rec in moments.values():
            rec["std"] = float(np.sqrt(rec.pop("M2") / rec["n"]))
            rec["range"] = rec["max"] - rec["min"]
        np.savez_compressed(HERE / f"{name}_geometry_display.npz", **display)
        return dict(
            path=str(path),
            source_shape=list(shape),
            positive_polar_geometry_pixels=n,
            scene_solar_zenith_degrees=scene,
            display_stride=stride,
            statistics=moments,
            designs=designs,
            maximum_absolute_dense_difference=dict(
                value=max_diff[0], native_row_column=max_diff[1]
            ),
            source_geometry_status="Genuine archived NEON AOP sensor angles; scene solar log"
            if name == "neon"
            else "Zero sensor placeholders; derived solar, acquisition time unverified",
            mask="Finite valid polar geometry; Goldhill additionally finite native source band; no source masks rewritten",
        )


def finalize_evidence(result):
    """Derive honest rank-deficient conditioning and a synthetic signal control."""
    from types import SimpleNamespace
    from spectralbridge.radiometry import Radiometry

    for flight in result["flights"].values():
        for record in flight["designs"].values():
            sv = record["singular_values"]
            record["raw_singular_value_ratio"] = sv[0] / sv[-1] if sv[-1] > 0 else None
            record["condition_number"] = (
                record["raw_singular_value_ratio"] if record["rank"] == 3 else None
            )
            record["condition_status"] = (
                "finite full-rank design"
                if record["rank"] == 3
                else "infinite for the rank-deficient model; tiny trailing SVD values are roundoff"
            )
    gold = np.load(HERE / "goldhill_geometry_display.npz")
    good = np.isfinite(gold["solar_azimuth"])
    indices = np.flatnonzero(good)[:256]
    solar = result["flights"]["goldhill"]["scene_solar_zenith_degrees"]
    az = gold["solar_azimuth"].ravel()[indices].reshape(16, 16)
    degrees = dict(
        solar_zn=np.full((16, 16), solar),
        solar_az=az,
        sensor_az=np.zeros((16, 16)),
        sensor_zn=np.zeros((16, 16)),
    )
    data = np.full((16, 16, 10), 0.3, np.float32)
    cube = SimpleNamespace(
        data=data,
        bands=10,
        mask_no_data=np.ones((16, 16), bool),
        wavelengths=np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862]),
        no_data=-9999.0,
        radiometry=Radiometry(
            1.0,
            0.0,
            "VALID",
            "Synthetic constant signal mathematical control ONLY; not Goldhill calibration",
        ),
    )
    cube.get_ancillary = lambda name, radians=True: (
        np.deg2rad(degrees[name]).astype(np.float32) if radians else degrees[name]
    )
    target = current.fit_and_save_brdf_model(
        cube,
        HERE / "synthetic_signal_real_geometry_control",
        brdf_kernel_config=current.HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    model = json.loads(target.read_text())
    assert model["validation"]["status"] == "UNSUPPORTED"
    assert all(f["rank"] == 1 for f in model["validation"]["fits"])
    assert not any(k in model for k in ["iso", "vol", "geo"])
    result["real_geometry_synthetic_signal_gate_control"] = dict(
        signal="Synthetic constant .3 in ten bands; never a Goldhill reflectance fit",
        geometry="Actual sampled Goldhill solar azimuth, actual scene solar zenith, stored zero sensor placeholders",
        supported_band_fits=0,
        unsupported_band_fits=len(model["validation"]["fits"]),
        rejection_status=model["validation"]["status"],
        model_path=str(target.relative_to(HERE)),
    )
    return result


def main():
    neon = (
        ROOT
        / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
    )
    gold = Path("/private/tmp/assumed-viewing-angles-20261103/goldhill_working.h5")
    model = (
        ROOT
        / "provenance/goldhill-correction-diagnosis/2026-10-30/saved_production_brdf_model.json"
    )
    protected = [neon, gold, OLD, model]
    before = {str(p): sha(p) for p in protected}
    result = dict(kernel_math_version=current.BRDF_KERNEL_MATH_VERSION, flights={})
    result["flights"]["neon"] = evaluate("neon", neon, "R10C", "Logs/", 4)
    result["flights"]["goldhill"] = evaluate(
        "goldhill", gold, "AOP-GOLDHILL-08-14-23-ExportPackage", "", 6
    )
    az = np.linspace(-2 * np.pi, 4 * np.pi, 361)
    solar = np.deg2rad(result["flights"]["goldhill"]["scene_solar_zenith_degrees"])
    values = current.calc_geom_kernel(az, solar, 0, 0, kernel_type="LiDenseR", b_r=10)
    result["goldhill_arbitrary_nadir_azimuth_range"] = float(np.ptp(values))
    result["goldhill_support"] = dict(
        angular_rank=result["flights"]["goldhill"]["designs"]["current"]["rank"],
        three_parameter_fit="UNSUPPORTED",
        radiometry="Unverified; no calibration assigned or real reflectance coefficients fitted",
        historical_model="Unchanged; incompatible version cannot be applied by current code",
    )
    result = finalize_evidence(result)
    after = {str(p): sha(p) for p in protected}
    assert before == after
    result["preservation"] = dict(
        before=before, after=after, unchanged=True, production_writes=False
    )
    (HERE / "real_geometry_validation.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    print(
        "Real geometry validation complete; source/model/historical hashes unchanged",
        flush=True,
    )


if __name__ == "__main__":
    main()
