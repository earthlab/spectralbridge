"""Geometric lower bounds and exact reference permutations for photo labels."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
SPEC = importlib.util.spec_from_file_location(
    "landsat_photo_annotation", DIRECTORY / "landsat_photo_annotation.py"
)
annotation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(annotation)
sys.path.remove(str(DIRECTORY))


def test_unknown_pixels_reduce_the_lower_bound_and_preserve_full_area():
    image = np.full((3, 2, 2), 200.0)
    image[:, :, 0] = 0
    case = dict(
        patch=[[-40, -40], [40, -40], [40, 40], [-40, 40]], dark_unknown_ceiling=100
    )
    classes = annotation.image_classes(case, image, 2023)
    fractions = annotation.fractions(classes)
    assert fractions == dict(target=0.5, other=0.0, uncertain=0.5)
    assert annotation.shifted_lower_bound(classes, 3) == 0.4
    assert sum(part.area for part in classes.values()) == 6400


def test_known_other_cover_has_exclusive_area_and_can_vary_by_year():
    case = dict(
        patch=[[-40, -40], [40, -40], [40, 40], [-40, 40]],
        unknown_polygons=[[[-15, -15], [-10, -15], [-10, 15], [-15, 15]]],
        other_polygons=[[[-15, -15], [-12, -15], [-12, 15], [-15, 15]]],
        year_other_polygons={"2024": [[[-12, -15], [0, -15], [0, 15], [-12, 15]]]},
    )
    image = np.full((3, 2, 2), 150.0)
    first = annotation.fractions(annotation.image_classes(case, image, 2022))
    later = annotation.fractions(annotation.image_classes(case, image, 2024))
    assert np.isclose(first["target"], 750 / 900)
    assert np.isclose(first["uncertain"], 60 / 900)
    assert np.isclose(first["other"], 90 / 900)
    assert later == dict(target=0.5, other=0.5, uncertain=0.0)


def test_unresolved_interpretation_is_unknown_rather_than_target_absence():
    classes = annotation.image_classes(
        dict(unresolved_years=[2023]), np.zeros((3, 2, 2)), 2023
    )
    assert annotation.fractions(classes) == dict(target=0.0, other=0.0, uncertain=1.0)


def test_exact_small_sample_npc_and_observed_statistics_match_package():
    from spectralbridge.pft_method_audit import AuditConfig, method_statistics

    values = np.array([[1.0, 2.0], [3.0, 5.0], [2.0, 3.0], [5.0, 7.0]])
    labels, blocks = np.array([0.0, 1.0, 0.0, 1.0]), np.array([0, 0, 1, 1])
    result = annotation.exact_statistics(values, labels, blocks)
    observed = method_statistics(
        values,
        labels,
        blocks,
        np.array([500.0, 800.0]),
        config=AuditConfig(permutations=19),
        integration_weights=np.ones(2),
    )
    assert result["permutations"] == 4
    assert result["p_npc"] == 0.5
    assert np.isclose(result["observed_max"], observed["stats"][0, 0])
    assert np.isclose(result["observed_integrated"], observed["stats"][0, 1])


def test_aerial_year_and_date_limit_do_not_propagate_a_label_to_other_years():
    accepted = pd.DataFrame(
        [
            dict(
                candidate_id="a",
                year=2023,
                aerial_date="2023-08-21",
                target="Herbaceous",
            )
        ]
    )
    qa = pd.DataFrame(
        [
            dict(
                candidate_id="a",
                year=2023,
                acquisition_datetime="2023-08-20",
                eligible_observation=True,
            ),
            dict(
                candidate_id="a",
                year=2023,
                acquisition_datetime="2023-11-20",
                eligible_observation=True,
            ),
            dict(
                candidate_id="a",
                year=2025,
                acquisition_datetime="2025-08-20",
                eligible_observation=True,
            ),
        ]
    )
    result = annotation.scene_candidates(accepted, qa)
    assert len(result) == 1
    assert result.iloc[0].year == 2023 and result.iloc[0].aerial_gap_days == 1


def test_manual_boundary_belt_preserves_other_and_marks_adjacent_uncertainty():
    case = dict(
        patch=[[-40, -40], [40, -40], [40, 40], [-40, 40]],
        other_polygons=[[[-0.6, -40], [0.6, -40], [0.6, 40], [-0.6, 40]]],
    )
    classes = annotation.image_classes(
        case, np.ones((3, 2, 2)) * 150, 2023, boundary_uncertainty=0.6
    )
    fractions = annotation.fractions(classes)
    np.testing.assert_allclose(
        [fractions["target"], fractions["other"], fractions["uncertain"]],
        [0.92, 0.04, 0.04],
    )


def test_uncertainty_overlay_preserves_known_holes():
    from shapely import Polygon

    polygon = Polygon(
        [(-2, -2), (2, -2), (2, 2), (-2, 2)],
        holes=[[(1, 1), (1, -1), (-1, -1), (-1, 1)]],
    )
    fig, ax = annotation.plt.subplots(figsize=(3, 3), dpi=100)
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    annotation.draw_geometry(ax, polygon, "orange", 1)
    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba())
    x, y = ax.transData.transform((0, 0)).astype(int)
    assert (image[image.shape[0] - y, x, :3] == 255).all()
    x, y = ax.transData.transform((1.5, 0)).astype(int)
    assert not (image[image.shape[0] - y, x, :3] == 255).all()
    annotation.plt.close(fig)


def test_real_aerial_timestamp_variants_with_fractional_seconds():
    accepted = pd.DataFrame(
        [
            dict(
                candidate_id="a",
                year=2022,
                aerial_date="2022-07-19T16:00:00Z",
                target="Herbaceous",
            ),
            dict(
                candidate_id="b",
                year=2024,
                aerial_date="2024-08-01T16:00:00.000000Z",
                target="Non-vegetated & dead",
            ),
        ]
    )
    qa = pd.DataFrame(
        [
            dict(
                candidate_id="a",
                year=2022,
                acquisition_datetime="2022-07-20T18:00:00+00:00",
                eligible_observation=True,
            ),
            dict(
                candidate_id="b",
                year=2024,
                acquisition_datetime="2024-08-02T18:00:00+00:00",
                eligible_observation=True,
            ),
        ]
    )
    result = annotation.scene_candidates(accepted, qa)
    assert result.aerial_gap_days.tolist() == [1, 1]


def test_edited_policy_requires_a_new_consistent_annotation_checkpoint(
    monkeypatch, tmp_path
):
    import hashlib
    import json
    import pytest

    reference = tmp_path / "reference"
    reference.mkdir()
    policy = tmp_path / "annotation_policy.json"
    policy.write_text("{}")
    fractions = tmp_path / "dated_cover_fractions.csv"
    fractions.write_text("target_fraction\n1\n")
    geometry = tmp_path / "annotations.gpkg"
    geometry.write_bytes(b"vector-checkpoint")
    source = reference / "regional_candidate_dataset.csv"
    source.write_text("candidate_id\na\n")
    records = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in {
            "policy_sha256": policy,
            "fraction_sha256": fractions,
            "geometry_sha256": geometry,
            "source_reference_sha256": source,
        }.items()
    }
    (tmp_path / "annotation_manifest.json").write_text(json.dumps(records))
    monkeypatch.setattr(annotation, "OUTPUT", tmp_path)
    monkeypatch.setattr(annotation, "POLICY", policy)
    monkeypatch.setattr(annotation, "REFERENCE", reference)
    annotation.validate_annotation_checkpoint()
    policy.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="Stale annotation checkpoint"):
        annotation.validate_annotation_checkpoint()
