"""Compact source contracts and leakage-free experimental audit orchestration."""

import json

import numpy as np
import pandas as pd
import pytest

from spectralbridge.mesma_readiness import (
    ReadinessConfig,
    decode_flight_history,
    run_readiness,
    META,
)


def test_nested_exposures_are_actual_flights_not_history_strings():
    value = json.dumps(
        [json.dumps(["flight1", "image1"]), json.dumps(["flight2", "image2"])]
    )
    assert decode_flight_history(value) == ("flight1", "flight2")
    with pytest.raises((ValueError, TypeError)):
        decode_flight_history('["invalid"]')


def test_small_complete_audit_no_identity_leakage_and_restart(tmp_path):
    compact = tmp_path / "compact"
    compact.mkdir()
    metadata = []
    neon = []
    oli = []
    rng = np.random.default_rng(13)
    for j, (species, category) in enumerate(
        [
            ("Populus tremuloides", "Deciduous"),
            ("Pinus contorta", "Evergreen"),
            ("Salix scouleriana", "Woody shrub"),
        ]
    ):
        for plant in range(6):
            identity = f"{j}_{plant}"
            metadata.append(
                {
                    **dict.fromkeys(META),
                    "GlobalID": identity,
                    "species": species,
                    "cover_category": category,
                    "aop_site": "NIWO",
                }
            )
            base = dict(
                site="NIWO",
                year=2023,
                GlobalID=identity,
                cover_category=category,
                species=species,
                flight_observations=1,
                flight_history=json.dumps([json.dumps(["flight", "image"])]),
            )
            a = np.ones(7) * 0.1 + np.eye(7)[j] * 0.6 + rng.normal(0, 0.001, 7)
            neon.append(
                {**base, **{f"corr_wl{w}nm": v for w, v in zip(range(400, 435, 5), a)}}
            )
            oli.append(
                {
                    **base,
                    **{
                        f"olioli_undarkened_wl{w}nm": v
                        for w, v in zip([443, 482, 561, 655, 865, 1609, 2201], a)
                    },
                }
            )
    source = tmp_path / "source.parquet"
    pd.DataFrame(metadata).to_parquet(source)
    pd.DataFrame(neon).to_parquet(compact / "corr_polygon_year.parquet")
    pd.DataFrame(oli).to_parquet(compact / "olioli_undarkened_polygon_year.parquet")
    config = ReadinessConfig(
        candidate_per_class=3,
        plant_folds=2,
        minimum_train=2,
        minimum_test=2,
        mc_replicates=2,
        all_flights=False,
    )
    output = tmp_path / "audit"
    result = run_readiness(source, compact, output, config=config, first_pass=True)
    assert result["status"].startswith("conditional_synthetic")
    membership = pd.read_parquet(output / "tables/fold_membership.parquet")
    for _, group in membership.groupby(["scheme", "fold"]):
        assert set(group[group.role.eq("train")].GlobalID).isdisjoint(
            group[group.role.eq("test")].GlobalID
        )
    estimates = pd.read_parquet(output / "tables/abundance_estimates.parquet")
    assert estimates.reconstruction_RMSE.notna().all()
    errors = pd.read_csv(output / "tables/fraction_errors.csv")
    assert errors.sum_violation_count.max() == 0
    assert errors.negative_fraction_count.max() == 0
    old = (output / "tables/fraction_errors.csv").stat().st_mtime_ns
    assert (
        run_readiness(source, compact, output, config=config, first_pass=True) == result
    )
    assert (output / "tables/fraction_errors.csv").stat().st_mtime_ns == old


def test_flight_holdout_replaces_annual_medians_with_actual_flight_only():
    from spectralbridge.mesma_readiness import replace_flight_targets

    table = pd.DataFrame({"GlobalID": ["a", "b"]})
    annual = {
        "NEON": np.array([[50.0, 50.0], [100.0, 100.0]]),
        "OLI": np.array([[50.0, 50.0], [100.0, 100.0]]),
    }
    index = pd.MultiIndex.from_tuples(
        [("b", "flight2")], names=["GlobalID", "flight_id"]
    )
    actual = {k: pd.DataFrame([[4.0, 6.0]], index=index) for k in annual}
    replace_flight_targets(annual, table, [1], "flight2", actual, 2)
    for values in annual.values():
        np.testing.assert_array_equal(values, [[50, 50], [2, 3]])
    with pytest.raises(KeyError):
        replace_flight_targets(annual, table, [0], "missing", actual, 1)


def test_all_actual_flight_folds_have_targets_and_ignore_history_encoding():
    from spectralbridge.mesma_readiness import _folds

    t = pd.DataFrame(
        {
            "label": ["a", "b", "a"],
            "site": ["NIWO"] * 3,
            "year": [2023] * 3,
            "GlobalID": ["p", "q", "r"],
            "flights": [("f1", "f2"), ("f1",), ("f2",)],
            "flight_history": ["nested JSON is not pipe delimited"] * 3,
        }
    )
    folds = [
        (name, mask)
        for name, kind, mask in _folds(t, "researcher", ReadinessConfig())
        if kind == "flight"
    ]
    assert len(folds) == 2
    assert folds[0][0] == "flight_f1"
    assert folds[0][1].tolist() == [True, True, False]
    assert folds[1][1].tolist() == [True, False, True]
