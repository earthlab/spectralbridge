"""New patch proposals remain hypotheses and preserve native spatial identities."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
SPEC = importlib.util.spec_from_file_location(
    "landsat_spatial_expansion", DIRECTORY / "landsat_spatial_expansion.py"
)
expansion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(expansion)
sys.path.remove(str(DIRECTORY))


def test_locator_hypotheses_do_not_confuse_aspen_conifers_and_chaparral():
    world = np.array([[10, 10, 10, 30, 60]])
    gap = np.array([[148, 141, 296, 148, 141]])
    masks = expansion.locator_masks(world, gap)
    expected = {
        "Deciduous": 0,
        "Evergreen": 1,
        "Woody shrub": 2,
        "Herbaceous": 3,
        "Non-vegetated & dead": 4,
    }
    for category, index in expected.items():
        assert np.flatnonzero(masks[category]).tolist() == [index]


def test_snapping_preserves_reference_grid_and_row_orientation():
    anchor = SimpleNamespace(
        easting=650000.0,
        northing=4500000.0,
        landsat_row=100,
        landsat_col=200,
        landsat_epsg=32613,
    )
    result = expansion.snap_center(650047.0, 4499951.0, anchor)
    assert result == dict(
        easting=650060.0,
        northing=4499940.0,
        landsat_col=202,
        landsat_row=102,
        landsat_epsg=32613,
    )
    assert (
        expansion.snap_center(result["easting"], result["northing"], anchor) == result
    )


def test_expanded_locator_count_and_spacing_are_explicit():
    mask = np.ones((160, 160), bool)
    results = list(expansion.regional.interior_centers(mask, count=12, spacing_m=300))
    assert len(results) == 12
    coordinates = np.array([(row, col) for row, col, _ in results]) * 20
    distances = np.linalg.norm(coordinates[:, None] - coordinates[None, :], axis=2)
    distances[np.eye(len(coordinates), dtype=bool)] = np.inf
    assert distances.min() >= 300


def test_annotation_handles_larger_context_and_flags_darkness_not_yellow_leaves():
    sys.path.insert(0, str(DIRECTORY))
    try:
        import landsat_photo_annotation as annotation
    finally:
        sys.path.remove(str(DIRECTORY))
    from shapely import box

    image = np.zeros((3, 2, 2), float)
    image[:] = np.array([200, 180, 20])[:, None, None]
    image[:, 0, 0] = 10
    case = dict(
        patch=[[-120, -120], [120, -120], [120, 120], [-120, 120]],
        dark_unknown_max_ceiling=30,
    )
    classes = annotation.image_classes(
        case, image, 2023, domain=box(-120, -120, 120, 120)
    )
    assert classes["uncertain"].area == 14400
    assert classes["target"].area == 43200
    assert sum(part.area for part in classes.values()) == 57600


def test_overlapping_contexts_merge_transitively_before_validation():
    import pandas as pd

    frame = pd.DataFrame(
        [
            dict(
                context_patch_id="a",
                landsat_epsg=32613,
                patch_easting=0,
                patch_northing=0,
            ),
            dict(
                context_patch_id="b",
                landsat_epsg=32613,
                patch_easting=220,
                patch_northing=0,
            ),
            dict(
                context_patch_id="c",
                landsat_epsg=32613,
                patch_easting=440,
                patch_northing=0,
            ),
            dict(
                context_patch_id="d",
                landsat_epsg=32613,
                patch_easting=1000,
                patch_northing=0,
            ),
            dict(
                context_patch_id="e",
                landsat_epsg=32612,
                patch_easting=0,
                patch_northing=0,
            ),
        ]
    )
    groups = expansion.patch_groups(frame)
    assert groups["a"] == groups["b"] == groups["c"]
    assert groups["d"] != groups["a"] and groups["e"] != groups["a"]


def test_changed_photo_policy_cannot_reuse_old_cover_measurements(
    tmp_path, monkeypatch
):
    import json
    import pytest

    monkeypatch.setattr(expansion, "OUTPUT", tmp_path)
    (tmp_path / "reviewed_patch_policy.json").write_text("{}")
    (tmp_path / "annotation_manifest.json").write_text(
        json.dumps(dict(policy_sha256="stale", fractions_sha256="stale"))
    )
    with pytest.raises(ValueError, match="annotation stage"):
        expansion.reference_cohort()
