"""Paired targets, fold isolation, source references and owned restart contracts."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn", reason="optional analytics extra")
from spectralbridge.spectral_learning import LearningConfig  # noqa: E402
from spectralbridge.spectral_library_analytics import (
    prepare_fold,
    run_learning,
    fold_support,
)  # noqa: E402

pytestmark = pytest.mark.scientific


def fixture():
    rng = np.random.default_rng(12)
    table = pd.DataFrame(
        [
            dict(
                GlobalID=f"{c}{i}",
                observation_id=f"{c}{i}@{year}",
                site="NIWO",
                year=year,
                species=c,
                pft_code=c,
                cover_category=c,
                flights=("f" + str(year),),
                paired_zero_norm=False,
            )
            for c in ["DBT", "ECT"]
            for i in range(8)
            for year in [2020, 2023]
        ]
    )
    table["label"] = table.pft_code
    offset = table.label.eq("ECT").to_numpy()[:, None]
    arrays = {
        "NEON": rng.normal(size=(len(table), 110)) * 0.1 + offset,
        "OLI": rng.normal(size=(len(table), 7)) * 0.1 + offset,
    }
    waves = {
        "NEON": np.arange(400, 950, 5),
        "OLI": np.array([443, 482, 561, 655, 865, 1609, 2201]),
    }
    return table, arrays, waves


def test_flight_targets_are_actual_flight_not_annual_medians():
    table, arrays, waves = fixture()
    train = table.GlobalID.str.endswith(("0", "1", "2", "3")).to_numpy()
    test = ~train
    keys = pd.MultiIndex.from_tuples(
        [(g, "f2023") for g in table.loc[test, "GlobalID"].unique()],
        names=["GlobalID", "flight_id"],
    )
    actual = {
        sensor: pd.DataFrame(np.full((len(keys), len(w)), 9.0), index=keys)
        for sensor, w in waves.items()
    }
    config = LearningConfig(minimum_train=2, minimum_test=1, minimum_calibration=2)
    prepared, support, status = prepare_fold(
        table, arrays, actual, "flight_f2023", "flight", train, test, config
    )
    assert status == "eligible"
    for sensor in arrays:
        np.testing.assert_allclose(prepared["test_arrays"][sensor], 9)
        assert not np.allclose(arrays[sensor][prepared["test"]], 9)
    assert support.status.eq("closed_evaluable").all()


def test_absent_training_class_is_open_set_not_closed_failure():
    table, arrays, waves = fixture()
    train = table.label.eq("DBT").to_numpy()
    test = ~train
    support = fold_support(
        table, train, test, LearningConfig(minimum_train=2, minimum_test=1)
    )
    assert support.set_index("label").loc["ECT", "status"] == "absent_training_open_set"
    prepared, _, status = prepare_fold(
        table,
        arrays,
        {},
        "site_S",
        "site",
        train,
        test,
        LearningConfig(minimum_train=2, minimum_test=1),
    )
    assert prepared is None and status == "insufficient_multiclass_support"


@pytest.mark.integration
def test_first_pass_all_representations_have_identical_tests_and_restart(
    tmp_path, monkeypatch
):
    import spectralbridge.spectral_library_analytics as module

    table, arrays, waves = fixture()
    monkeypatch.setattr(
        module,
        "load_analytics_inputs",
        lambda *args: (table, arrays, waves, {}, dict(source="invented fixture")),
    )
    config = LearningConfig(
        minimum_train=2,
        minimum_test=1,
        minimum_calibration=2,
        bootstraps=19,
        inner_folds=2,
        plant_folds=2,
    )
    root = tmp_path / "run"
    manifest = run_learning(
        tmp_path, tmp_path, root, config=config, first_pass=True, workers=1
    )
    assert manifest["fit_cases"] == 19
    predictions = pd.read_parquet(root / "predictions.parquet")
    reference = None
    for _, group in predictions.groupby(["representation", "model"]):
        ids = sorted(group.observation_id)
        if reference is None:
            reference = ids
        assert reference == ids
    for path in (root / "checkpoints").glob("*/memberships.parquet"):
        membership = pd.read_parquet(path)
        roles = {role: set(x.GlobalID) for role, x in membership.groupby("role")}
        assert roles["proper_training"].isdisjoint(roles["test"])
        assert roles.get("calibration", set()).isdisjoint(roles["test"])
    before = {str(p): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert (
        run_learning(
            tmp_path, tmp_path, root, config=config, first_pass=True, workers=1
        )
        == manifest
    )
    assert before == {
        str(p): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()
    }
    next((root / "checkpoints").glob("*/model.joblib")).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checkpoint"):
        run_learning(
            tmp_path, tmp_path, root, config=config, first_pass=True, workers=1
        )


def test_reference_index_is_not_a_spectral_copy_and_unchanged_load_reuses_files(
    tmp_path, monkeypatch
):
    import json
    import spectralbridge.spectral_library_analytics as module
    from spectralbridge.plant_spectral_atlas import _file_hash

    table, arrays, waves = fixture()
    table["flight_history"] = [
        json.dumps([json.dumps(["f" + str(year), "f" + str(year) + ".img"])])
        for year in table.year
    ]
    source = tmp_path / "original.parquet"
    table.to_parquet(source, index=False)
    original = _file_hash(source)
    analysis = tmp_path / "paired"
    compact = analysis / "compact"
    (compact / "corr").mkdir(parents=True)
    grids = pd.DataFrame(
        {
            "flight_id": ["f2020", "f2023"],
            "source_image": ["f2020.img", "f2023.img"],
            "grid_id": ["grid0", "grid0"],
        }
    )
    path = compact / "corr/flight_source_grids.csv"
    grids.to_csv(path, index=False)
    (analysis / "statistics_manifest.json").write_text(
        json.dumps(
            {
                "identity": {"source": original},
                "outputs": {"compact/corr/flight_source_grids.csv": _file_hash(path)},
            }
        )
    )
    monkeypatch.setattr(
        module, "load_compact_inputs", lambda *args: (table, arrays, waves)
    )
    monkeypatch.setattr(module, "flight_target_tables", lambda *args: {})
    output = tmp_path / "index"
    module.load_analytics_inputs(source, compact, output)
    index = pd.read_parquet(output / "canonical_analysis_index.parquet")
    assert len(index) == len(table)
    assert not any("_wl" in column for column in index)
    assert index.native_grid_ids.eq('["grid0"]').all()
    before = {p.name: p.stat().st_mtime_ns for p in output.iterdir()}
    module.load_analytics_inputs(source, compact, output)
    assert before == {p.name: p.stat().st_mtime_ns for p in output.iterdir()}
    assert _file_hash(source) == original


def test_staged_cli_reuses_sealed_run_without_reprofiling(tmp_path, monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "analytics_cli",
        Path(__file__).parents[1] / "examples/spectral_library_analytics.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "learning_manifest.json").write_text('{"status":"complete"}')
    calls = []
    monkeypatch.setattr(module, "run_learning", lambda *a, **kw: calls.append("reused"))
    monkeypatch.setattr(
        module,
        "profile_learning",
        lambda *a, **kw: pytest.fail("must not rewrite sealed profile"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analytics",
            "original.parquet",
            "--compact",
            "compact",
            "--output",
            str(tmp_path),
            "--stage",
            "all",
        ],
    )
    module.main()
    assert calls == ["reused"]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analytics",
            "original.parquet",
            "--compact",
            "compact",
            "--output",
            str(tmp_path),
            "--stage",
            "profile",
        ],
    )
    with pytest.raises(SystemExit):
        module.main()
