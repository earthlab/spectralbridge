"""Offline scene selection and one-flight orchestration contracts."""

from types import SimpleNamespace
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from spectralbridge import landsat_flight_validation as v
from spectralbridge.landsat_agreement import ReferenceGrid, OLI_CENTERS, OLI_CHANNELS


def item(name="oli", date="2021-09-16T12:00:00Z", platform="landsat-8"):
    p = {
        "datetime": date,
        "platform": platform,
        "landsat:correction": "L2SP",
        "eo:cloud_cover": 1,
        "landsat:collection_category": "T1",
    }
    assets = {
        k: SimpleNamespace(
            href=f"https://example.org/{name}_SR_B{i}.TIF", extra_fields={}
        )
        for i, k in enumerate([*OLI_CHANNELS, "qa_pixel", "qa_radsat"], 1)
    }
    return SimpleNamespace(
        id=name,
        properties=p,
        collection_id="landsat-c2-l2",
        assets=assets,
        geometry=None,
        to_dict=lambda **kw: {"id": name},
    )


def flight(tmp_path):
    a = np.arange(900, dtype=float).reshape(30, 30) / 10000 + 0.1
    paths = []
    for variant in ["corrected", "undarkened", "adjusted"]:
        path = tmp_path / (variant + ".tif")
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=30,
            height=30,
            count=7,
            dtype="float32",
            crs="EPSG:32613",
            transform=from_origin(500000, 4400000, 1, 1),
        ) as dst:
            dst.write(np.stack([a + i * 0.01 for i in range(7)]).astype("float32"))
            dst.update_tags(
                ns="ENVI",
                wavelength=",".join(map(str, OLI_CENTERS)),
                reflectance_scale_factor="1",
            )
        paths.append(str(path))
    return v.FlightValidationInput(
        "flight",
        "TEST",
        "2021-09-15T12:00:00Z",
        *paths,
        1,
        "fixture explicit UTC",
        timezone_verified=True,
    )


def test_candidates_keep_incompatible_same_day_and_signed_time():
    rows = v.candidate_records(
        [item(), item("etm", "2021-09-15T12:00:00Z", "landsat-7")],
        "2021-09-15T12:00:00Z",
    )
    assert rows.iloc[0].delta_time_hours == 24
    assert rows.iloc[0].within_1_days
    assert rows.iloc[1].same_calendar_day
    assert rows.iloc[1].status == "incompatible_sensor_for_seven_band_OLI"


def test_ranking_prioritizes_time_before_cloud_free_area():
    rows = v.candidate_records(
        [item("near"), item("far", "2021-09-18T12:00:00Z")], "2021-09-15T12:00:00Z"
    )
    rows["status"] = "QA_evaluated"
    rows["usable_pixels"] = [100, 10000]
    rows["clear_overlap_fraction"] = [0.6, 1]
    rows["spatial_coverage_fraction"] = 1
    assert v.rank_scene_candidates(rows, 100).iloc[0].item_id == "near"
    assert v.rank_scene_candidates(rows, 20000).empty
    assert v.rank_scene_candidates(
        v.candidate_records([item(platform="landsat-7")], "2021-09-15T12:00:00Z")
    ).empty


def test_no_scene_records_explicit_status(tmp_path):
    result = v.compare_flight_to_real_landsat(
        flight(tmp_path),
        tmp_path / "out",
        items=[],
        config=v.FlightValidationConfig(bootstraps=19),
    )
    assert result["status"] == "no_scene"
    assert (
        json.loads((tmp_path / "out/status.json").read_text())["status"] == "no_scene"
    )


def test_band_metadata_gate(tmp_path):
    f = flight(tmp_path)
    with rasterio.open(f.adjusted_raster, "r+") as dst:
        dst.update_tags(ns="ENVI", wavelength="band_01,band_02")
    with pytest.raises(ValueError, match="physical OLI"):
        v._validate_sources(f)


def test_cloud_only_scene_not_a_translation_failure(tmp_path, monkeypatch):
    f = flight(tmp_path)
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 10, 10)), 3, 3
    )
    qa = {
        "qa_pixel": np.full((3, 3), 1 << 3, np.uint16),
        "qa_radsat": np.zeros((3, 3), np.uint16),
    }
    monkeypatch.setattr(v, "load_scene_qa", lambda *a: (qa, grid))
    result = v.compare_flight_to_real_landsat(
        f,
        tmp_path / "out",
        items=[item()],
        config=v.FlightValidationConfig(minimum_pixels=3, bootstraps=19),
    )
    assert result["status"] == "no_eligible_scene"
    rows = pd.read_csv(tmp_path / "out/scene_candidates.csv")
    assert rows.iloc[0].usable_pixels == 0
    assert rows.iloc[0].status == "insufficient_QA_overlap"


def test_complete_mocked_transport_and_checksum_restart(tmp_path, monkeypatch):
    f = flight(tmp_path)
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 10, 10)), 3, 3
    )
    qa = {
        "qa_pixel": np.zeros((3, 3), np.uint16),
        "qa_radsat": np.zeros((3, 3), np.uint16),
        "cloud_distance_lower_bound_m": np.full((3, 3), 300.0),
    }
    monkeypatch.setattr(v, "load_scene_qa", lambda *a: (qa, grid))
    means = v.aggregate_to_landsat_grid({"u": f.undarkened_raster}, grid)["means"]["u"]
    monkeypatch.setattr(
        v,
        "load_scene_surface_reflectance",
        lambda *a: (means + 0.001, Path(f.corrected_raster)),
    )
    # Plot rendering is separately exercised on the real pilot, not necessary for a transport unit test.
    from spectralbridge import landsat_flight_report

    monkeypatch.setattr(
        landsat_flight_report, "build_flight_validation_figures", lambda *a: None
    )
    root = tmp_path / "out"
    config = v.FlightValidationConfig(
        minimum_pixels=3, bootstraps=19, spatial_block_pixels=1
    )
    result = v.compare_flight_to_real_landsat(f, root, items=[item()], config=config)
    assert result["status"] == "complete_single_flight"
    pixels = pd.read_parquet(root / "pixel_metrics.parquet")
    assert len(pixels) == 9
    metrics = pd.read_csv(root / "band_metrics.csv")
    np.testing.assert_allclose(metrics.mean_bias, -0.001, atol=1e-8)
    before = (root / "band_metrics.csv").stat().st_mtime_ns
    assert (
        v.compare_flight_to_real_landsat(f, root, items=[item()], config=config)
        == result
    )
    assert before == (root / "band_metrics.csv").stat().st_mtime_ns


@pytest.mark.skipif(
    not os.getenv("SPECTRALBRIDGE_REAL_LANDSAT_WINDOW"),
    reason="optional cached real Landsat window",
)
def test_optional_real_landsat_window():
    with rasterio.open(os.environ["SPECTRALBRIDGE_REAL_LANDSAT_WINDOW"]) as src:
        assert src.count == 7 and src.crs and src.res == (30, 30)
        assert src.tags()["reflectance_units"] == "unitless"
        values = src.read(masked=True)
        assert values.count() > 0
        assert np.isfinite(values.compressed()).all()
