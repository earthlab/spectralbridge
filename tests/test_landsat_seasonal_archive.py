"""Season and spatial contracts for repeated Landsat observations."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from affine import Affine
from rasterio.crs import CRS
from rasterio.transform import rowcol

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
SPEC = importlib.util.spec_from_file_location(
    "landsat_seasonal_archive", DIRECTORY / "landsat_seasonal_archive.py"
)
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)
sys.path.remove(str(DIRECTORY))


def test_calendar_season_stays_fixed_across_leap_years():
    for year in [2020, 2021, 2024, 2025]:
        start, end, anchor = archive.season_window("2023-08-20", year)
        assert anchor.strftime("%m-%d") == "08-20"
        assert (anchor - start).days == (end - anchor).days == 21


def test_season_can_cross_calendar_boundary():
    start, end, anchor = archive.season_window("2023-01-05", 2024, 10)
    assert start == pd.Timestamp("2023-12-26", tz="UTC")
    assert end == pd.Timestamp("2024-01-15", tz="UTC")
    assert anchor.year == 2024


def test_same_location_requires_exact_ground_footprint():
    class Grid:
        crs = CRS.from_epsg(32613)
        width = height = 100
        transform = Affine(30, 0, 450000, 0, -30, 4431000)

        def index(self, x, y):
            return rowcol(self.transform, x, y)

    reference = SimpleNamespace(landsat_epsg=32613, easting=450015, northing=4430985)
    grid = Grid()
    assert archive.grid_match(grid, reference) == (True, 0, 0)
    grid.transform = Affine(30, 0, 450005, 0, -30, 4431000)
    assert not archive.grid_match(grid, reference)[0]
    grid.crs = CRS.from_epsg(32612)
    assert not archive.grid_match(grid, reference)[0]


def test_quality_ranking_uses_aerosol_and_season_without_response_bands():
    candidates = pd.DataFrame(
        {
            "scene_id": ["close_fallback", "far_preferred", "close_preferred"],
            "preferred_aerosol": [False, True, True],
            "season_offset_days": [0, 10, 2],
            "aerosol_level": [0, 1, 1],
            "B5": [np.nan, 1000, -1000],
        }
    )
    result = archive.quality_order(candidates)
    assert result.scene_id.tolist() == [
        "close_preferred",
        "far_preferred",
        "close_fallback",
    ]
    candidates.B5 = [0, 0, 0]
    assert (
        archive.quality_order(candidates).scene_id.tolist() == result.scene_id.tolist()
    )


def test_archive_keeps_years_linked_to_the_same_footprint(monkeypatch, tmp_path):
    output = tmp_path / "observations"
    output.mkdir()
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "regional_candidate_dataset.csv").write_text(
        "candidate_id\nfixed_cell\n"
    )
    monkeypatch.setattr(archive, "OUTPUT", output)
    monkeypatch.setattr(archive, "REFERENCE", reference)
    monkeypatch.setattr(archive, "REGIONS", {"test_region": []})
    for year in [2020, 2021]:
        pd.DataFrame(
            [
                dict(
                    candidate_id="fixed_cell",
                    region="test_region",
                    year=year,
                    observation_status="selected",
                    preferred_aerosol=True,
                    cover_stability_status="pending",
                )
            ]
        ).to_csv(output / f"test_region-{year}-observations.csv", index=False)
    pd.DataFrame(
        [dict(candidate_id="fixed_cell", temporal_cover_flag="review_required")]
    ).to_csv(
        output / "cover_review_notes.csv",
        index=False,
    )
    archive.finalize([2020, 2021], 21)
    result = pd.read_csv(output / "seasonal_observations.csv")
    assert len(result) == 2
    assert result.candidate_id.nunique() == 1
    assert result.year.tolist() == [2020, 2021]
    assert result.cover_stability_status.eq("review_required").all()
