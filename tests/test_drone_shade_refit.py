"""Shade refits preserve the original training subset and expose missing bands."""

import importlib
from pathlib import Path
import sys

import numpy as np
import pytest

DIRECTORY = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(DIRECTORY))
refit = importlib.import_module("drone_shade_excluded_refit")
report = importlib.import_module("drone_shade_refit_summary")
sys.path.remove(str(DIRECTORY))


def test_shade_exclusion_cannot_reintroduce_original_heldout_pixels():
    original = np.array([[True, True, False], [True, False, True]])
    mask = np.array([[0, 1, 0], [255, 0, 0]], dtype=np.uint8)
    training = refit.retained_training(original, mask)
    assert training.tolist() == [[True, False, False], [False, False, True]]
    assert not (training & ~original).any()
    with pytest.raises(ValueError, match="Unknown"):
        refit.retained_training(original, np.full(original.shape, 3))


def test_aggregate_valid_with_unavailable_bands_is_not_a_full_pass():
    model = dict(
        validation=dict(
            status="VALID",
            fits=[
                dict(band=i, status="VALID" if i < 8 else "NOT_APPLICABLE")
                for i in range(10)
            ],
        )
    )
    summary = report.band_support(model)
    assert summary["valid_bands"] == 8 and not summary["full_band_pass"]
    assert summary["unavailable_bands"] == [9, 10]
    for f in model["validation"]["fits"]:
        f["status"] = "VALID"
    assert report.band_support(model)["full_band_pass"]


def test_baseline_kernel_configuration_and_reference_are_reproduced():
    # Independent of native production data; explicit saved settings differ from
    # the generic direct-fit defaults and must be passed to the fit function.
    driver = refit.setup()
    c = driver.support.c
    settings = c.BRDFKernelConfig(
        volume_kernel="RossThick",
        geom_kernel="LiDenseR",
        b_r=10.0,
        h_b=2.0,
        solar_zn_type="scene",
    )
    expected = np.array([1.0, -0.04586202988221, -1.0])
    np.testing.assert_allclose(
        c._reference_design(c.ReferenceGeometry(), settings), expected, atol=1e-12
    )


def test_fractional_mask_cutoffs_have_distinct_restart_paths():
    names = [
        refit.mask_filename("flight", t) for t in [0.09, 0.095, 0.0975, 0.099, 0.10]
    ]
    assert len(set(names)) == 5
    assert names[0] == "flight__shade_candidate_relative_visible_09pct.tif"
    assert names[-1] == "flight__shade_candidate_relative_visible_10pct.tif"
    assert "9p5pct" in names[1]
