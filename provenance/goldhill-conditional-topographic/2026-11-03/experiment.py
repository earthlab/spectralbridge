"""Isolated conditional experiment. No production calibration promotion or monkeypatch.

Clones only function namespace bindings; original bytecode is retained. Experimental
Radiometry calls the existing affine kernel directly while require_valid still rejects
its HYPOTHETICAL_UNVERIFIED record. No product may enter physical production APIs.
"""

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy.ndimage import binary_dilation
from sklearn.linear_model import HuberRegressor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge import corrections as current  # noqa: E402
from spectralbridge.radiometry import Radiometry  # noqa: E402
from spectralbridge.pipelines.drone import _compute_solar_geometry_arrays  # noqa: E402

WORK = Path("/private/tmp/goldhill-conditional-topographic-20261103")
SOURCE = Path(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
)
PRIOR = ROOT / "provenance/goldhill-end-to-end/2026-11-03"
WAVES = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
SCALE = 0.0001999969482421875
SEED = 20261103


def safe(x):
    if isinstance(x, dict):
        return {str(k): safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [safe(v) for v in x]
    if isinstance(x, np.generic):
        return safe(x.item())
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def write(name, x):
    (HERE / name).write_text(json.dumps(safe(x), indent=2, allow_nan=False) + "\n")


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


class HypothesisRadiometry(Radiometry):
    """Diagnostic affine adapter: never VALID and still rejected by production."""

    def to_physical(self, values, *, band_index=None):
        return self._affine(values, self.scale, self.offset, band_index=band_index)

    def to_stored(self, values, *, band_index=None):
        return self._affine(
            values, self.scale, self.offset, inverse=True, band_index=band_index
        )


def isolated(function):
    namespace = dict(function.__globals__)
    namespace["require_radiometry"] = lambda cube: cube.radiometry
    clone = types.FunctionType(
        function.__code__,
        namespace,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


class Cube:
    def __init__(self, data, mask, geometry, scale=1.0):
        self.data, self.mask_no_data, self.geometry = data, mask.copy(), geometry
        self.lines, self.columns, self.bands = data.shape
        self.scale_factor, self.no_data = scale, np.nan
        self.radiometry = HypothesisRadiometry(
            scale,
            0,
            "HYPOTHETICAL_UNVERIFIED",
            "MicaSense_Metashape_DN_32768; isolated P171 experiment",
        )

    def get_ancillary(self, name, radians=True):
        return self.geometry[name] if radians else np.rad2deg(self.geometry[name])

    def iter_chunks(self, chunk_y=128, chunk_x=None):
        for y in range(0, self.lines, chunk_y):
            z = min(self.lines, y + chunk_y)
            yield y, z, 0, self.columns, self.data[y:z]


def distribution(v):
    v = np.asarray(v)
    v = v[np.isfinite(v)]
    if not v.size:
        return {"n": 0}
    return dict(
        n=len(v),
        quantiles=np.quantile(v, [0, 0.001, 0.01, 0.25, 0.5, 0.75, 0.99, 0.999, 1]),
        mean=v.mean(),
        negative=int((v < 0).sum()),
        above_one=int((v > 1).sum()),
    )


def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx = x - x.mean()
    slope = dx @ (y - y.mean()) / (dx @ dx)
    intercept = y.mean() - slope * x.mean()
    residual = y - slope * x - intercept
    return slope, intercept, residual


def denominator_support(ci, ref, c, c_low, c_high, xmin, xmax, source_mask):
    # Both numerator/denominator must remain positive across block-bootstrap C.
    # No gain cap; uncertainty interval is an experimental decision aid.
    return (
        source_mask
        & (ci > 0)
        & (ci >= xmin)
        & (ci <= xmax)
        & (ci + c_low > current.MIN_SCS_C_DENOM)
        & (ref + c_low > 0)
        & np.isfinite(c_high)
        & np.isfinite(c)
    )


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    old_path = (
        ROOT
        / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
    )
    spec = importlib.util.spec_from_file_location("p171_historical", old_path)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    geometry_paths = {
        n: Path("/private/tmp/goldhill-end-to-end-20261103/ancillary")
        / f"legacy_{n}.tif"
        for n in ["slope", "aspect", "solar_zn", "solar_az"]
    }
    config = json.loads((PRIOR / "branches.json").read_text())
    protected = [
        SOURCE,
        old_path,
        ROOT / "src/spectralbridge/corrections.py",
        ROOT / "src/spectralbridge/radiometry.py",
        ROOT / "src/spectralbridge/pipelines/drone.py",
        Path(config["polygon_index"]),
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg",
        *geometry_paths.values(),
        Path(config["branches"]["new_historical_topo"]["path"]),
    ]
    protected.extend(p for p in PRIOR.iterdir() if p.is_file())
    hashes = {str(p): sha(p) for p in protected}
    write(
        "input_manifest.json",
        {
            "protected_hashes": hashes,
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        },
    )
    with rasterio.open(SOURCE) as src:
        stored = src.read().transpose(1, 2, 0)
        mask = src.dataset_mask() > 0
        profile = dict(
            crs=str(src.crs),
            transform=list(src.transform),
            height=src.height,
            width=src.width,
        )
        geometry = {}
        for n, p in geometry_paths.items():
            with rasterio.open(p) as g:
                assert g.shape == src.shape and g.crs == src.crs
                np.testing.assert_allclose(
                    tuple(g.transform), tuple(src.transform), atol=1e-6, rtol=0
                )
                values = g.read(1)
                values[~(g.read_masks(1) > 0)] = np.nan
                geometry[n] = np.deg2rad(values).astype("float32")
        lon, lat = Transformer.from_crs(src.crs, 4326, always_xy=True).transform(
            *src.xy(src.height // 2, src.width // 2)
        )
    cube = Cube(stored, mask, geometry, SCALE)
    try:
        cube.radiometry.require_valid()
    except ValueError:
        pass
    else:
        raise AssertionError("Hypothesis incorrectly accepted by production")
    raw = cube.radiometry.to_physical(stored)
    raw[~mask] = np.nan
    np.save(WORK / "raw.npy", raw)
    ci = current.calc_cosine_i(
        geometry["solar_zn"],
        geometry["solar_az"],
        geometry["aspect"],
        geometry["slope"],
    )
    ref = np.cos(geometry["solar_zn"]) * np.cos(geometry["slope"])
    geomvalid = (
        mask
        & np.isfinite(ci)
        & np.isfinite(ref)
        & (geometry["slope"] >= 0)
        & (geometry["slope"] <= np.pi / 2)
    )
    np.savez_compressed(
        HERE / "geometry_arrays.npz",
        **{k: v[::6, ::6] for k, v in geometry.items()},
        ci=ci[::6, ::6],
        mask=mask[::6, ::6],
    )
    index = pd.read_parquet(config["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    # Exclude all evaluated polygon pixels plus 2 m buffer from fitting variants.
    evaluation = np.zeros(mask.shape, bool)
    evaluation[rr, cc] = True
    exclusion = binary_dilation(evaluation, iterations=20)
    eligible = geomvalid & (ci > 0) & (geometry["slope"] > np.deg2rad(5)) & ~exclusion
    np.save(WORK / "fit_eligible.npy", eligible)
    candidate_cube = Cube(raw, mask, geometry)
    fits = {}
    for name, func, c in [
        ("historical", old.fit_scs_c_coefficients, cube),
        ("current", isolated(current.fit_scs_c_coefficients), cube),
        (
            "eligible",
            isolated(current.fit_scs_c_coefficients),
            Cube(raw, eligible, geometry),
        ),
    ]:
        print("FIT", name, flush=True)
        fits[name] = func(c, chunk_y=128)
    # Test scale invariance in actual package current fit, not just algebra.
    fit_fraction = isolated(current.fit_scs_c_coefficients)(candidate_cube, chunk_y=128)
    fit_fixed = isolated(current.fit_scs_c_coefficients)(
        Cube(stored, mask, geometry, 1e-4), chunk_y=128
    )
    write(
        "scale_invariance.json",
        dict(
            C_candidate=fits["current"],
            C_decoded_once=fit_fraction,
            C_fixed_fraction=fit_fixed,
            max_abs_C_difference=float(np.max(abs(fits["current"] - fit_fixed))),
            max_abs_C_decode_difference=float(
                np.max(abs(fits["current"] - fit_fraction))
            ),
            analytic="For R*=kR, a*=ka,b*=kb, C*=b*/a*=C; factors unchanged unless near-zero slope fallback changes state. Offset and masks must match.",
        ),
    )
    print("REGRESSION diagnostics and spatial block bootstrap", flush=True)
    # Deterministic 1-in-17 scene sample, blocks 20 m x 20 m; no label use.
    rows, cols = np.indices(mask.shape)
    sampled = (np.arange(mask.size).reshape(mask.shape) % 17) == 0
    sel = eligible & sampled
    x = ci[sel].astype(float)
    yy = raw[sel].astype(float)
    blocks = (rows[sel] // 200) * 100 + (cols[sel] // 200)
    unique = np.unique(blocks)
    rng = np.random.default_rng(SEED)
    stats = []
    uncertainties = []
    bootstrap = []
    robust_c = []
    for b, w in enumerate(WAVES):
        slope, intercept, res = ols(x, yy[:, b])
        huber = HuberRegressor(epsilon=1.35, alpha=0, max_iter=300).fit(
            x[:, None], yy[:, b]
        )
        robust_c.append(huber.intercept_ / huber.coef_[0])
        sums = []
        for block in unique:
            z = blocks == block
            xx = x[z]
            y = yy[z, b]
            sums.append([z.sum(), xx.sum(), y.sum(), xx @ xx, xx @ y])
        sums = np.asarray(sums)
        draw = rng.integers(0, len(unique), (399, len(unique)))
        total = sums[draw].sum(axis=1)
        n, sx, sy, sxx, sxy = total.T
        a = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        bb = (sy - a * sx) / n
        cs = bb / a
        low, high = np.quantile(cs, [0.025, 0.975])
        uncertainties.append([low, high])
        bootstrap.append(cs)
        for name, fitmask in [
            ("historical", geomvalid),
            ("current", geomvalid),
            ("eligible", eligible),
        ]:
            xx = ci[fitmask].astype(float)
            y = raw[..., b][fitmask].astype(float)
            aa, bb0, resid = ols(xx, y)
            den = xx + fits[name][b]
            stats.append(
                dict(
                    method=name,
                    wavelength_nm=int(w),
                    n=len(xx),
                    slope=aa,
                    intercept=bb0,
                    C=float(fits[name][b]),
                    r2=1 - np.sum(resid**2) / np.sum((y - y.mean()) ** 2),
                    rmse=np.sqrt(np.mean(resid**2)),
                    residual_quantiles=np.quantile(resid, [0, 0.01, 0.5, 0.99, 1]),
                    illumination_min=xx.min(),
                    illumination_max=xx.max(),
                    denominator=distribution(den),
                )
            )
        stats.append(
            dict(
                method="robust_Huber_sample",
                wavelength_nm=int(w),
                n=len(x),
                slope=huber.coef_[0],
                intercept=huber.intercept_,
                C=robust_c[-1],
                rmse=np.sqrt(np.mean((yy[:, b] - huber.predict(x[:, None])) ** 2)),
                C_block_bootstrap_OLS_interval=[low, high],
            )
        )
    write("regression_diagnostics.json", stats)
    write(
        "coefficient_uncertainty.json",
        dict(
            OLS_block_bootstrap_C=np.array(bootstrap),
            C_intervals=uncertainties,
            blocks=len(unique),
            draws=399,
            subsample_stride=17,
            fit_pixels=int(eligible.sum()),
            sample_pixels=int(sel.sum()),
            polygon_buffer_m=2,
        ),
    )
    fits["robust"] = np.array(robust_c, np.float32)
    # A bounded alternative already in the package: cosine normalization.
    branches = {"raw": dict(path=str(WORK / "raw.npy"), format="npy")}
    fullsupport = {}
    factors = []
    extremes = []
    display = {}
    stabmask = geomvalid.copy()
    for b in range(10):
        lo, hi = uncertainties[b]
        stabmask &= denominator_support(
            ci,
            ref,
            fits["eligible"][b],
            lo,
            hi,
            float(x.min()),
            float(x.max()),
            geomvalid,
        )
    np.save(WORK / "stable_support.npy", stabmask)
    for name, C in [
        ("historical", fits["historical"]),
        ("current", fits["current"]),
        ("eligible_OLS", fits["eligible"]),
        ("robust_Huber", fits["robust"]),
        ("stabilized", fits["eligible"]),
        ("cosine", np.zeros(10)),
    ]:
        print("APPLY", name, flush=True)
        out = np.lib.format.open_memmap(
            WORK / f"{name}.npy", mode="w+", dtype="float32", shape=raw.shape
        )
        usemask = (
            stabmask
            if name == "stabilized"
            else (geomvalid & (ci > 0) if name == "cosine" else geomvalid)
        )
        c = Cube(raw, usemask, geometry)
        func = (
            old.apply_topo_correct
            if name == "historical"
            else isolated(current.apply_topo_correct)
        )
        for ys, ye, xs, xe, chunk in c.iter_chunks(128):
            out[ys:ye] = func(
                c, chunk, ys, ye, xs, xe, use_scs_c=name != "cosine", scs_c=C
            )
        out.flush()
        branches[name] = dict(path=str(WORK / f"{name}.npy"), format="npy")
        support = np.isfinite(out).all(axis=-1)
        fullsupport[name] = support
        np.save(WORK / f"{name}_support.npy", support)
        for b, w in enumerate(WAVES):
            valid = support & (raw[..., b] > 0)
            ratio = out[..., b][valid] / raw[..., b][valid]
            factors.append(
                dict(
                    branch=name,
                    wavelength_nm=int(w),
                    **distribution(ratio),
                    above10=int((ratio > 10).sum()),
                    above100=int((ratio > 100).sum()),
                    native_support=int(support.sum()),
                )
            )
        redratio = np.divide(
            out[..., 4],
            raw[..., 4],
            out=np.full(mask.shape, np.nan, np.float32),
            where=raw[..., 4] > 0,
        )
        k = np.nanargmax(redratio)
        r, c0 = np.unravel_index(k, mask.shape)
        extremes.append(
            dict(
                branch=name,
                row=r,
                col=c0,
                red_factor=redratio[r, c0],
                illumination=ci[r, c0],
                C_red=C[4],
                denominator=ci[r, c0] + C[4],
                slope_deg=np.rad2deg(geometry["slope"][r, c0]),
            )
        )
        for label, a in [
            ("red", out[..., 4]),
            ("nir", out[..., 9]),
            ("factor", redratio),
            ("difference", out[..., 4] - raw[..., 4]),
        ]:
            display[f"{name}_{label}"] = a[::6, ::6].copy()
        del out
    common = mask & np.logical_and.reduce(list(fullsupport.values()))
    np.save(WORK / "common.npy", common)
    for label, a in [
        ("raw_red", raw[..., 4]),
        ("raw_nir", raw[..., 9]),
        ("eligible", eligible),
        ("stable", stabmask),
        ("common", common),
        ("shadow", geomvalid & (ci <= 0)),
    ]:
        display[label] = a[::6, ::6]
    np.savez_compressed(HERE / "display_arrays.npz", **display)
    write(
        "branches.json",
        dict(
            branches=branches,
            profile=profile,
            polygon_index=config["polygon_index"],
            work=WORK,
            common_pixels=int(common.sum()),
            raw_pixels=int(mask.sum()),
            geometry_valid_pixels=int(geomvalid.sum()),
            self_shadow_pixels=int((geomvalid & (ci <= 0)).sum()),
            missing_geometry_pixels=int((mask & ~geomvalid).sum()),
            stabilized_pixels=int(stabmask.sum()),
        ),
    )
    write("coefficients.json", fits)
    write("factor_statistics.json", factors)
    write("extreme_pixels.json", extremes)
    # Replay must match the previous experiment, apart from the declared global scale.
    previous = np.load(config["branches"]["new_historical_topo"]["path"], mmap_mode="r")
    replay = np.load(WORK / "historical.npy", mmap_mode="r")
    check = np.isfinite(replay) & np.isfinite(previous) & (previous != -9999)
    write(
        "historical_reproduction.json",
        dict(
            max_abs_candidate_error=float(
                np.max(abs(replay[check] - previous[check] * SCALE))
            ),
            red_factor=extremes[0],
            previous_red_max=309.9168395996094,
        ),
    )
    # Geometry alternatives use package's UTC solar function; no visual selection.
    time_cases = {
        "UTC_inherited": "2023-08-15T19:53:07",
        "UTC_start": "2023-08-15T19:42:38",
        "UTC_end": "2023-08-15T20:03:47",
        "UTC_midpoint": "2023-08-15T19:53:12.500000",
        "local_MDT_interpretation": "2023-08-16T01:53:07",
        "nominal_package_local": "2023-08-14T19:41:00",
    }
    timing = []
    time_display = {}
    for name, t in time_cases.items():
        z, az = _compute_solar_geometry_arrays(
            acquisition_datetime=datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
            longitude=np.array([[lon]]),
            latitude=np.array([[lat]]),
        )
        g = dict(geometry)
        g["solar_zn"] = np.full(mask.shape, np.deg2rad(z.item()), np.float32)
        g["solar_az"] = np.full(mask.shape, np.deg2rad(az.item()), np.float32)
        incidence = current.calc_cosine_i(
            g["solar_zn"], g["solar_az"], g["aspect"], g["slope"]
        )
        re = np.cos(g["solar_zn"]) * np.cos(g["slope"])
        c = isolated(current.fit_scs_c_coefficients)(Cube(raw, mask, g), chunk_y=128)
        den = incidence + c[4]
        num = re + c[4]
        ratio = current._scs_c_ratio(num, den)
        timing.append(
            dict(
                case=name,
                UTC=t,
                zenith_deg=z.item(),
                azimuth_deg=az.item(),
                C=c,
                incidence=distribution(incidence[geomvalid]),
                self_shadow_pixels=int((geomvalid & (incidence <= 0)).sum()),
                red_factor=distribution(ratio[geomvalid]),
                above10=int((ratio[geomvalid] > 10).sum()),
                red_factor_relative_to_inherited=None,
            )
        )
        time_display[name] = incidence[::6, ::6]
    write("solar_sensitivity.json", timing)
    np.savez_compressed(HERE / "solar_maps.npz", **time_display)
    assert all(sha(p) == v for p, v in hashes.items())
    write(
        "experiment_configuration.json",
        dict(
            status="HYPOTHETICAL_UNVERIFIED",
            calibration_hypothesis="MicaSense_Metashape_DN_32768",
            scale=SCALE,
            offset=0,
            units="candidate fractional reflectance",
            protected_files_unchanged=True,
            protected_count=len(hashes),
            production_guard_still_rejects=True,
            production_changes=0,
            BRDF_applied=False,
            factor_clipping=False,
            affine_kernel="Radiometry._affine; isolated HypothesisRadiometry",
            cloned_bytecode_functions=["fit_scs_c_coefficients", "apply_topo_correct"],
            eligibility="Positive illumination; slope>5 degrees for fitting; no evaluated polygon or 2m buffer in eligible/robust fit; application within fit illumination span and positive numerator/denominator over 95% spatial-block C interval. No brightness threshold or factor cap.",
            prespecified="Huber epsilon=1.35, no regularization; OLS C uncertainty399 block draws, 20m blocks; all choices before PFT evaluation; no selection by classification.",
        ),
    )
    print("EXPERIMENT COMPLETE", flush=True)


if __name__ == "__main__":
    main()
