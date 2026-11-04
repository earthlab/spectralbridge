"""Synthetic arithmetic/eligibility checks; no empirical Goldhill calibration."""

import numpy as np
import pytest
from spectralbridge.radiometry import Radiometry


def test_documented_divisor_composes_with_fixed_encoding_for_all_uint16_codes():
    dn = np.arange(65536, dtype=np.float32)
    stored = dn * np.float32(10000 / 65535)
    synthetic = Radiometry(
        65535 / (32768 * 10000),
        0,
        "VALID",
        "Synthetic mathematical test, not a Goldhill calibration declaration",
    )
    decoded = synthetic.to_physical(stored)
    np.testing.assert_allclose(decoded, dn / 32768, atol=1.2e-7, rtol=0)
    reconstructed = synthetic.to_stored(decoded) * np.float32(65535 / 10000)
    np.testing.assert_array_equal(np.rint(reconstructed), dn)
    assert decoded[0] == 0
    assert decoded[32768] == pytest.approx(1, abs=1.2e-7)
    assert decoded[-1] > 1.99  # Valid high codes must not be clipped to one.


def test_supported_hypothesis_does_not_promote_unverified_real_units():
    record = Radiometry(
        65535 / (32768 * 10000),
        0,
        "UNSUPPORTED",
        "Plausible convention; applied source calibration unverified",
        encoding={
            "kind": "range_normalized_dn",
            "physical_calibration_status": "UNVERIFIED",
            "nodata": -9999,
        },
    )
    with pytest.raises(ValueError, match="Radiometry UNSUPPORTED"):
        record.to_physical(np.array([0, 5000, -9999], np.float32))
