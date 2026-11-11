"""Metashape preamble, repeated band positions and explicit CRS interpretation."""

import hashlib

import numpy as np
import pytest

from spectralbridge.drone_view_geometry import read_metashape_camera_locations


def table(path, *, epsg=26913, count=2, duplicate=False, bad_rotation=False):
    header = "PhotoID,X,Y,Z,Omega,Phi,Kappa," + ",".join(
        f"r{i}{j}" for i in range(1, 4) for j in range(1, 4)
    )
    rotation = np.eye(3).reshape(-1)
    if bad_rotation:
        rotation[0] = 2
    suffix = ",".join(map(str, [450000, 4430000, 2800, 0, 0, 0, *rotation]))
    path.write_text(
        f"CRS,{epsg}\n# Cameras ({count})\n# {header}\nIMG_0001_1,{suffix}\n"
        + ("IMG_0001_1" if duplicate else "IMG_0001_2")
        + ","
        + suffix
        + "\n"
    )
    return path


def test_band_records_are_distinct_and_source_is_immutable(tmp_path):
    path = table(tmp_path / "AOP-GOLDHILL-8-14-2023-camera-locations.csv")
    original = path.read_bytes()
    photos, meta = read_metashape_camera_locations(path)
    assert len(photos) == 2 and meta["distinct_positions"] == 1
    assert meta["adopted_crs"] == "EPSG:26913" and not meta["crs_overridden"]
    assert meta["source_sha256"] == hashlib.sha256(original).hexdigest()
    assert path.read_bytes() == original and meta["actual_contributors"] == "UNVERIFIED"


def test_crs_discrepancy_never_auto_relabels(tmp_path):
    path = table(tmp_path / "camera.csv", epsg=5070)
    _, declared = read_metashape_camera_locations(path)
    assert declared["adopted_crs"] == "EPSG:5070"
    with pytest.raises(ValueError, match="evidence"):
        read_metashape_camera_locations(path, crs_override=26913)
    _, override = read_metashape_camera_locations(
        path,
        crs_override=26913,
        crs_override_provenance="Synthetic independent project report fixture",
    )
    assert (
        override["declared_crs"] == "EPSG:5070"
        and override["adopted_crs"] == "EPSG:26913"
    )
    assert override["crs_overridden"] and path.read_text().startswith("CRS,5070")


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"count": 3}, "count"),
        ({"duplicate": True}, "unique"),
        ({"bad_rotation": True}, "orthogonal"),
        ({"epsg": 4326}, "metre"),
    ],
)
def test_invalid_camera_contract_is_actionable(tmp_path, kwargs, reason):
    with pytest.raises(ValueError, match=reason):
        read_metashape_camera_locations(table(tmp_path / "camera.csv", **kwargs))
