"""Contracts for independent-map discovery before Landsat PFT testing."""

import importlib.util
from pathlib import Path

import numpy as np
from shapely import box
from shapely.geometry import mapping

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "examples/publication_figures/landsat_regional_candidates.py"
)
SPEC = importlib.util.spec_from_file_location("landsat_regional_candidates", SCRIPT)
candidates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidates)


def test_empty_map_proposes_no_candidates():
    assert list(candidates.interior_centers(np.zeros((100, 100), dtype=bool))) == []


def test_map_candidates_have_interior_support_and_are_spaced():
    mask = np.ones((160, 160), dtype=bool)
    centers = list(candidates.interior_centers(mask))
    assert len(centers) == 3
    for row, col, distance in centers:
        assert distance >= candidates.MIN_MAP_INTERIOR_METERS
        assert min(row + 1, col + 1, 160 - row, 160 - col) * 20 == distance
    for first, second in zip(centers, centers[1:]):
        assert np.hypot(first[0] - second[0], first[1] - second[1]) * 20 >= 1000


def test_narrow_island_is_rejected():
    mask = np.zeros((80, 80), dtype=bool)
    mask[40, 10:70] = True
    assert list(candidates.interior_centers(mask)) == []


def test_scene_ranking_requires_footprint_and_prioritizes_time_then_cloud():
    def scene(name, day, cloud, footprint):
        return dict(
            id=name,
            geometry=mapping(footprint),
            properties={
                "datetime": f"2023-08-{day:02d}T12:00:00Z",
                "eo:cloud_cover": cloud,
            },
        )

    point = candidates.Point(-105.5, 40)
    available = box(-106, 39, -105, 41)
    scenes = [
        scene("outside", 14, 0, box(-120, 42, -119, 43)),
        scene("cloudy_same_day", 14, 20, available),
        scene("clear_same_day", 14, 2, available),
        scene("clear_later", 16, 0, available),
    ]
    assert [item["id"] for item in candidates.scene_order(point, scenes)] == [
        "clear_same_day",
        "cloudy_same_day",
        "clear_later",
    ]


def test_truncated_catalogue_is_subdivided_and_deduplicated():
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.bounds = []

        def post(self, url, *, json, timeout):
            bounds = json["bbox"]
            self.bounds.append(bounds)
            truncated = bounds[2] - bounds[0] > 1
            return Response(
                dict(
                    features=[dict(id=str(bounds)), dict(id="shared_border_tile")],
                    links=[dict(rel="next")] if truncated else [],
                )
            )

    session = Session()
    result = candidates.fetch_catalogue(
        session, {"bbox": [0, 0, 2, 2], "collections": ["naip"]}
    )
    assert len(session.bounds) == 5
    assert len(result["features"]) == 5
    assert not result["links"]


def test_external_map_does_not_assign_researcher_pft(monkeypatch):
    mask = np.full((160, 160), 10, dtype=np.uint8)
    transform = candidates.from_origin(450000, 4430000, 20, 20)
    monkeypatch.setattr(candidates, "map_grid", lambda region: (mask, transform))
    result = candidates.discover("front_range")
    assert len(result) == 3
    assert result.map_label.eq("Tree cover").all()
    assert result.researcher_category.isna().all()
    assert result.reference_review.eq("pending").all()


def test_map_assets_use_the_correct_source_key_and_cache(monkeypatch, tmp_path):
    calls = []

    class Raster:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Warped(Raster):
        def __init__(self, raster, **kwargs):
            self.shape = kwargs["height"], kwargs["width"]

        def read(self, band):
            return np.full(self.shape, 148, dtype=np.uint16)

    def open_asset(item, key):
        calls.append(key)
        return Raster()

    monkeypatch.setattr(candidates, "CACHE", tmp_path)
    monkeypatch.setattr(
        candidates, "REGIONS", {"front_range": [-105.001, 39.999, -104.999, 40.001]}
    )
    monkeypatch.setattr(candidates, "items", lambda *args: [{"id": "test_map"}])
    monkeypatch.setattr(candidates, "open_asset", open_asset)
    monkeypatch.setattr(candidates, "WarpedVRT", Warped)
    forest, _ = candidates.map_grid("front_range", "gap")
    worldcover, _ = candidates.map_grid("front_range")
    assert forest.max() == worldcover.max() == 148
    assert calls == ["data", "map"]
    candidates.map_grid("front_range", "gap")
    assert calls == ["data", "map"]
