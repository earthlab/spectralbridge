"""Scientific gap, sampling, null, response and mixture invariants (all offline)."""

import numpy as np
import pandas as pd
import pytest
from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas
from spectralbridge.pft_method_audit import AuditConfig, method_statistics
from spectralbridge.sensor_pft_transfer import (
    project_neon_to_oli,
    OLI_CENTERS,
    validate_sensor_coordinates,
)
from spectralbridge.mixtures import (
    fcls,
    fit_models,
    grouped_identity_split,
    validate_holdout,
    adequacy_status,
    detection_metrics,
)

pytestmark = pytest.mark.scientific


def test_replicating_pixels_changes_neither_biological_N_nor_inference(tmp_path):
    rows = []
    for plant in range(8):
        for pixel in range(3):
            rows.append(
                dict(
                    GlobalID=str(plant),
                    species="A" if plant < 4 else "B",
                    flight_id="f",
                    source_image="f.img",
                    polygon_id=plant,
                    corr_b001_wl0400nm=plant * 0.1 + pixel * 0.01,
                    corr_b002_wl0405nm=plant * 0.2 - pixel * 0.01,
                    corr_b003_wl0410nm=plant * 0.3 + pixel * 0.01,
                )
            )
    frame = pd.DataFrame(rows)
    results = []
    for name, data in [
        ("original", frame),
        ("duplicated", pd.concat([frame] * 7, ignore_index=True)),
    ]:
        source = tmp_path / (name + ".parquet")
        data.to_parquet(source)
        audit = run_plant_spectral_atlas(
            source, tmp_path / name, make_figures=False, min_plants_per_species=1
        )
        assert audit["independent_labelled_plants"] == 8
        table = pd.read_parquet(
            tmp_path / name / "plant_harmonized_spectra.parquet"
        ).sort_values("GlobalID")
        y = table[["corr_wl400nm", "corr_wl405nm", "corr_wl410nm"]].to_numpy()
        result = method_statistics(
            y,
            table.species.eq("B"),
            np.zeros(8),
            [400, 405, 410],
            config=AuditConfig(permutations=39),
            seed=19,
        )
        assert len(result["rows"]) == 8
        results.append(result)
    np.testing.assert_allclose(results[0]["stats"], results[1]["stats"])
    assert results[0]["p"] == results[1]["p"]


def test_identical_group_distributions_have_zero_effect_and_known_offset_matches_algebra():
    a = np.array([-1.0, 0, 1])[:, None] * [1, 2, 3]
    labels = [0] * 3 + [1] * 3
    cfg = AuditConfig(permutations=39)
    same = method_statistics(
        np.vstack([a, a]), labels, np.zeros(6), [400, 405, 410], config=cfg
    )
    np.testing.assert_allclose(same["curves"][0], 0, atol=1e-14)
    assert same["p"]["max"] == 1
    shifted = np.vstack([a, a + 2])
    result = method_statistics(
        shifted, labels, np.zeros(6), [400, 405, 410], config=cfg
    )
    np.testing.assert_allclose(result["curves"][0], 2)
    expected = np.max(2 / (shifted.std(0, ddof=1) / np.sqrt(1.5)))
    np.testing.assert_allclose(result["stats"][0, 0], expected)


@pytest.mark.parametrize("scale", [0.01, 3.0, 1000.0])
def test_common_positive_scaling_preserves_standardized_ensemble(scale):
    rng = np.random.default_rng(72)
    y = rng.normal(size=(20, 5))
    z = np.tile([0, 1], 10)
    cfg = AuditConfig(permutations=39)
    a = method_statistics(
        y, z, np.zeros(20), np.arange(400, 425, 5), config=cfg, seed=17
    )
    b = method_statistics(
        y * scale, z, np.zeros(20), np.arange(400, 425, 5), config=cfg, seed=17
    )
    np.testing.assert_allclose(a["stats"], b["stats"], atol=1e-10)
    assert a["p"] == b["p"]


def test_gaussian_projection_flat_linear_and_fwhm_analytic_expectations():
    w = np.arange(200.0, 3001.0, 0.5)
    flat, coverage = project_neon_to_oli(np.full((2, len(w)), 0.3), w)
    np.testing.assert_allclose(flat, 0.3, atol=1e-12)
    np.testing.assert_allclose(coverage, 1, atol=1e-8)
    linear, _ = project_neon_to_oli((0.02 + w * 0.0001)[None, :], w)
    np.testing.assert_allclose(linear[0], 0.02 + OLI_CENTERS * 0.0001, atol=1e-8)
    # Independent continuous Gaussian expectation E[(X-mu)^2] = sigma^2.
    from spectralbridge.sensor_pft_transfer import OLI_WIDTHS

    squared, _ = project_neon_to_oli((w * w)[None, :], w)
    np.testing.assert_allclose(
        squared[0] - OLI_CENTERS**2, (OLI_WIDTHS / 2.354820045) ** 2, rtol=2e-7
    )


def test_sensor_support_and_band_order_are_explicit():
    with pytest.raises(ValueError, match="increasing"):
        project_neon_to_oli([[1, 2, 3]], [410, 405, 400])
    with pytest.raises(ValueError, match="increasing"):
        project_neon_to_oli([[1, 2, 3]], [400, np.nan, 410])
    with pytest.raises(ValueError):
        project_neon_to_oli([[np.nan] * 3], [400, 405, 410])
    with pytest.raises(ValueError):
        validate_sensor_coordinates(OLI_CENTERS[::-1], "OLI")


@pytest.mark.parametrize("seed", range(5))
def test_fcls_fraction_and_row_order_properties(seed):
    rng = np.random.default_rng(seed)
    truth = rng.dirichlet(np.ones(3), size=12)
    e = np.eye(3)
    fit = fcls(truth, e)
    np.testing.assert_allclose(fit["fractions"], truth, atol=1e-9)
    np.testing.assert_allclose(
        fcls(truth[::-1], e)["fractions"][::-1], truth, atol=1e-9
    )
    assert np.all(fit["fractions"] >= 0)
    np.testing.assert_allclose(fit["fractions"].sum(1), 1)


@pytest.mark.parametrize("kind", ["plant", "site", "flight"])
def test_holdouts_reject_deliberate_identity_and_candidate_leakage(kind):
    # The externally defined site/flight test mask can expose a repeated identity.
    ids = np.array(["a", "a", "b", "c"])
    test = np.array([False, True, False, False])
    train, purged_test = grouped_identity_split(ids, test)
    validate_holdout(ids, train, purged_test, [2, 3])
    with pytest.raises(ValueError, match="identity leakage"):
        validate_holdout(ids, ~test, test)
    with pytest.raises(ValueError, match="outside training"):
        validate_holdout(ids, train, test, [1, 2])
    renamed = np.array(["x", "x", "y", "z"])
    np.testing.assert_array_equal(grouped_identity_split(renamed, test)[0], train)


def test_unknown_exact_fit_is_not_promoted_to_valid_membership():
    a, b = np.eye(2)
    unknown = 0.5 * a + 0.5 * b
    fit = fit_models(unknown[None, :], [0, 1], [a, b], max_components=2)
    assert fit["RMSE"][0] < 1e-7
    assert (
        adequacy_status(fit["RMSE"], 0.01)[0] == "LOW_RESIDUAL_NOT_VALIDATED_MEMBERSHIP"
    )
    assert adequacy_status([0.02], 0.01)[0] == "NO_ADEQUATE_LIBRARY_MODEL"
    assert adequacy_status([0], np.nan)[0] == "UNASSESSED_MISSING_THRESHOLD"
    with pytest.raises(ValueError):
        adequacy_status([-1], 0.01)


@pytest.mark.parametrize(
    "truth,estimated,expected",
    [
        ([0, 1], [0, 1], (0.0, 0.0)),
        ([0, 1], [1, 1], (1.0, 0.0)),
        ([0, 1], [0, 0], (0.0, 1.0)),
        ([0, 0.05, 0.2, 1], [0.1, 0.1, 0.099, 1], (1.0, 1 / 3)),
    ],
)
def test_detection_absence_presence_thresholds(truth, estimated, expected):
    result = detection_metrics(truth, estimated)
    np.testing.assert_allclose(
        [result["false_positive_rate"], result["false_negative_rate"]], expected
    )
    assert result["TP"] + result["FP"] + result["TN"] + result["FN"] == len(truth)


def test_detection_undefined_denominators_and_invalid_fractions():
    assert np.isnan(detection_metrics([0], [0])["false_negative_rate"])
    assert np.isnan(detection_metrics([1], [1])["false_positive_rate"])
    assert detection_metrics([1], [1], threshold=1)["TP"] == 1
    for a, b in [([np.nan], [0]), ([0], [1.1]), ([0, 1], [0])]:
        with pytest.raises(ValueError):
            detection_metrics(a, b)
