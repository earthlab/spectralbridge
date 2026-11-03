"""Unit-aware affine conversion, diagnostic normalization and source-mask contracts."""

import json

import h5py
import numpy as np
import pytest

from spectralbridge.radiometry import Radiometry, dataset_radiometry


def test_neon_documented_divisor_and_nodata_are_decoded_once(tmp_path):
    with h5py.File(tmp_path / "source.h5", "w") as h:
        d = h.create_dataset("data", data=np.array([0, 3500, -9999], np.int16))
        d.attrs.update(Scale_Factor=10000.0, Data_Ignore_Value=-9999, Units="Unitless.")
        r = dataset_radiometry(d, neon=True)
        np.testing.assert_allclose(r.to_physical(d[:])[:2], [0, 0.35], atol=3e-8)
        assert np.isnan(r.to_physical(d[:])[2])
        assert r.record()["encoding"]["source_scale_direction"] == "divisor"
        assert r.record()["encoding"]["kind"] == "scaled_physical_reflectance"
        assert r.scale == 0.0001


def test_per_band_affine_round_trip_and_no_data():
    r = Radiometry(
        [0.0001, 0.0002],
        [0.05, -0.1],
        "VALID",
        "Synthetic band calibration",
        encoding={
            "kind": "scaled_physical_reflectance",
            "nodata": -9999,
            "physical_calibration_status": "VERIFIED",
        },
    )
    x = np.array([[0, 1000], [5000, -9999]], np.float32)
    physical = r.to_physical(x)
    np.testing.assert_allclose(
        physical, [[0.05, 0.1], [0.55, np.nan]], atol=8e-8, equal_nan=True
    )
    np.testing.assert_allclose(
        r.to_stored(physical), [[0, 1000], [5000, np.nan]], atol=0.001, equal_nan=True
    )
    np.testing.assert_allclose(
        r.to_physical(np.array([1000, 2000]), band_index=1), [0.1, 0.3], atol=4e-8
    )
    with pytest.raises(ValueError, match="band"):
        r.to_physical(np.ones((2, 3)))
    assert (
        Radiometry.from_record(json.loads(json.dumps(r.record()))).record()
        == r.record()
    )


def test_range_fraction_is_explicitly_diagnostic_not_physical():
    r = Radiometry(
        None,
        None,
        "UNSUPPORTED",
        "Verified numerical encoding; no physical calibration",
        encoding={
            "kind": "range_normalized_dn",
            "stored_units": "range-normalized DN",
            "physical_calibration_status": "UNVERIFIED",
            "nodata": -9999,
            "normalization": {
                "stored_min": 0,
                "stored_max": 10000,
                "source_min": [0, 174],
                "source_max": [65535, 65535],
            },
        },
    )
    values = np.array([[0, 5000], [-9999, 10000]], np.float32)
    np.testing.assert_allclose(
        r.to_normalized_fraction(values), [[0, 0.5], [np.nan, 1]], equal_nan=True
    )
    with pytest.raises(ValueError, match="Radiometry"):
        r.to_physical(values)
    with pytest.raises(ValueError, match="Radiometry"):
        Radiometry(
            0.0001, 0, "VALID", "False promotion", encoding=r.encoding
        ).require_valid()


def test_explicit_saturation_and_nodata_are_distinct_from_zero_or_negative_signal():
    r = Radiometry(
        1,
        0,
        "VALID",
        "Synthetic known quality semantics",
        encoding={
            "kind": "fractional_physical_reflectance",
            "nodata": -9999,
            "saturation": {
                "status": "DOCUMENTED",
                "value": 65535,
                "provenance": "Synthetic saturation flag",
            },
        },
    )
    x = np.array([0, -0.1, 1.2, -9999, 65535, np.nan, np.inf], np.float32)
    np.testing.assert_array_equal(
        r.valid_stored(x), [True, True, True, False, False, False, False]
    )
    assert r.to_physical(x)[0] == 0 and r.to_physical(x)[1] < 0
    assert np.isnan(r.to_physical(x)[3:]).all()


def test_full_affine_header_contract_round_trips_with_vectors(tmp_path):
    from spectralbridge.envi_writer import build_envi_header_text
    from spectralbridge.envi import hdr_to_dict

    r = Radiometry(
        [0.1, 0.2],
        [0.3, 0.4],
        "VALID",
        "Synthetic full metadata",
        encoding={
            "kind": "scaled_physical_reflectance",
            "source_units": "synthetic counts",
            "stored_units": "scaled reflectance",
            "nodata": "NaN",
            "scale_direction": "multiplier",
            "valid_numerical_range": [0, 10000],
            "quality_mask": {"status": "NOT_PROVIDED"},
        },
    )
    header = {
        "samples": 2,
        "lines": 2,
        "bands": 2,
        "data type": 4,
        "byte order": 0,
        "interleave": "bsq",
        "projection": "EPSG:32613",
        "map info": ["UTM", 1, 1, 0, 2, 1, 1, 13, "North", "WGS-84"],
        "wavelength": [650, 860],
        "wavelength units": "Nanometers",
        **r.header(),
    }
    path = tmp_path / "data.hdr"
    path.write_text(build_envi_header_text(header))
    assert Radiometry.from_header(hdr_to_dict(path)).record() == r.record()


def test_unknown_and_contradictory_scale_direction_are_rejected():
    with pytest.raises(ValueError, match="Radiometry"):
        Radiometry(
            1, 0, "VALID", "Missing units", encoding={"kind": "unknown"}
        ).require_valid()

    with pytest.raises(ValueError, match="Radiometry"):
        Radiometry(
            10000,
            0,
            "VALID",
            "Wrong direction",
            encoding={
                "kind": "scaled_physical_reflectance",
                "scale_direction": "divisor",
            },
        ).require_valid()


def test_declared_tiff_alpha_and_partial_band_nodata_survive_ingestion(tmp_path):
    import hashlib
    import rasterio
    from rasterio.enums import ColorInterp
    from rasterio.transform import from_origin
    from spectralbridge.pipelines.drone import convert_drone_tiff_to_h5
    from spectralbridge.neon_cube import NeonCube
    from spectralbridge.io.neon import read_neon_cube

    path = tmp_path / "source.tif"
    data = np.full((4, 3, 3), 1000, np.float32)
    data[3] = 255
    data[3, 0, 0] = 0
    data[:3, 0, 1] = 0  # Legitimate zero, positive alpha.
    data[0, 1, 1] = -9999  # Other band remains observed.
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=4,
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4400000, 1, 1),
        nodata=-9999,
    ) as dst:
        dst.write(data)
        dst.colorinterp = (
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.alpha,
        )
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    r = Radiometry(0.0001, 0, "VALID", "Synthetic TIFF calibration")
    h5 = convert_drone_tiff_to_h5(
        path,
        output_h5_path=tmp_path / "derived.h5",
        wavelengths_nm=[444, 650, 860],
        fwhm_nm=[20, 20, 20],
        radiometry=r.record(),
    )
    cube = NeonCube(h5)
    assert cube.bands == 3
    assert not cube.mask_no_data[0, 0]
    assert cube.mask_no_data[0, 1] and cube.mask_no_data[1, 1]
    assert cube.data[0, 1, 0] == 0
    assert np.isnan(cube.radiometry.to_physical(cube.data)[1, 1, 0])
    assert cube.radiometry.to_physical(cube.data)[1, 1, 1] == pytest.approx(0.1)
    _, _, meta = read_neon_cube(h5, sample_slice=(1, 3), line_slice=(0, 2))
    np.testing.assert_array_equal(
        meta["source_valid_mask"], cube.source_valid_mask[:2, 1:3]
    )
    assert cube.radiometry.encoding["source_alpha_band_indices"] == [4]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_h5_explicit_mask_is_applied_without_mutating_stored_values(tmp_path):
    from spectralbridge.neon_cube import NeonCube

    # A tiny standard reader fixture; masks have declared, not inferred semantics.
    path = tmp_path / "source.h5"
    with h5py.File(path, "w") as h:
        group = h.create_group("TEST/Reflectance")
        d = group.create_dataset(
            "Reflectance_Data", data=np.full((3, 4, 2), 1000, np.float32)
        )
        d.attrs["Data_Ignore_Value"] = -9999
        meta = group.create_group("Metadata")
        spectral = meta.create_group("Spectral_Data")
        spectral.create_dataset("Wavelength", data=[650.0, 860.0]).attrs["Units"] = (
            "Nanometers"
        )
        spectral.create_dataset("FWHM", data=[20.0, 20.0])
        cs = meta.create_group("Coordinate_System")
        cs.create_dataset(
            "Map_Info", data=np.bytes_("UTM,1,1,500000,4400000,1,1,13,North,WGS-84")
        )
        cs.create_dataset("Coordinate_System_String", data=np.bytes_("EPSG:32613"))
        mask = np.ones((3, 4), bool)
        mask[1, 2] = False
        m = meta.create_dataset("Source_Valid_Mask", data=mask)
        d.attrs["spectralbridge_valid_mask_path"] = m.name
        r = Radiometry(
            0.0001,
            0,
            "VALID",
            "Synthetic H5 calibration",
            encoding={
                "kind": "scaled_physical_reflectance",
                "source_valid_mask_path": m.name,
            },
        )
        d.attrs["spectralbridge_radiometry"] = json.dumps(r.record())
    before = path.read_bytes()
    cube = NeonCube(path)
    assert cube.data[1, 2, 0] == 1000 and not cube.mask_no_data[1, 2]
    chunk = next(cube.iter_chunks(chunk_y=3, chunk_x=4))[-1]
    assert (chunk[1, 2] == -9999).all() and cube.data[1, 2, 0] == 1000
    assert path.read_bytes() == before


def test_output_identity_contract_replaces_inherited_scaled_contract():
    scaled = Radiometry(
        0.0001,
        0,
        "VALID",
        "Synthetic original encoding",
        encoding={"kind": "scaled_physical_reflectance"},
    )
    header = scaled.header()
    header.update(Radiometry(1, 0, "VALID", "Decoded physical output").header())
    output = Radiometry.from_header(header)
    assert output.scale == 1
    np.testing.assert_array_equal(
        output.to_physical(np.array([0.35], np.float32)), np.array([0.35], np.float32)
    )
    header["physical reflectance multiplier"] = 0.0001
    with pytest.raises(ValueError, match="disagree"):
        Radiometry.from_header(header)


@pytest.mark.parametrize("scale,offset", [([0.0001, 0.0002], 0), (0.0001, 0.05)])
def test_stored_space_convolution_refuses_noncommuting_affine_encoding(
    tmp_path, scale, offset
):
    from spectralbridge.pipelines.pipeline import convolve_resample_product

    path = tmp_path / "input.hdr"
    # Failure precedes dimensions/raster access and output creation.
    header = Radiometry(
        scale, offset, "VALID", "Synthetic affine convolution input"
    ).header()
    path.write_text(
        "ENVI\n"
        + "\n".join(
            f"{k} = {v}"
            for k, v in header.items()
            if k
            not in {"physical reflectance multiplier", "physical reflectance offset"}
        )
    )
    with pytest.raises(ValueError, match="common zero-offset"):
        convolve_resample_product(path, {"red": np.array([1, 1])}, tmp_path / "output")
    assert not (tmp_path / "output.img").exists()
