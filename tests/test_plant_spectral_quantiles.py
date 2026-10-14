"""Boosted signatures preserve replication, unsupported gaps and matching evidence."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("xgboost")

from spectralbridge.plant_spectral_quantiles import (  # noqa: E402
    QUANTILES,
    QuantileModelConfig,
    _fit_checkpoint,
    _quantile_distances_many,
    _split_plants,
    fit_quantile_signature,
    quantile_distance,
    rank_unknown_spectrum,
    run_boosted_quantile_atlas,
)
from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas  # noqa: E402
from spectralbridge.plant_spectral_regions import run_regional_plant_atlas  # noqa: E402


def small_config(**kwargs):
    return QuantileModelConfig(
        quantiles=(0.1, 0.5, 0.9),
        boosting_rounds=4,
        max_depth=2,
        min_plants_per_species=2,
        workers=1,
        stages=("corr",),
        **kwargs,
    )


def test_integer_percentiles_are_99_interior_quantiles():
    assert len(QUANTILES) == 99 and QUANTILES[0] == 0.01 and QUANTILES[-1] == 0.99
    for q in [(0, 0.5, 0.9), (0.1, 0.5, 1), (0.5, 0.1, 0.9)]:
        with pytest.raises(ValueError, match="Quantiles"):
            replace(small_config(), quantiles=q).validate()


def test_fits_preserve_wavelength_gaps_negative_values_and_99_lines():
    w = np.array([400, 405, 410, 415, 1400, 1500, 1505, 1510, 1515.0])
    y = np.array(
        [[-2, -1, 0, 1, np.nan, 3, 4, 5, 6], [-1, 0, 1, 2, np.nan, 4, 5, 6, 7.0]]
    )
    config = replace(small_config(), quantiles=QUANTILES)
    raw, ordered, metrics = fit_quantile_signature(w, y, config=config)
    assert raw.shape == ordered.shape == (99, len(w))
    assert np.isnan(raw[:, 4]).all() and np.isnan(ordered[:, 4]).all()
    assert np.isfinite(ordered[:, [0, 1, 2, 3, 5, 6, 7, 8]]).all()
    assert metrics["segments"] == 2
    assert np.all(np.diff(ordered[:, 0]) >= 0)
    assert ordered[:, 0].min() < 0  # no clipping of valid negatives
    np.testing.assert_array_equal(ordered, np.sort(raw, axis=0))


def test_equal_spectrum_weights_ignore_external_pixel_counts():
    # Fitter accepts one spectrum per independent unit, never pixel-count inputs.
    w = np.arange(400, 440, 5.0)
    y = np.array([np.sin(w / 20), np.sin(w / 20) + 2])
    raw, _, _ = fit_quantile_signature(w, y, config=small_config())
    reverse, _, _ = fit_quantile_signature(w, y[::-1], config=small_config())
    np.testing.assert_allclose(raw, reverse)


def test_scalar_and_bounded_batch_pinball_scores_agree():
    rng = np.random.default_rng(3)
    q = np.array([0.1, 0.5, 0.9])
    curves = np.sort(rng.normal(size=(3, 8)), axis=0)
    queries = rng.normal(size=(5, 8))
    expected = np.array([quantile_distance(row, curves, q)[0] for row in queries])
    np.testing.assert_allclose(
        _quantile_distances_many(queries, curves, q), expected, atol=1e-12
    )
    queries[0, 2] = np.nan
    expected = np.array([quantile_distance(row, curves, q)[0] for row in queries])
    np.testing.assert_allclose(
        _quantile_distances_many(queries, curves, q), expected, atol=1e-12
    )
    with pytest.raises(ValueError, match="Insufficient"):
        quantile_distance([np.nan, 1], np.array([[0, 0], [1, 1], [2, 2]]), q)


def test_holdout_identity_is_disjoint_stable_and_grouped():
    plants = pd.DataFrame(
        {
            "GlobalID": list("ABCDEFGH"),
            "region": ["NIWO"] * 4 + ["WREF"] * 4,
            "species": ["Test species"] * 8,
        }
    )
    a = _split_plants(plants, small_config())
    b = _split_plants(plants, small_config())
    pd.testing.assert_frame_equal(a, b)
    assert a[a.partition == "held_out"].groupby("region").size().to_dict() == {
        "NIWO": 1,
        "WREF": 1,
    }
    assert set(a.loc[a.partition == "train", "GlobalID"]).isdisjoint(
        a.loc[a.partition == "held_out", "GlobalID"]
    )


def test_fit_checkpoint_reuse_is_independent_of_presentation_identity(tmp_path):
    config = small_config()
    w = np.arange(400, 430, 5.0)
    y = np.array([w, w + 2])
    meta = {
        "level": "species",
        "region": "NIWO",
        "species": "Test species",
        "GlobalID": "",
        "stage": "corr",
        "partition": "full",
        "independent_plants": 2,
    }
    first = _fit_checkpoint(tmp_path, meta, w, y, config, {"implementation": "old"})
    path = tmp_path / first["checkpoint"]
    before = path.stat().st_mtime_ns
    second = _fit_checkpoint(
        tmp_path, meta, w, y, replace(config, workers=2), {"implementation": "new"}
    )
    assert first == second and path.stat().st_mtime_ns == before
    with np.load(path) as saved:
        assert set(saved.files) == {
            "wavelengths_nm",
            "quantiles",
            "raw_curves",
            "ordered_curves",
            "empirical_median",
        }


def _source_library(tmp_path):
    rows = []
    for i, (region, species) in enumerate(
        [
            ("NIWO", "Abies testii"),
            ("NIWO", "Abies testii"),
            ("NIWO", "Pinus testii"),
            ("NIWO", "Pinus testii"),
            ("WREF", "Abies testii"),
            ("WREF", "Abies testii"),
        ]
    ):
        for flight in [1, 2]:
            fid = (
                f"NEON_D13_{region}_DP1_L00{flight}-1_20230815_directional_reflectance"
            )
            for _ in range(1 if flight == 1 else 3):
                row = {
                    "GlobalID": f"plant-{i}",
                    "species": species,
                    "polygon_id": i + 1,
                    "flight_id": fid,
                    "source_image": fid + ".img",
                    "source_parquet": fid + "_polygons.parquet",
                    "aop_site": region,
                    "ecoregion": region,
                }
                for stage, factor in [
                    ("raw", 2),
                    ("corr", 1),
                    ("olioli", 0.5),
                    ("micasense", 0.25),
                ]:
                    bands = (
                        [400, 405, 410, 1400, 1500, 1505, 1510]
                        if stage in ("raw", "corr")
                        else [475, 865]
                    )
                    for band, wl in enumerate(bands, 1):
                        row[f"{stage}_b{band:03}_wl{wl:04}nm"] = factor * (
                            (500 if species.startswith("Pinus") else 50)
                            + i
                            + flight
                            + band
                        )
                rows.append(row)
    source = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(source)
    return source


def test_complete_model_flow_and_unknown_matching(tmp_path):
    source = _source_library(tmp_path)
    comparisons = tmp_path / "comparisons"
    products = comparisons / "products"
    for stage in ["raw", "corr", "olioli", "micasense"]:
        run_plant_spectral_atlas(
            source,
            products / stage,
            spectral_stage=stage,
            make_figures=False,
            grid_step_nm=5 if stage in ("raw", "corr") else None,
            excluded=((1340, 1450), (1790, 2000)) if stage in ("raw", "corr") else (),
        )
    run_regional_plant_atlas(
        source, comparisons, comparisons / "regional", min_plants_per_species=2, dpi=300
    )
    out = tmp_path / "models"
    audit = run_boosted_quantile_atlas(
        comparisons, out, config=small_config(), make_individual_pdf=False
    )
    assert audit["independent_plants"] == 6 and audit["quantile_lines"] == 3
    assert audit["individual_models"] == 6 and audit["full_species_models"] == 5
    split = pd.read_parquet(out / "training_holdout_plants.parquet")
    results = pd.read_csv(out / "held_out_individual_reference_matches.csv")
    assert set(results.reference_GlobalID).issubset(
        split.loc[split.partition == "train", "GlobalID"]
    )
    assert set(results.GlobalID).issubset(
        split.loc[split.partition == "held_out", "GlobalID"]
    )
    assert (out / "ALL_species_quantiles.pdf").is_file()
    assert (out / "NIWO_individual_examples.svg").is_file()
    model_index = pd.read_parquet(out / "model_index.parquet")
    model = model_index[
        (model_index.level == "individual") & (model_index.GlobalID == "plant-0")
    ].iloc[0]
    with np.load(out / "checkpoints" / model.checkpoint) as saved:
        query_w = saved["wavelengths_nm"]
        query_y = saved["empirical_median"]
    ranks = rank_unknown_spectrum(out, query_w, query_y, stage="corr", region="NIWO")
    assert ranks.iloc[0].species == "Abies testii"
    individual = rank_unknown_spectrum(
        out,
        query_w,
        query_y,
        stage="corr",
        level="individual",
        exclude_plant_ids=["plant-0"],
    )
    assert "plant-0" not in individual.GlobalID.tolist()
    manifest = (out / "quantile_manifest.json").read_bytes()
    assert (
        run_boosted_quantile_atlas(
            comparisons, out, config=small_config(), make_individual_pdf=False
        )
        == audit
    )
    assert (out / "quantile_manifest.json").read_bytes() == manifest


def test_template_baseline_is_bounded_and_matches_direct_distance():
    import runpy
    from pathlib import Path

    function = runpy.run_path(
        str(
            Path(__file__).resolve().parents[1]
            / "examples/evaluate_quantile_matches.py"
        )
    )["nearest_templates"]
    queries = np.array([[0.0, 2.0, np.nan], [10.0, 9.0, np.nan]])
    references = np.array([[0.0, 1.0, np.nan], [9.0, 9.0, np.nan]])
    mae, rmse = function(queries, references, ["a", "b"], batch_size=1)
    assert mae.tolist() == rmse.tolist() == ["a", "b"]
    expected = np.argmin(
        np.mean((queries[:, :2, None] - references[:, :2].T[None, :, :]) ** 2, axis=1),
        axis=1,
    )
    assert rmse.tolist() == np.array(["a", "b"])[expected].tolist()


def test_template_baseline_rejects_insufficient_common_coverage():
    import runpy
    from pathlib import Path

    function = runpy.run_path(
        str(
            Path(__file__).resolve().parents[1]
            / "examples/evaluate_quantile_matches.py"
        )
    )["nearest_templates"]
    with pytest.raises(ValueError, match="Insufficient"):
        function([[1, np.nan]], [[1, np.nan]], ["a"])


def test_physical_micasense_matching_rejects_unverified_export_labels(tmp_path):
    import json
    from spectralbridge.plant_spectral_atlas import _file_hash

    root = tmp_path / "models"
    (root / "checkpoints").mkdir(parents=True)
    w = np.array([475, 560, 668, 717, 840, 841, 842, 843, 844, 845.0])
    path = root / "checkpoints" / "model.npz"
    np.savez_compressed(
        path,
        wavelengths_nm=w,
        quantiles=[0.1, 0.5, 0.9],
        ordered_curves=np.array([np.arange(10), np.arange(10) + 1, np.arange(10) + 2]),
    )
    pd.DataFrame(
        [
            {
                "level": "species",
                "stage": "micasense",
                "partition": "full",
                "region": "ALL",
                "species": "Test species",
                "GlobalID": "",
                "checkpoint": path.name,
            }
        ]
    ).to_parquet(root / "model_index.parquet")
    (root / "quantile_manifest.json").write_text(
        json.dumps(
            {
                "outputs": {
                    "model_index.parquet": _file_hash(root / "model_index.parquet"),
                    "checkpoints/model.npz": _file_hash(path),
                }
            }
        )
    )
    with pytest.raises(ValueError, match="unverified"):
        rank_unknown_spectrum(root, w, np.arange(10) + 1, stage="micasense")
    result = rank_unknown_spectrum(
        root,
        w,
        np.arange(10) + 1,
        stage="micasense",
        allow_unverified_export_coordinates=True,
    )
    assert (
        result.iloc[0].species == "Test species"
    )  # explicit archive-coordinate replay only


def test_quantile_reports_put_each_sensor_in_a_separate_column(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    import spectralbridge.plant_spectral_quantiles as module
    import spectralbridge.plant_spectral_comparison as comparison

    captured = []

    def figure(root, records, rows, columns, *args, **kwargs):
        captured.append(columns)
        return plt.figure()

    monkeypatch.setattr(module, "_quantile_figure", figure)
    monkeypatch.setattr(comparison, "_save", lambda fig, *args: plt.close(fig))
    index = pd.DataFrame(
        [
            {
                "partition": "full",
                "level": "species",
                "plot_min": -1,
                "plot_max": 10,
                "region": "ALL",
                "species": "Test species",
                "stage": stage,
            }
            for stage in ("raw", "corr", "olioli", "micasense")
        ]
    )
    module._plot_quantile_reports(
        tmp_path, index, QuantileModelConfig(), make_individual_pdf=False
    )
    assert len(captured) == 1
    assert [stages for heading, stages in captured[0]] == [
        ("raw",),
        ("corr",),
        ("olioli",),
        ("micasense",),
    ]


@pytest.mark.parametrize(
    "stage,grid",
    [
        ("olioli", [443.0, 482.0, 561.0, 655.0, 865.0, 1609.0, 2201.0]),
        (
            "micasense",
            [475.0, 560.0, 668.0, 717.0, 840.0, 841.0, 842.0, 843.0, 844.0, 845.0],
        ),
    ],
)
def test_separate_sensor_column_uses_its_own_wavelength_range(tmp_path, stage, grid):
    import matplotlib.pyplot as plt
    from spectralbridge.plant_spectral_quantiles import _draw_quantile_panel

    (tmp_path / "checkpoints").mkdir()
    w = np.array(grid)
    values = np.broadcast_to(np.arange(len(w)), (3, len(w))).astype(float)
    np.savez(
        tmp_path / "checkpoints" / "sensor.npz",
        wavelengths_nm=w,
        ordered_curves=values,
        quantiles=np.array([0.1, 0.5, 0.9]),
        empirical_median=values[1],
    )
    records = pd.DataFrame([{"stage": stage, "checkpoint": "sensor.npz"}])
    fig, ax = plt.subplots()
    _draw_quantile_panel(ax, records, tmp_path, (), (-1, 10), (stage,))
    assert ax.get_xlim()[0] < w[0] and ax.get_xlim()[1] > w[-1]
    assert ax.get_xlim()[1] - ax.get_xlim()[0] == pytest.approx((w[-1] - w[0]) * 1.05)
    np.testing.assert_equal(ax.lines[0].get_xdata(), w)
    plt.close(fig)
