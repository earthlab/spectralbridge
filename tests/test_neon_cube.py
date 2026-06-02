from pathlib import Path

import numpy as np
import pytest

from spectralbridge.io.neon import _orient_cube, read_neon_cube
from spectralbridge.neon_cube import NeonCube

h5py = pytest.importorskip("h5py")


def _create_fake_neon_file(path: Path) -> None:
    wavelengths = np.array([400, 410, 420, 430, 440], dtype=np.float32)
    fwhm = np.array([10, 10, 10, 10, 10], dtype=np.float32)
    map_info = [
        "UTM",
        "1.0",
        "1.0",
        "500000.0",
        "4420000.0",
        "1.0",
        "-1.0",
        "13",
        "North",
        "WGS-84",
    ]

    data = np.zeros((20, 20, 5), dtype=np.float32)
    for y in range(20):
        for x in range(20):
            for b in range(5):
                data[y, x, b] = y * 1000 + x * 10 + b

    with h5py.File(path, "w") as h5_file:
        base_group = h5_file.create_group("TEST_KEY")
        reflectance_group = base_group.create_group("Reflectance")
        reflectance_dataset = reflectance_group.create_dataset(
            "Reflectance_Data", data=data, dtype=np.float32
        )
        reflectance_dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)

        metadata_group = reflectance_group.create_group("Metadata")
        spectral_group = metadata_group.create_group("Spectral_Data")
        wavelength_ds = spectral_group.create_dataset("Wavelength", data=wavelengths)
        wavelength_ds.attrs["Units"] = "Nanometers"
        spectral_group.create_dataset("FWHM", data=fwhm)

        coordinate_group = metadata_group.create_group("Coordinate_System")
        coordinate_group.create_dataset(
            "Map_Info", data=np.array(map_info, dtype="S")
        )
        coordinate_group.create_dataset(
            "Coordinate_System_String",
            data=np.array("FAKE PROJECTION WKT", dtype="S"),
        )


def _create_fake_legacy_neon_file(path: Path) -> None:
    wavelengths = np.array([500, 600, 700], dtype=np.float32)
    fwhm = np.array([5, 5, 5], dtype=np.float32)
    map_info = [
        "UTM",
        "1.0",
        "1.0",
        "500000.0",
        "4420000.0",
        "1.0",
        "-1.0",
        "13",
        "North",
        "WGS-84",
    ]

    data = np.zeros((10, 10, 3), dtype=np.float32)
    for y in range(10):
        for x in range(10):
            for b in range(3):
                data[y, x, b] = y * 100 + x * 10 + b

    with h5py.File(path, "w") as h5_file:
        reflectance_group = h5_file.create_group("Reflectance")
        reflectance_dataset = reflectance_group.create_dataset(
            "Reflectance",
            data=data,
            dtype=np.float32,
        )
        reflectance_dataset.attrs["NoData"] = np.float32(-9999.0)

        metadata_group = reflectance_group.create_group("Metadata")
        spectral_group = metadata_group.create_group("Spectral")
        wavelength_ds = spectral_group.create_dataset("Wavelengths", data=wavelengths)
        wavelength_ds.attrs["Unit"] = "Nanometers"
        spectral_group.create_dataset("FWHM", data=fwhm)

        coordinate_group = metadata_group.create_group("Coordinates")
        coordinate_group.create_dataset(
            "Map_Info", data=np.array(map_info, dtype="S")
        )
        coordinate_group.create_dataset(
            "Projection", data=np.array("LEGACY PROJECTION", dtype="S")
        )


def _create_fake_site_group_legacy_file(path: Path) -> None:
    wavelengths = np.linspace(400, 420, 5, dtype=np.float32)
    fwhm = np.full(5, 10, dtype=np.float32)
    data = np.arange(20 * 10 * 5, dtype=np.float32).reshape(20, 10, 5)

    map_info = [
        "UTM",
        "1.0",
        "1.0",
        "500000.0",
        "4420000.0",
        "1.0",
        "-1.0",
        "13",
        "North",
        "WGS-84",
    ]

    with h5py.File(path, "w") as h5_file:
        site_group = h5_file.create_group("NIWO")
        reflectance_group = site_group.create_group("Reflectance")
        reflectance_ds = reflectance_group.create_dataset(
            "Reflectance_Data", data=data, dtype=np.float32
        )
        reflectance_ds.attrs["Data_Ignore_Value"] = np.float32(-9999.0)

        metadata_group = reflectance_group.create_group("Metadata")
        spectral_group = metadata_group.create_group("Spectral_Data")
        wavelength_ds = spectral_group.create_dataset("Wavelength", data=wavelengths)
        wavelength_ds.attrs["Units"] = "Nanometers"
        spectral_group.create_dataset("FWHM", data=fwhm)

        coordinate_group = metadata_group.create_group("Coordinate_System")
        coordinate_group.create_dataset("Map_Info", data=np.array(map_info, dtype="S"))
        coordinate_group.create_dataset(
            "Coordinate_System_String",
            data=np.array("LEGACY SITE PROJECTION", dtype="S"),
        )


def _create_fake_neon_file_missing_nodata(path: Path) -> None:
    _create_fake_neon_file(path)
    with h5py.File(path, "r+") as h5_file:
        reflectance_dataset = h5_file["TEST_KEY/Reflectance/Reflectance_Data"]
        for attr_name in ("Data_Ignore_Value", "_FillValue", "NoData", "no_data"):
            reflectance_dataset.attrs.pop(attr_name, None)


def _orientation_contract_grid(offset: float = 0.0) -> np.ndarray:
    return np.array(
        [
            [11.0, 12.0, 13.0, 14.0],
            [21.0, 22.0, 23.0, 24.0],
            [31.0, 32.0, 33.0, 34.0],
        ],
        dtype=np.float32,
    ) + np.float32(offset)


def _create_fake_orientation_contract_file(
    path: Path,
    *,
    cube_layout: str = "yxb",
    ancillary_overrides: dict[str, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    wavelengths = np.array([550.0, 660.0], dtype=np.float32)
    fwhm = np.array([10.0, 10.0], dtype=np.float32)
    map_info = [
        "UTM",
        "1.0",
        "1.0",
        "500000.0",
        "4420000.0",
        "1.0",
        "-1.0",
        "13",
        "North",
        "WGS-84",
    ]

    reflectance_band_0 = _orientation_contract_grid()
    reflectance_band_1 = _orientation_contract_grid(offset=100.0)
    cube_yxb = np.stack([reflectance_band_0, reflectance_band_1], axis=2)

    ancillary = {
        "Slope": _orientation_contract_grid(offset=200.0),
        "Aspect": _orientation_contract_grid(offset=300.0),
        "Solar_Zenith_Angle": _orientation_contract_grid(offset=400.0),
        "Solar_Azimuth_Angle": _orientation_contract_grid(offset=500.0),
        "To_Sensor_Zenith_Angle": _orientation_contract_grid(offset=600.0),
        "To_Sensor_Azimuth_Angle": _orientation_contract_grid(offset=700.0),
    }
    if ancillary_overrides:
        ancillary.update(ancillary_overrides)

    if cube_layout == "yxb":
        stored_cube = cube_yxb
    elif cube_layout == "byx":
        stored_cube = np.moveaxis(cube_yxb, 2, 0)
    elif cube_layout == "ybx":
        stored_cube = np.moveaxis(cube_yxb, 2, 1)
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported cube layout: {cube_layout}")

    with h5py.File(path, "w") as h5_file:
        base_group = h5_file.create_group("DRONE")
        reflectance_group = base_group.create_group("Reflectance")
        reflectance_dataset = reflectance_group.create_dataset(
            "Reflectance_Data", data=stored_cube, dtype=np.float32
        )
        reflectance_dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)

        metadata_group = reflectance_group.create_group("Metadata")
        spectral_group = metadata_group.create_group("Spectral_Data")
        wavelength_ds = spectral_group.create_dataset("Wavelength", data=wavelengths)
        wavelength_ds.attrs["Units"] = "Nanometers"
        spectral_group.create_dataset("FWHM", data=fwhm)

        coordinate_group = metadata_group.create_group("Coordinate_System")
        coordinate_group.create_dataset(
            "Map_Info", data=np.array(map_info, dtype="S")
        )
        coordinate_group.create_dataset(
            "Coordinate_System_String",
            data=np.array("FAKE PROJECTION WKT", dtype="S"),
        )

        for dataset_name, values in ancillary.items():
            metadata_group.create_dataset(dataset_name, data=np.asarray(values, dtype=np.float32))

    expected = {"reflectance": cube_yxb}
    expected.update({name: np.asarray(values, dtype=np.float32) for name, values in ancillary.items()})
    return expected


def test_neon_cube_iter_chunks(tmp_path):
    fake_h5_path = tmp_path / "fake_neon.h5"
    _create_fake_neon_file(fake_h5_path)

    cube = NeonCube(h5_path=fake_h5_path)

    assert cube.lines == 20
    assert cube.columns == 20
    assert cube.bands == 5

    assert cube.data.shape == (20, 20, 5)
    assert cube.data.dtype == np.float32

    assert isinstance(cube.mask_no_data, np.ndarray)
    assert cube.mask_no_data.shape == (20, 20)

    assert cube.wavelengths.shape == (5,)
    assert cube.fwhm.shape == (5,)

    chunks = list(cube.iter_chunks(chunk_y=10, chunk_x=10))
    assert len(chunks) == 4
    for ys, ye, xs, xe, arr in chunks:
        assert arr.shape == (ye - ys, xe - xs, cube.bands)

    coverage = set()
    for ys, ye, xs, xe, arr in chunks:
        for yy in range(ys, ye):
            for xx in range(xs, xe):
                coverage.add((yy, xx))
    assert len(coverage) == 20 * 20

    header = cube.build_envi_header()

    assert header["samples"] == 20
    assert header["lines"] == 20
    assert header["bands"] == 5

    assert header["interleave"].lower() == "bsq"
    assert header["data type"] == 4
    assert header["byte order"] == 0

    assert "map info" in header
    assert "projection" in header
    assert "wavelength" in header
    assert "fwhm" in header
    assert "wavelength units" in header

    assert isinstance(header["map info"], (list, tuple))
    assert len(header["map info"]) >= 6
    assert isinstance(header["wavelength"], list)
    assert isinstance(header["fwhm"], list)
    assert len(header["wavelength"]) == cube.bands
    assert len(header["fwhm"]) == cube.bands
    assert all(isinstance(v, float) for v in header["wavelength"])
    assert all(isinstance(v, float) for v in header["fwhm"])
    assert header["wavelength units"].lower() == "nanometers"


def test_read_neon_cube_new_layout(tmp_path):
    fake_h5_path = tmp_path / "fake_neon.h5"
    _create_fake_neon_file(fake_h5_path)

    cube, wavelengths, meta = read_neon_cube(fake_h5_path)

    assert cube.shape == (20, 20, 5)
    assert wavelengths.shape == (5,)
    assert meta["bands"] == 5
    assert meta["lines"] == 20
    assert meta["wavelength_units"].lower() == "nanometers"
    assert meta["metadata_group_paths"]
    assert meta["layout"] == "reflectance_group"


def test_read_neon_cube_old_layout(tmp_path):
    fake_h5_path = tmp_path / "legacy_neon.h5"
    _create_fake_legacy_neon_file(fake_h5_path)

    cube, wavelengths, meta = read_neon_cube(fake_h5_path)

    assert cube.shape == (10, 10, 3)
    assert wavelengths.shape == (3,)
    assert meta["bands"] == 3
    assert meta["map_info"]
    assert meta["wavelength_units"].lower() == "nanometers"
    assert meta["metadata_group_paths"]
    assert meta["layout"] == "legacy_hdf5"


def test_read_neon_cube_pre_2021_new_layout(tmp_path):
    fake_h5_path = tmp_path / "NEON_D13_SITE_DP1_L001-1_20200720_directional_reflectance.h5"
    _create_fake_neon_file(fake_h5_path)

    cube, wavelengths, meta = read_neon_cube(fake_h5_path)

    assert cube.shape == (20, 20, 5)
    assert wavelengths.shape == (5,)
    assert meta["bands"] == 5
    assert meta["metadata_group_paths"]


def test_read_neon_cube_site_group_legacy_layout(tmp_path):
    fake_h5_path = tmp_path / "NEON_D13_NIWO_DP1_20200720_reflectance.h5"
    _create_fake_site_group_legacy_file(fake_h5_path)

    cube, wavelengths, meta = read_neon_cube(fake_h5_path)

    assert cube.shape == (20, 10, 5)
    assert wavelengths.shape == (5,)
    assert meta["bands"] == 5
    assert meta["layout"] == "legacy_site_group"
    assert meta["site"] == "NIWO"
    assert meta["metadata_group_paths"]
    assert meta["wavelength_units"].lower() == "nanometers"


def test_read_neon_cube_remains_strict_when_nodata_metadata_missing(tmp_path):
    fake_h5_path = tmp_path / "fake_neon_missing_nodata.h5"
    _create_fake_neon_file_missing_nodata(fake_h5_path)

    with pytest.raises(
        RuntimeError,
        match="Reflectance dataset missing a recognised no-data attribute",
    ):
        read_neon_cube(fake_h5_path)


def test_drone_hdf5_orientation_contract_preserves_reflectance_and_ancillary_alignment(
    tmp_path: Path,
) -> None:
    h5_path = tmp_path / "drone_orientation_contract.h5"
    expected = _create_fake_orientation_contract_file(h5_path)

    cube = NeonCube(h5_path=h5_path)

    expected_reflectance = expected["reflectance"]
    np.testing.assert_array_equal(cube.data, expected_reflectance)
    np.testing.assert_array_equal(cube.data[:, :, 0], _orientation_contract_grid())

    wrong_spatial_orientations = (
        expected_reflectance.transpose(1, 0, 2),
        expected_reflectance[::-1, :, :],
        expected_reflectance[:, ::-1, :],
    )
    for wrong in wrong_spatial_orientations:
        assert not np.array_equal(cube.data, wrong)

    ancillary_expectations = {
        "slope": expected["Slope"],
        "aspect": expected["Aspect"],
        "solar_zn": expected["Solar_Zenith_Angle"],
        "solar_az": expected["Solar_Azimuth_Angle"],
        "sensor_zn": expected["To_Sensor_Zenith_Angle"],
        "sensor_az": expected["To_Sensor_Azimuth_Angle"],
    }
    for name, values in ancillary_expectations.items():
        loaded = cube.get_ancillary(name, radians=False)
        np.testing.assert_array_equal(loaded, values)
        assert not np.array_equal(loaded, values.T)
        assert not np.array_equal(loaded, values[::-1, :])
        assert not np.array_equal(loaded, values[:, ::-1])


@pytest.mark.parametrize("cube_layout", ["yxb", "byx", "ybx"])
def test_orient_cube_normalises_supported_spectral_axis_positions(
    tmp_path: Path,
    cube_layout: str,
) -> None:
    h5_path = tmp_path / f"cube_{cube_layout}.h5"
    expected = _create_fake_orientation_contract_file(h5_path, cube_layout=cube_layout)

    raw_cube, wavelengths, _meta = read_neon_cube(h5_path)

    assert wavelengths.shape == (2,)
    np.testing.assert_array_equal(raw_cube, expected["reflectance"])

    wrong_spatial_orientations = (
        expected["reflectance"].transpose(1, 0, 2),
        expected["reflectance"][::-1, :, :],
        expected["reflectance"][:, ::-1, :],
    )
    for wrong in wrong_spatial_orientations:
        assert not np.array_equal(raw_cube, wrong)


def test_orient_cube_moves_only_the_spectral_axis() -> None:
    cube_yxb = np.stack(
        [_orientation_contract_grid(), _orientation_contract_grid(offset=100.0)],
        axis=2,
    )

    np.testing.assert_array_equal(_orient_cube(cube_yxb, 2), cube_yxb)
    np.testing.assert_array_equal(
        _orient_cube(np.moveaxis(cube_yxb, 2, 0), 2),
        cube_yxb,
    )
    np.testing.assert_array_equal(
        _orient_cube(np.moveaxis(cube_yxb, 2, 1), 2),
        cube_yxb,
    )

    assert not np.array_equal(_orient_cube(np.moveaxis(cube_yxb, 2, 0), 2), cube_yxb[::-1, :, :])
    assert not np.array_equal(_orient_cube(np.moveaxis(cube_yxb, 2, 1), 2), cube_yxb[:, ::-1, :])


def test_get_ancillary_reports_actionable_shape_mismatches(tmp_path: Path) -> None:
    h5_path = tmp_path / "drone_ancillary_mismatch.h5"
    _create_fake_orientation_contract_file(
        h5_path,
        ancillary_overrides={"Slope": np.arange(12, dtype=np.float32).reshape(4, 3)},
    )

    cube = NeonCube(h5_path=h5_path)

    with pytest.raises(
        ValueError,
        match=r"Ancillary 'slope' has shape \(4, 3\) which does not match the reflectance cube \(3, 4\)",
    ):
        cube.get_ancillary("slope", radians=False)
