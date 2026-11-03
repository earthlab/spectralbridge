"""Read-only, real-data unit audit; bounded I/O, diagnostic outputs only."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import h5py
import numpy as np
import rasterio
from rasterio.windows import Window

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.radiometry import Radiometry, dataset_radiometry  # noqa: E402
from spectralbridge.neon_cube import NeonCube  # noqa: E402

WAVES = [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]
ORIGINAL = Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif")
BASE = ORIGINAL.parent / "base/goldhill.tif"
SCALED = ORIGINAL.parent / "rescale/goldhill.tif"
H5 = Path("/private/tmp/assumed-viewing-angles-20261103/goldhill_working.h5")
RECOVERED = Path(
    "/private/tmp/goldhill-radiometric-recovery-20261102/goldhill_recovered_source_dn.tif"
)
RAW = RECOVERED.parent / "normalized_raw.npy"
NEON = (
    ROOT
    / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
)
OLD = (
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
)
MODEL = (
    ROOT
    / "provenance/goldhill-correction-diagnosis/2026-10-30/saved_production_brdf_model.json"
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    protected = [ORIGINAL, BASE, SCALED, H5, RECOVERED, OLD, MODEL, NEON]
    before = {str(p): sha(p) for p in protected}
    print("Protected inputs hashed", flush=True)
    mins = np.full(10, np.inf)
    maxs = -mins.copy()
    with rasterio.open(ORIGINAL) as src:
        assert src.colorinterp[-1].name == "alpha"
        original_metadata = dict(
            shape=[src.height, src.width, src.count],
            dtype=src.dtypes[0],
            nodata=src.nodata,
            colorinterp=[x.name for x in src.colorinterp],
            scales=list(src.scales),
            offsets=list(src.offsets),
        )
        for y in range(0, src.height, 128):
            x = src.read(
                list(range(1, 11)),
                window=Window(0, y, src.width, min(128, src.height - y)),
            )
            mins = np.minimum(mins, x.min(axis=(1, 2)))
            maxs = np.maximum(maxs, x.max(axis=(1, 2)))
    mapping = []
    with rasterio.open(BASE) as a, rasterio.open(SCALED) as b:
        assert a.transform == b.transform and a.shape == b.shape and a.crs == b.crs
        for band in range(10):
            n = 0
            ss = 0.0
            err = 0.0
            lo = np.inf
            hi = -np.inf
            for y in range(0, a.height, 128):
                w = Window(0, y, a.width, min(128, a.height - y))
                dn = a.read(band + 1, window=w).astype(float)
                s = b.read(band + 1, window=w).astype(float)
                valid = np.isfinite(dn) & np.isfinite(s)
                predicted = (dn[valid] - mins[band]) * 10000 / (maxs[band] - mins[band])
                e = predicted - s[valid]
                n += e.size
                ss += float(e @ e)
                err = max(err, float(np.max(np.abs(e))))
                lo = min(lo, float(s[valid].min()))
                hi = max(hi, float(s[valid].max()))
            mapping.append(
                dict(
                    wavelength_nm=WAVES[band],
                    source_min=float(mins[band]),
                    source_max=float(maxs[band]),
                    numeric_multiplier=10000 / (maxs[band] - mins[band]),
                    numeric_offset=-mins[band] * 10000 / (maxs[band] - mins[band]),
                    paired_values=n,
                    max_abs_error=err,
                    rmse=(ss / n) ** 0.5,
                    scaled_25cm_range=[lo, hi],
                )
            )
    print("Independent 25 cm pairs verified", flush=True)
    raw = np.load(RAW, mmap_mode="r")
    shape = raw.shape[:2]
    with rasterio.open(RECOVERED) as src:
        assert src.shape == shape
        alpha = (
            src.read(11) > 0
        )  # Explicit prior source lineage: recovered original alpha, not inferred spectral data.
    valid = np.isfinite(raw[..., 0]) & (raw[..., 0] != -9999)
    diag = Radiometry(
        None,
        None,
        "UNSUPPORTED",
        "Independent 25 cm pairs verify normalization; physical calibration unavailable",
        encoding=dict(
            kind="range_normalized_dn",
            physical_calibration_status="UNVERIFIED",
            stored_units="range-normalized DN",
            source_units="Metashape UInt16 numerical output; physical calibration unverified",
            nodata=-9999,
            normalization=dict(
                stored_min=0,
                stored_max=10000,
                source_min=mins.tolist(),
                source_max=maxs.tolist(),
            ),
        ),
    )
    rows = []
    histogram = []
    positions = []
    native = []
    edges = np.linspace(0, 10000, 101)
    for band, wave in enumerate(WAVES):
        s = raw[..., band]
        good = np.isfinite(s) & (s != -9999)
        common = alpha & good
        historical = valid & np.isfinite(s) & (s >= 0) & (s <= 2)
        frac = diag.to_normalized_fraction(s, band_index=band)
        eligible = common & np.isfinite(frac) & (frac >= 0) & (frac <= 1)
        rows.append(
            dict(
                wavelength_nm=wave,
                total_image_pixels=int(s.size),
                legacy_finite_footprint=int(valid.sum()),
                source_alpha_footprint=int(alpha.sum()),
                nodata_quality_valid=int(common.sum()),
                historical_A=int(historical.sum()),
                historical_A_common_alpha=int((historical & alpha).sum()),
                diagnostic_B=int(eligible.sum()),
                B_excluded_negative=int((common & (frac < 0)).sum()),
                B_excluded_above_one=int((common & (frac > 1)).sum()),
                physical_C=None,
                physical_C_status="UNRESOLVED",
                production_brdf_eligible=None,
                independent_angular_design_rank=1,
                supported_brdf_fits=0,
                stored_range=[float(s[good].min()), float(s[good].max())],
                common_alpha_quantiles=np.quantile(
                    s[common], [0, 0.01, 0.5, 0.99, 1]
                ).tolist(),
                A_values=s[historical].astype(float).tolist(),
                B_fraction_quantiles=np.quantile(
                    frac[eligible], [0, 0.01, 0.5, 0.99, 1]
                ).tolist(),
            )
        )
        histogram.append(np.histogram(s[common], edges)[0])
        positions.append(np.argwhere(historical).tolist())
        native.append(np.histogram(frac[eligible], np.linspace(0, 1, 101))[0])
    expected = [3, 1, 9, 13, 14, 30, 8, 4, 1, 0]
    assert [r["historical_A"] for r in rows] == expected
    print("All ten historical counts reproduced", flush=True)
    # Execute the unchanged historical fitter on real Goldhill source and angles.
    spec = importlib.util.spec_from_file_location("p167_unchanged_historical", OLD)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    cube = NeonCube(H5)
    legacy = SimpleNamespace(
        data=raw,
        bands=10,
        wavelengths=cube.wavelengths,
        mask_no_data=valid,
        scale_factor=1.0,
        get_ancillary=cube.get_ancillary,
    )
    calls = []
    original_lstsq = np.linalg.lstsq

    def record_lstsq(x, y, *args, **kwargs):
        calls.append(len(y))
        return original_lstsq(x, y, *args, **kwargs)

    out = HERE / "historical_replay"
    if out.exists():
        raise RuntimeError(
            "Use a fresh diagnostic output directory; historical replay is not overwritten"
        )
    try:
        np.linalg.lstsq = record_lstsq
        result = old.fit_and_save_brdf_model(
            legacy, out, brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG
        )
    finally:
        np.linalg.lstsq = original_lstsq
    saved = json.loads(MODEL.read_text())
    replayed = json.loads(result.read_text())
    exact = {k: replayed[k] == saved[k] for k in ["iso", "vol", "geo"]}
    assert all(exact.values()) and calls == [n for n in expected if n >= 3]
    del cube, legacy
    print(
        "Unchanged historical fitter reproduces all coefficient arrays exactly",
        flush=True,
    )
    # Native 10-band NEON numerical audit, bounded by 128 lines.
    with h5py.File(NEON, "r") as h:
        d = h["R10C/Reflectance/Reflectance_Data"]
        wave = h["R10C/Reflectance/Metadata/Spectral_Data/Wavelength"][:]
        ix = np.array([np.argmin(abs(wave - x)) for x in WAVES])
        assert len(set(ix)) == 10
        calibration = dataset_radiometry(d, neon=True)
        stats = [
            dict(
                wavelength_nm=float(wave[i]),
                stored_min=np.inf,
                stored_max=-np.inf,
                physical_min=np.inf,
                physical_max=-np.inf,
                valid=0,
                eligible_0_2=0,
                negative=0,
            )
            for i in ix
        ]
        max_roundtrip = 0.0
        old_exact = True
        reference_error = 0.0
        for y in range(0, d.shape[0], 128):
            x = d[y : y + 128, :, ix]
            p = calibration.to_physical(x)
            v = calibration.valid_stored(x)
            prev = x.astype(np.float32) * np.float32(0.0001)
            old_exact &= np.array_equal(p[v], prev[v])
            reference_error = max(
                reference_error,
                float(np.max(abs(p[v] - (x.astype(float) * 0.0001)[v]))),
            )
            back = calibration.to_stored(p)
            max_roundtrip = max(max_roundtrip, float(np.max(abs(back[v] - x[v]))))
            for b, rec in enumerate(stats):
                good = v[..., b]
                s = x[..., b][good]
                r = p[..., b][good]
                rec["stored_min"] = min(rec["stored_min"], int(s.min()))
                rec["stored_max"] = max(rec["stored_max"], int(s.max()))
                rec["physical_min"] = min(rec["physical_min"], float(r.min()))
                rec["physical_max"] = max(rec["physical_max"], float(r.max()))
                rec["valid"] += int(good.sum())
                rec["eligible_0_2"] += int(((r >= 0) & (r <= 2)).sum())
                rec["negative"] += int((r < 0).sum())
        neon = dict(
            shape=list(d.shape),
            radiometry=calibration.record(),
            selected_bands=stats,
            max_roundtrip_dn_error=max_roundtrip,
            finite_values_bit_identical_to_previous_decoder=bool(old_exact),
            max_float64_reference_error=reference_error,
        )
    stride = 8
    np.savez_compressed(
        HERE / "display_arrays.npz",
        stored=raw[::stride, ::stride, 4],
        alpha=alpha[::stride, ::stride],
        valid=valid[::stride, ::stride],
        histograms=np.array(histogram),
        fraction_histograms=np.array(native),
        edges=edges,
    )
    after = {str(p): sha(p) for p in protected}
    assert before == after
    record = dict(
        original=original_metadata,
        numeric_mapping=mapping,
        normalization_code_status="No authoritative original export/normalization code recovered; observed max equals UInt16 max so those conventions cannot be distinguished",
        goldhill=rows,
        diagnostic_radiometry=diag.record(),
        historical_accepted_positions=positions,
        historical_replay=dict(
            module_sha256=before[str(OLD)],
            coefficient_arrays_bit_exact=exact,
            lstsq_population_sizes=calls,
            output=str(result.relative_to(ROOT)),
        ),
        neon=neon,
        protected_hashes=before,
        protected_files_unchanged=True,
        quality_limitations="Alpha is documented only in original TIFF/recovered lineage; no independent saturation or sensor-quality flags supplied; 65535 is not assumed to be a documented saturation flag",
        display_stride=stride,
    )
    (HERE / "results.json").write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            dict(red=rows[4], neon_roundtrip=max_roundtrip, protected=len(before)),
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
