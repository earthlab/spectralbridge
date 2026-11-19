"""HLS has distinct QA, scale, grid and interpolation-support contracts."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely import box

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
hls = importlib.import_module("landsat_hls_reference_rebuild")
sys.path.remove(str(DIRECTORY))


def test_hls_fmask_is_not_landsat_collection2_qa():
    clear, aerosol = hls.fmask_clear([0, 64, 128, 192, 1, 2, 4, 8, 16, 32, 255])
    assert clear.tolist() == [
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert aerosol[:4].tolist() == [0, 1, 2, 3]


def test_hls_scale_preserves_negative_reflectance_and_rejects_own_fill():
    values = hls.scale_hls(np.array([-9999, -1000, 0, 1000, 10000]))
    assert np.isnan(values[0])
    np.testing.assert_allclose(values[1:], [-0.1, 0, 0.1, 1])


def test_resampling_source_support_uses_four_by_four_native_pixels():
    anchor = dict(easting=0, northing=0)
    support = hls.source_kernel(15, 15, anchor)
    assert support.bounds == (-45, -45, 75, 75)
    assert support.area == 16 * 900
    # Nominal new-grid purity can be perfect while outside source support is unknown.
    nominal = box(0, 0, 30, 30)
    assert hls.photo_fraction(nominal, nominal) == 1
    assert hls.photo_fraction(nominal, support) == 1 / 16


def test_structural_support_counts_unobserved_outside_context_in_denominator():
    grid = np.full((240, 240), 20.0)
    anchor = dict(easting=0, northing=0)
    assert hls.structural_fraction(grid, box(-15, -15, 15, 15), anchor) == (1.0, 1.0)
    assert hls.structural_fraction(grid, box(105, -15, 135, 15), anchor) == (0.5, 0.5)
    grid[105:135, 105:135] = np.nan
    assert hls.structural_fraction(grid, box(-15, -15, 15, 15), anchor) == (0.0, 0.0)


def test_unaligned_structural_grid_requires_exact_area_handling():
    with pytest.raises(ValueError, match="exact area"):
        hls.structural_fraction(
            np.ones((240, 240)), box(0.2, 0.2, 30.2, 30.2), dict(easting=0, northing=0)
        )


def test_modified_frozen_reference_geometries_fail_before_reading_shapes(
    tmp_path, monkeypatch
):
    import json

    monkeypatch.setattr(hls, "REFERENCES", tmp_path)
    (tmp_path / "reviewed_patch_policy.json").write_text('{"cases": []}')
    (tmp_path / "photo_reference_annotations.gpkg").write_bytes(b"changed geometry")
    (tmp_path / "annotation_manifest.json").write_text(
        json.dumps(
            dict(
                policy_sha256=hls.sha(tmp_path / "reviewed_patch_policy.json"),
                geometry_sha256="stale",
            )
        )
    )
    with pytest.raises(ValueError, match="Frozen annotation"):
        hls.cases()


def test_empty_region_still_writes_a_completed_stage_table(tmp_path, monkeypatch):
    import pandas as pd

    monkeypatch.setattr(hls, "OUTPUT", tmp_path)
    monkeypatch.setattr(
        hls,
        "reference_cells",
        lambda region: (pd.DataFrame(columns=["candidate_id", "aerial_year"]), {}),
    )
    hls.extract("cascades")
    saved = pd.read_csv(tmp_path / "cascades-selected_observations.csv")
    assert saved.empty and "all_bands_finite" in saved
