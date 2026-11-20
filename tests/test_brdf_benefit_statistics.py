"""Regression checks for scientific pairing and compact permutation equivalence."""

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from spectralbridge.pft_method_audit import AuditConfig, method_statistics

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
stat = importlib.import_module("brdf_benefit_statistics")
drone = importlib.import_module("brdf_benefit_drone")
aop = importlib.import_module("brdf_benefit_aop")
sys.path.pop(0)


def test_compact_npc_exactly_matches_canonical_without_quadratic_energy():
    rng = np.random.default_rng(19)
    y = rng.normal(size=(30, 5))
    z = np.tile([0, 1], 15)
    blocks = np.repeat(["a", "b", "c"], 10)
    y[:, 0] += z * 0.7
    canonical = method_statistics(
        y,
        z,
        blocks,
        np.arange(5),
        config=AuditConfig(permutations=127),
        seed=12,
        integration_weights=np.ones(5),
    )
    p, n, s = stat.npc(y, z, blocks, permutations=127, seed=12)
    assert p == canonical["p"]["npc"]
    assert (n, s) == (30, 3)


def test_identical_predictions_have_zero_delta_interval_and_no_evidence():
    source = pd.DataFrame(
        dict(
            identity=["a", "b", "c", "d"],
            truth=["A", "A", "B", "B"],
            site=["x", "x", "y", "y"],
            prediction=["A", "B", "B", "B"],
        )
    )
    paired = pd.concat([source.assign(arm="no_brdf"), source.assign(arm="brdf")])
    result = stat.paired_scores(paired, permutations=31, bootstrap=100)
    assert result["ba_no_brdf"] == 0.75
    assert result["delta_ba"] == result["ci_low"] == result["ci_high"] == 0
    assert result["p_identity"] == result["p_site_exact"] == 1
    repeated = pd.concat([paired, paired[paired.identity == "a"]])
    assert stat.paired_scores(repeated, permutations=31, bootstrap=100) == result


def test_source_pairing_refuses_misaligned_year_or_label():
    source = pd.DataFrame(
        dict(
            identity=["a", "a"],
            site=["x", "x"],
            category=["A", "A"],
            year=[2020, 2021],
            arm=["no_brdf", "brdf"],
        )
    )
    with pytest.raises(ValueError, match="not exactly paired"):
        stat.paired_table(source)


def test_fractional_affine_uses_explicit_native_mapping_without_rescaling():
    plan = SimpleNamespace(
        bands=[
            SimpleNamespace(native_source_band_index=3, slope=2.0, intercept=0.01),
            SimpleNamespace(native_source_band_index=1, slope=0.5, intercept=-0.02),
        ]
    )
    data = np.array([[0.1, 0.2, 0.3], [-0.1, 0.1, 0.2]])
    np.testing.assert_allclose(
        drone.translate(data, plan), [[0.61, 0.03], [0.41, -0.07]]
    )


def test_aop_readonly_arrays_fill_and_decode_before_projection(monkeypatch):
    raw = ["raw_b001_wl0444nm", "raw_b002_wl0475nm"]
    frame = pd.DataFrame(
        dict(
            flight_id=["NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"] * 2,
            GlobalID=["{ABC}"] * 2,
            cover_category=["Evergreen"] * 2,
            aop_site=["NIWO"] * 2,
            x=[1.0, 2.0],
            y=[3.0, 4.0],
            epsg=[32613] * 2,
            **{
                raw[0]: [1000.0, -9999.0],
                raw[1]: [2000.0, -9999.0],
                "corr_b001_wl0444nm": [1100.0, -9999.0],
                "corr_b002_wl0475nm": [2200.0, -9999.0],
            },
        )
    )

    def project(values, wave):
        np.testing.assert_allclose(values, [[0.1, 0.2], [0.11, 0.22]])
        return np.repeat(values.mean(axis=1)[:, None], 7, axis=1), np.ones(7)

    monkeypatch.setattr(aop, "project_neon_to_oli", project)
    summary, audit = aop.flight_summary(frame, raw, [])
    assert audit["paired_rows"] == 1
    assert set(summary.identity) == {"abc"}
    assert len(summary) == 2
