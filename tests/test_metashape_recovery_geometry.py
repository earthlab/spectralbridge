"""Independent axis and ray checks for the isolated recovery experiment."""

import importlib.util
from pathlib import Path
import numpy as np
import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "provenance/metashape-recovery/2026-11-05/geometry.py"
)
spec = importlib.util.spec_from_file_location("metashape_recovery_geometry", PATH)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_true_north_clockwise_and_surface_to_sensor():
    zen, az = g.viewing_angles(
        [[0, 1, 1], [1, 0, 1], [0, -1, 1], [-1, 0, 1]], [0, 0, 0], np.eye(3)
    )
    np.testing.assert_allclose(zen, 45)
    np.testing.assert_allclose(az, [0, 90, 180, 270])


def test_ecef_frame_and_ray_scale_do_not_change_angles():
    R = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
    z, a = g.viewing_angles([10, 1, 0], [0, 0, 0], R)
    np.testing.assert_allclose(z, np.rad2deg(np.arctan(0.1)))
    assert a == pytest.approx(90)
    distance, forward = g.point_ray_distance([0, 0, 10], [0, 0, 0], [0, 0, 3])
    assert distance == 0 and forward


def test_wrong_frames_backwards_and_degenerate_rays_fail():
    with pytest.raises(ValueError, match="Orthonormal"):
        g.viewing_angles([0, 0, 10], [0, 0, 0], np.eye(3) * 2)
    with pytest.raises(ValueError, match="above"):
        g.viewing_angles([0, 0, -1], [0, 0, 0], np.eye(3))
    with pytest.raises(ValueError, match="nonzero"):
        g.normalize([0, 0, 0])


def test_mixed_project_and_relative_height_assets_fail_before_rays():
    camera = dict(
        project_fingerprint="synthetic-alignment-A",
        chunk_key=0,
        crs="EPSG:26913",
        coordinate_frame="project_absolute",
    )
    assert g.require_asset_binding(camera, dict(camera)) == camera
    other = dict(camera, project_fingerprint="synthetic-alignment-B")
    with pytest.raises(ValueError, match="project_fingerprint"):
        g.require_asset_binding(camera, other)
    with pytest.raises(ValueError, match="coordinate_frame"):
        g.require_asset_binding(
            camera, dict(camera, coordinate_frame="relative_height")
        )
    with pytest.raises(ValueError, match="Missing source binding"):
        g.require_asset_binding({}, camera)


def test_retained_mosaic_native_directory_is_not_the_first_thumbnail(tmp_path):
    import rasterio
    from rasterio.transform import from_origin

    path = tmp_path / "retained.tif"
    for size, value, append in [(2, 7, False), (8, 123, True)]:
        options = dict(
            driver="GTiff",
            width=size,
            height=size,
            count=10,
            dtype="uint16",
            crs="EPSG:26913",
            transform=from_origin(450000, 4400000, 1, 1),
        )
        if append:
            options["APPEND_SUBDATASET"] = "YES"
        with rasterio.open(path, "w", **options) as dst:
            dst.write(np.full((10, size, size), value, np.uint16))
    with rasterio.open(path) as base:
        assert base.shape == (2, 2)
    with g.open_native_orthomosaic_tile(path, expected_shape=(8, 8)) as native:
        assert native.shape == (8, 8)
        assert np.all(native.read() == 123)
    with pytest.raises(ValueError, match="declared tile grid"):
        g.open_native_orthomosaic_tile(path, expected_shape=(16, 16))


def test_identical_psx_pointers_cannot_identify_different_alignments(tmp_path):
    projects = []
    for name, value in [("a", b"estimated pose A"), ("b", b"estimated pose B")]:
        folder = tmp_path / name
        folder.mkdir()
        p = folder / "flight.psx"
        p.write_bytes(b"same pointer")
        data = folder / "flight.files"
        (data / "0" / "0").mkdir(parents=True)
        (data / "project.zip").write_bytes(b"project descriptor")
        (data / "0" / "chunk.zip").write_bytes(value)
        (data / "0" / "0" / "frame.zip").write_bytes(b"frame descriptor")
        projects.append(p)
    assert projects[0].read_bytes() == projects[1].read_bytes()
    assert g.project_descriptor_fingerprint(
        projects[0]
    ) != g.project_descriptor_fingerprint(projects[1])
