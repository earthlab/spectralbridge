import h5py
import numpy as np
import pyarrow as pa

from spectralbridge.io.neon_schema import detect_legacy, resolve, canonical_vectors
from spectralbridge.pipelines.pipeline import CANONICAL_COLUMNS
from spectralbridge.pipelines.pipeline import _to_canonical_table


def _mk_h5(struct):
    f = h5py.File(b":memory:", "w")
    for path, arr in struct.items():
        grp = f
        parts = path.strip("/").split("/")
        for p in parts[:-1]:
            grp = grp.require_group(p)
        data = np.asarray(arr)
        grp.create_dataset(parts[-1], data=data)
    return f


def test_detect_legacy_true_false():
    f1 = _mk_h5(
        {
            "Reflectance/Reflectance_Data": np.zeros((1, 1, 1), np.float32),
            "Reflectance/Metadata/Spectral_Data/Wavelength": [1.0, 2.0],
            "Reflectance/Metadata/to-sun_Zenith_Angle": [30.0],
        }
    )
    try:
        assert detect_legacy(f1) is True
    finally:
        f1.close()

    f2 = _mk_h5(
        {
            "Reflectance/Reflectance_Data": np.zeros((1, 1, 1), np.float32),
            "Reflectance/Metadata/Spectral_Data/wavelength": [1.0, 2.0],
            "Reflectance/Metadata/to-sun_zenith_angle": [30.0],
        }
    )
    try:
        assert detect_legacy(f2) is False
    finally:
        f2.close()


def test_canonical_vectors_returns_float32():
    f = _mk_h5(
        {
            "Reflectance/Reflectance_Data": np.zeros((1, 1, 1), np.float32),
            "Reflectance/Metadata/Spectral_Data/Wavelength": [400.0, 500.0],
            "Reflectance/Metadata/Spectral_Data/FWHM": [5.0, 5.0],
            "Reflectance/Metadata/to-sun_Zenith_Angle": [30.0],
            "Reflectance/Metadata/to-sensor_Zenith_Angle": [15.0],
        }
    )
    try:
        resolved = resolve(f)
        wavelength_nm, fwhm_nm, to_sun_zenith, to_sensor_zenith = canonical_vectors(resolved)
        assert wavelength_nm.dtype == np.float32
        assert fwhm_nm.dtype == np.float32
        assert to_sun_zenith.dtype == np.float32
        assert to_sensor_zenith.dtype == np.float32
    finally:
        f.close()


def test_parquet_canonicalization():
    tbl = pa.table(
        {
            "flightline_id": ["X"],
            "row": [0],
            "col": [0],
            "x": [0.0],
            "y": [0.0],
            "band": [0],
            "Wavelength": [550.0],
            "reflectance": [0.1],
        }
    )
    out = _to_canonical_table(tbl)
    if hasattr(out, "column_names"):
        assert "wavelength_nm" in out.column_names
        if hasattr(out, "schema") and hasattr(pa, "float32"):
            assert out.schema.field("wavelength_nm").type == pa.float32()
            assert out.schema.field("reflectance").type == pa.float32()
        assert "fwhm_nm" in out.column_names
    else:  # pragma: no cover - pyarrow stub returns dict-like structure
        assert "wavelength_nm" in out
        assert "fwhm_nm" in out


def test_parquet_canonicalization_preserves_required_field_order_and_types():
    tbl = pa.table(
        {
            "flightline_id": ["X"],
            "row": [0],
            "col": [1],
            "x": [10.0],
            "y": [20.0],
            "band": [2],
            "wavelength": [550.0],
            "reflectance": [0.1],
        }
    )

    out = _to_canonical_table(tbl)

    if hasattr(out, "column_names"):
        assert out.column_names[: len(CANONICAL_COLUMNS)] == CANONICAL_COLUMNS
        if hasattr(out, "schema"):
            assert out.schema.field("flightline_id").type == pa.string()
            assert out.schema.field("row").type == pa.int64() or out.schema.field("row").type == pa.int32()
            assert out.schema.field("col").type == pa.int64() or out.schema.field("col").type == pa.int32()
            assert out.schema.field("x").type == pa.float64()
            assert out.schema.field("y").type == pa.float64()
            assert out.schema.field("band").type == pa.int64() or out.schema.field("band").type == pa.int32()
            assert out.schema.field("wavelength_nm").type == pa.float32()
            assert out.schema.field("fwhm_nm").type == pa.float32()
            assert out.schema.field("reflectance").type == pa.float32()
    else:  # pragma: no cover - pyarrow stub returns dict-like structure
        assert list(out.keys())[: len(CANONICAL_COLUMNS)] == CANONICAL_COLUMNS
