"""Permanent production-boundary and golden Ruby encoding regressions."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pytest
from spectralbridge.drone_radiometry import (
    radiometry_from_source_encoding,
    resolve_drone_source,
    SOURCE_ATTRIBUTE,
)

FIXTURE = Path(__file__).parent / "data/drone_radiometry/ruby_verified.tif"


def declaration(name, **extra):
    return dict(
        schema_version=1,
        input_encoding=name,
        verification_status="VERIFIED_ENCODING",
        processing_state="calibrated_reflectance",
        provenance="Explicit synthetic verified encoding",
        **extra,
    )


@pytest.mark.parametrize(
    "encoding,stored,expected",
    [
        (
            "metashape_micasense_reflectance_uint16_v1",
            [0, 8192, 32768, 49152],
            [0, 0.25, 1, 1.5],
        ),
        (
            "metashape_micasense_65535_to_10000_v1",
            [0, 8192 * 10000 / 65535, 32768 * 10000 / 65535],
            [0, 0.25, 1],
        ),
        ("reflectance_times_10000", [0, 2500, 10000, 15000], [0, 0.25, 1, 1.5]),
        ("reflectance_fraction", [0, 0.25, 1, 1.5], [0, 0.25, 1, 1.5]),
    ],
)
def test_named_representations_decode_once(encoding, stored, expected):
    r = radiometry_from_source_encoding(declaration(encoding))
    np.testing.assert_allclose(r.to_physical(stored), expected, rtol=2e-7, atol=1e-8)
    np.testing.assert_allclose(
        r.to_stored(r.to_physical(stored)), stored, rtol=2e-7, atol=0.002
    )
    assert r.encoding["independent_physical_accuracy"] == "UNVERIFIED"


def test_explicit_band_offsets_nodata_nan_and_zero_are_distinct():
    r = radiometry_from_source_encoding(
        declaration(
            "explicit_calibrated_affine",
            scale=[0.001, 0.002],
            offset=[0.1, -0.1],
            nodata=-9999,
        )
    )
    np.testing.assert_allclose(
        r.to_physical([[0, 100], [2000, -9999], [np.nan, 0]]),
        [[0.1, 0.1], [2.1, np.nan], [np.nan, -0.1]],
        equal_nan=True,
        rtol=1e-6,
    )


@pytest.mark.parametrize(
    "record",
    [
        declaration("raw_micasense_sensor_dn"),
        declaration("unknown"),
        declaration("metashape_micasense_reflectance_uint16_v1", scale=0.0001),
        declaration("reflectance_times_10000", apply_sensor_calibration=True),
        declaration("reflectance_fraction", offset=0.1),
    ],
)
def test_raw_unknown_contradictory_and_double_calibration_fail(record):
    with pytest.raises(ValueError):
        radiometry_from_source_encoding(record).require_valid()


def test_numeric_range_and_camera_filename_do_not_establish_calibration(tmp_path):
    p = tmp_path / "MicaSense_Metashape_10000.tif"
    p.write_bytes(b"not a calibration certificate")
    assert resolve_drone_source(p).radiometry is None


def test_sidecar_binds_source_and_prevents_conflicting_explicit_scale(tmp_path):
    p = tmp_path / "source.h5"
    p.write_bytes(b"fake source for boundary test")
    side = p.with_suffix(".h5.radiometry.json")
    side.write_text(
        json.dumps(
            dict(
                source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                declaration=declaration("reflectance_times_10000"),
            )
        )
    )
    assert resolve_drone_source(p).radiometry.scale == 0.0001
    from spectralbridge.radiometry import Radiometry

    with pytest.raises(ValueError, match="conflicts"):
        resolve_drone_source(
            p,
            explicit=Radiometry(
                0.0002, 0, "VALID", "Incorrect double scaling"
            ).record(),
        )
    p.write_bytes(b"different source")
    with pytest.raises(ValueError, match="SHA256"):
        resolve_drone_source(p)


def test_golden_ruby_automatic_tiff_h5_envi_roundtrip(tmp_path):
    from spectralbridge.pipelines.drone import (
        convert_drone_tiff_to_h5,
        export_h5_to_envi,
    )
    from spectralbridge.neon_cube import NeonCube
    from spectralbridge.radiometry import Radiometry
    from spectralbridge.envi import hdr_to_dict
    import rasterio

    manifest = json.loads(FIXTURE.with_suffix(".json").read_text())
    assert (
        hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == manifest["fixture_sha256"]
    )
    h = convert_drone_tiff_to_h5(FIXTURE, output_h5_path=tmp_path / "derived.h5")
    cube = NeonCube(h)
    assert cube.bands == 10 and cube.wavelengths[-1] == 842
    np.testing.assert_allclose(cube.data[0, 0], manifest["pixel_0_0_DN"])
    np.testing.assert_allclose(
        cube.radiometry.to_physical(cube.data[0, 0]),
        manifest["pixel_0_0_reflectance"],
        rtol=2e-7,
    )
    image, header = export_h5_to_envi(h, output_stem=tmp_path / "native")
    r = Radiometry.from_header(hdr_to_dict(header))
    assert r.scale == 1 / 32768
    with rasterio.open(FIXTURE) as source, rasterio.open(image) as out:
        assert source.transform == out.transform and source.crs == out.crs
        assert out.count == 10
        np.testing.assert_allclose(
            r.to_physical(out.read()[:, 0, 0]),
            manifest["pixel_0_0_reflectance"],
            rtol=2e-7,
        )
    assert hdr_to_dict(header)["reflectance scale factor"] == 32768
    assert (
        hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == manifest["fixture_sha256"]
    )
    with pytest.raises(ValueError, match="wavelength"):
        convert_drone_tiff_to_h5(
            FIXTURE,
            output_h5_path=tmp_path / "wrong.h5",
            wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
        )


def test_typed_h5_metadata_and_nonzero_affine_preserved(tmp_path):
    import h5py
    from spectralbridge.radiometry import dataset_radiometry

    with h5py.File(tmp_path / "typed.h5", "w") as h:
        d = h.create_dataset(
            "Reflectance/Reflectance_Data", data=[0, 2500, 15000, np.nan]
        )
        d.attrs[SOURCE_ATTRIBUTE] = json.dumps(declaration("reflectance_times_10000"))
        r = dataset_radiometry(d)
        np.testing.assert_allclose(
            r.to_physical(d[:]), [0, 0.25, 1.5, np.nan], rtol=2e-7, equal_nan=True
        )
        d.attrs["spectralbridge_radiometry"] = json.dumps(
            dict(
                scale=0.0002,
                offset=0,
                status="VALID",
                provenance="Conflicting legacy assumption",
            )
        )
        with pytest.raises(ValueError, match="Conflicting"):
            dataset_radiometry(d)


def test_legacy_h5_checksum_sidecar_is_attached_only_to_working_copy(tmp_path):
    import h5py
    from spectralbridge.pipelines.drone import (
        convert_drone_tiff_to_h5,
        _prepare_drone_source_working_h5,
    )
    from spectralbridge.neon_cube import NeonCube

    source = convert_drone_tiff_to_h5(FIXTURE, output_h5_path=tmp_path / "legacy.h5")
    with h5py.File(source, "r+") as h:
        d = next(v for v in h.values()).get("Reflectance/Reflectance_Data")
        del d.attrs["spectralbridge_source_encoding"]
        del d.attrs["spectralbridge_radiometry"]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    source.with_suffix(".h5.radiometry.json").write_text(
        json.dumps(
            dict(
                source_sha256=digest,
                declaration=declaration(
                    "metashape_micasense_reflectance_uint16_v1",
                    wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 842],
                ),
            )
        )
    )
    prepared, _ = _prepare_drone_source_working_h5(
        source, source_type="h5", working_path=tmp_path / "derived__working.h5"
    )
    assert NeonCube(prepared).radiometry.scale == 1 / 32768
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_golden_origin_is_in_packaged_verified_registry():
    from importlib.resources import files

    registry = json.loads(
        files("spectralbridge")
        .joinpath("data/drone_radiometric_sources.json")
        .read_text()
    )
    fixture = json.loads(FIXTURE.with_suffix(".json").read_text())
    assert any(
        r["sha256"] == fixture["original_source_sha256"] for r in registry["sources"]
    )


def test_golden_polygon_parquet_contains_fraction_once(tmp_path):
    import pandas as pd
    import pyarrow.parquet as pq
    from spectralbridge.pipelines.drone import (
        convert_drone_tiff_to_h5,
        export_h5_to_envi,
        apply_drone_corrections,
    )
    from spectralbridge.neon_cube import NeonCube
    from spectralbridge.polygons import extract_polygon_parquet_from_envi

    h = convert_drone_tiff_to_h5(FIXTURE, output_h5_path=tmp_path / "source.h5")
    cube = NeonCube(h)
    image, header = export_h5_to_envi(h, output_stem=tmp_path / "native")
    raw, rawhdr, _ = apply_drone_corrections(
        cube=cube,
        envi_img=image,
        envi_hdr=header,
        corrected_stem=tmp_path / "raw_explicitly_requested",
        apply_topo=False,
        apply_brdf=False,
    )
    index = tmp_path / "index.parquet"
    pd.DataFrame(
        dict(
            pixel_id=[0],
            polygon_id=[1],
            row=[0],
            col=[0],
            x=[cube.transform[0]],
            y=[cube.transform[3]],
        )
    ).to_parquet(index, index=False)
    out = extract_polygon_parquet_from_envi(
        raw, rawhdr, index, tmp_path / "raw__polygon.parquet"
    )
    table = pq.read_table(out)
    frame = table.to_pandas()
    values = [float(frame[c].iloc[0]) for c in frame if c.startswith("raw_b")]
    expected = json.loads(FIXTURE.with_suffix(".json").read_text())[
        "pixel_0_0_reflectance"
    ]
    assert len(values) == 10
    np.testing.assert_allclose(values, expected, rtol=2e-7)
    assert (
        table.schema.metadata[b"spectralbridge.reflectance_units"]
        == b"physical_reflectance_v1"
    )


def test_typed_h5_rejects_conflicting_nodata(tmp_path):
    import h5py
    from spectralbridge.radiometry import dataset_radiometry

    with h5py.File(tmp_path / "nodata.h5", "w") as h:
        d = h.create_dataset("Reflectance/Reflectance_Data", data=[0, -9999])
        d.attrs["Data_Ignore_Value"] = -9999
        d.attrs[SOURCE_ATTRIBUTE] = json.dumps(
            declaration("reflectance_times_10000", nodata=-999)
        )
        with pytest.raises(ValueError, match="NoData declarations disagree"):
            dataset_radiometry(d)


def test_explicit_wavelengths_cannot_override_recognized_identity():
    bad = declaration(
        "metashape_micasense_reflectance_uint16_v1",
        wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
    )
    import rasterio

    with rasterio.open(FIXTURE) as source:
        with pytest.raises(ValueError, match="wavelength"):
            resolve_drone_source(FIXTURE, metadata=source.tags(), explicit=bad)
