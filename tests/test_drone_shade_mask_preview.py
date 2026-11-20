"""Candidate masks never infer shade truth or confuse missing data with sunlight."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1] / "examples/drone_shade_mask_preview.py"
spec = importlib.util.spec_from_file_location("drone_shade_preview", PATH)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def test_visible_bands_follow_wavelengths_not_positions():
    assert preview.visible_indices([668, 900, 475, 560]) == [2, 3, 0]
    with pytest.raises(ValueError, match="unambiguous"):
        preview.visible_indices([668, 475, 475, 560])


def test_full_native_support_nodata_and_threshold_boundary():
    cube = np.full((4, 1, 4), 10.0)
    cube[:3, 0, 0] = 1
    cube[:3, 0, 1] = 2
    cube[3, 0, 2] = np.nan  # Missing non-visible band still invalidates pixel.
    mask, _ = preview.classify(cube, [0, 1, 2], 10, 0.2)
    assert mask.tolist() == [[1, 0, 255, 0]]
    cube[3, 0, 2] = -9999
    mask, _ = preview.classify(cube, [0, 1, 2], 10, 0.2, -9999)
    assert mask[0, 2] == 255


def test_relative_masks_are_scale_invariant_nested_and_chunk_consistent():
    cube = np.arange(36, dtype=float).reshape(3, 3, 4)
    conservative, _ = preview.classify(cube, [0, 1, 2], 30, 0.3)
    stronger, _ = preview.classify(cube, [0, 1, 2], 30, 0.6)
    assert np.all((conservative != 1) | (stronger == 1))
    scaled, _ = preview.classify(cube * 10000, [0, 1, 2], 300000, 0.6)
    np.testing.assert_array_equal(stronger, scaled)
    chunks = [
        preview.classify(cube[:, row : row + 1], [0, 1, 2], 30, 0.6)[0]
        for row in range(3)
    ]
    np.testing.assert_array_equal(stronger, np.concatenate(chunks))
    with pytest.raises(ValueError, match="normalizer"):
        preview.classify(cube, [0, 1, 2], 0, 0.2)


def test_conservative_trial_masks_all_bands_without_mutating_retained_values():
    import sys

    directory = str(PATH.parent)
    sys.path.insert(0, directory)
    try:
        import drone_conservative_shade_translation_trial as trial
    finally:
        sys.path.remove(directory)
    cube = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    original = cube.copy()
    mask = np.array([[0, 1, 255], [0, 0, 1]], dtype=np.uint8)
    output = trial.mask_chunk(cube, mask, np.nan)
    np.testing.assert_array_equal(cube, original)
    np.testing.assert_array_equal(output[mask == 0], original[mask == 0])
    assert np.isnan(output[mask != 0]).all()
    with pytest.raises(ValueError, match="Unknown mask code"):
        trial.mask_chunk(cube, np.full((2, 3), 5), np.nan)
    with pytest.raises(ValueError, match="dimensions differ"):
        trial.mask_chunk(cube, np.zeros((1, 3)), np.nan)
