"""Reference discovery cannot use spectral agreement or invent spatial support."""

import importlib
import sys
from pathlib import Path

from shapely.geometry import box, mapping

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
epochs = importlib.import_module("landsat_evergreen_epochs")
structural = importlib.import_module("landsat_structural_reference")
sys.path.remove(str(DIRECTORY))


def test_epochs_exclude_reference_year_wrong_season_and_wrong_location():
    def item(key, date, bounds=(-1, -1, 1, 1)):
        return dict(
            id=key, properties={"datetime": date}, geometry=mapping(box(*bounds))
        )

    metadata = dict(
        longitude=0,
        latitude=0,
        scene_datetime="2023-07-16T00:00:00Z",
        naip_datetime="2023-07-15T00:00:00Z",
    )
    choices = epochs.epoch_choices(
        metadata,
        [
            item("same-year", "2023-07-15T00:00:00Z"),
            item("winter", "2021-01-01T00:00:00Z"),
            item("elsewhere", "2021-07-16T00:00:00Z", (2, 2, 3, 3)),
            item("later", "2021-08-01T00:00:00Z"),
            item("nearest", "2021-07-17T00:00:00Z"),
        ],
    )
    assert [year for year, _ in choices] == [2021]
    assert [row[2] for row in choices[0][1]] == ["nearest", "later"]


def test_structural_item_selection_requires_coverage_and_is_stable():
    items = [
        dict(id=key, geometry=mapping(box(*bounds)))
        for key, bounds in [
            ("z", (-1, -1, 1, 1)),
            ("a", (-2, -2, 2, 2)),
            ("outside", (2, 2, 3, 3)),
        ]
    ]
    assert [x["id"] for x in structural.covering_items(items, 0, 0)] == ["a", "z"]


def test_region_with_no_alternate_epochs_writes_readable_empty_table(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(epochs, "OUTPUT", tmp_path)
    monkeypatch.setattr(epochs, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(epochs, "SEASONAL", tmp_path)
    monkeypatch.setattr(epochs, "PATCHES", {"test": []})
    (tmp_path / "test-aerial-catalogue.json").write_text('{"features": []}')
    epochs.run_region("test")
    assert (
        (tmp_path / "test-alternate-aerial-epochs.csv")
        .read_text()
        .startswith("epoch_id,status,")
    )


def test_first_returns_preserve_gaps_and_exclude_outside_points():
    import numpy as np

    sys.path.insert(0, str(DIRECTORY))
    try:
        cloud = importlib.import_module("landsat_evergreen_pointcloud")
    finally:
        sys.path.remove(str(DIRECTORY))
    grid = cloud.first_return_grid(
        np.array([0.2, 0.8, 1.2, -0.1, 3.0]),
        np.array([0.2, 0.8, 0.2, 0.2, 0.2]),
        np.array([8.0, 12.0, 0.0, 100.0, 100.0]),
        0,
        0,
        size=3,
    )
    assert grid[0, 0] == 12
    assert grid[0, 1] == 0
    assert np.isfinite(grid).sum() == 2
    assert np.isnan(grid[1, 0])


def test_cell_structural_fraction_uses_whole_area_not_only_observed_bins():
    import numpy as np

    sys.path.insert(0, str(DIRECTORY))
    try:
        cloud = importlib.import_module("landsat_evergreen_pointcloud")
    finally:
        sys.path.remove(str(DIRECTORY))
    grid = np.full((240, 240), np.nan)
    grid[105:120, 105:135] = 20
    score = next(
        s
        for s in cloud.cell_scores(grid)
        if s["offset_east_m"] == 0 and s["offset_north_m"] == 0
    )
    assert score["observed_fraction"] == 0.5
    assert score["above_5m_fraction"] == 0.5
    assert score["above_10m_fraction"] == 0.5


def test_newer_structural_failure_cannot_be_hidden_by_older_passing_project(
    tmp_path, monkeypatch
):
    import json
    import numpy as np

    sys.path.insert(0, str(DIRECTORY))
    try:
        shortlist = importlib.import_module("landsat_evergreen_shortlist")
    finally:
        sys.path.remove(str(DIRECTORY))
    monkeypatch.setattr(shortlist, "DEST", tmp_path)
    monkeypatch.setattr(shortlist, "CACHE", tmp_path)
    key = "r2-cascades-evergreen-001"
    patch = dict(
        easting=500000,
        northing=5000000,
        landsat_epsg=32610,
        landsat_row=100,
        landsat_col=100,
        scene_datetime="2023-07-16T00:00:00Z",
        naip_datetime="2023-07-15T00:00:00Z",
        naip_id="aerial",
    )
    (tmp_path / f"{key}.json").write_text(json.dumps(patch))
    for project, year, height in [("USGS_old", 2016, 20.0), ("WA_new", 2018, 0.0)]:
        path = tmp_path / f"{key}-{project}.npy"
        np.save(path, np.full((240, 240), height))
        path.with_suffix(".json").write_text(
            json.dumps(
                dict(
                    array_sha256=shortlist.sha(path),
                    identity={"project": project},
                    source_intervals=[{"end_datetime": f"{year}-12-31T00:00:00Z"}],
                )
            )
        )
    assert shortlist.assemble().empty
