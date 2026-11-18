"""Publication summaries preserve footprint weighting and evidence scope."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PATH = (
    Path(__file__).resolve().parents[1]
    / "examples/publication_figures/landsat_pft_panel.py"
)
SPEC = importlib.util.spec_from_file_location("landsat_pft_panel", PATH)
panel = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = panel
SPEC.loader.exec_module(panel)


def test_ribbons_use_per_spectrum_normalization_and_preserve_missing_swir():
    # Unequal brightness must not change footprint weights in the quantiles.
    source = pd.DataFrame(
        {
            panel.LABEL: ["H"] * 3,
            "B1": [1, 20, 3],
            "B2": [1, 10, 1],
            "B3": [1, 10, 1],
            "B4": [1, 10, 1],
            "B5": [1, 10, 1],
        }
    )
    stats = panel.summarize_spectra({"drone": source}, ["H"])["drone"]
    normalized = np.array([1 / 5, 2 / 6, 3 / 7])
    assert stats.count["H"] == 3
    assert np.isclose(stats.median.loc["H", "B1"], np.median(normalized))
    assert np.isclose(stats.q25.loc["H", "B1"], np.quantile(normalized, 0.25))
    assert np.isclose(stats.q75.loc["H", "B1"], np.quantile(normalized, 0.75))
    for frame in (stats.median, stats.q25, stats.q75):
        assert frame.loc["H", ["B6", "B7"]].isna().all()


def test_gap_strips_keep_all_three_pairs_and_unavailable_bands():
    frames = {}
    for index, sensor in enumerate(panel.SENSORS):
        bands = panel.BANDS if index < 2 else panel.SHARED_BANDS
        frame = pd.DataFrame(
            {band: [1.0 + (index if band == "B5" else 0)] for band in bands}
        )
        frame[panel.LABEL] = "H"
        frames[sensor] = frame
    gaps = panel.band_gaps(panel.summarize_spectra(frames, ["H"]))
    assert gaps.shape == (1, 3, 7)
    assert np.isnan(gaps[0, :2, 5:]).all()
    assert np.isfinite(gaps[0, 2]).all()
    assert panel.CATEGORIES[-2:] == ["Woody shrub", "Non-vegetated & dead"]


def test_landsat_table_uses_primary_matched_test_and_never_fills_missing_tests(
    tmp_path,
):
    path = tmp_path / "tests.csv"
    pd.DataFrame(
        [
            dict(
                threshold=0.90,
                shift_m=0,
                a="Herbaceous",
                b="Non-vegetated & dead",
                status="exploratory_photo_labels",
                n_a=4,
                n_b=2,
                p_npc_holm=0.03,
            ),
            dict(
                threshold=0.95,
                shift_m=0,
                a="Herbaceous",
                b="Non-vegetated & dead",
                status="exploratory_photo_labels",
                n_a=1,
                n_b=1,
                p_npc_holm=1.0,
            ),
            dict(
                threshold=0.95,
                shift_m=0,
                a="Deciduous",
                b="Evergreen",
                status="no_matched_photo_supported_cohort",
                n_a=0,
                n_b=0,
                p_npc_holm=np.nan,
            ),
        ]
    ).to_csv(path, index=False)
    evidence = panel.load_landsat_evidence(panel.CATEGORIES, path)
    assert evidence["Herbaceous"] == evidence["Non-vegetated & dead"] == "n=1; p=1.00†"
    assert (
        evidence["Deciduous"]
        == evidence["Evergreen"]
        == evidence["Woody shrub"]
        == "No matched reference"
    )
