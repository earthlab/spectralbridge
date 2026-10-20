"""Year separation preserves independent identities and source acquisition dates."""

import numpy as np
import pandas as pd
import pytest
from spectralbridge.plant_spectral_years import _acquisition_group, _year_plant_spectra


def observations():
    rows = []
    for plant, year, flight, value in [
        ("A", 2020, "001", 2),
        ("A", 2020, "002", 8),
        ("A", 2023, "001", 20),
        ("B", 2020, "001", 10),
    ]:
        name = f"NEON_D13_NIWO_DP1_L{flight}-1_{year}0815_directional_reflectance"
        rows.append(
            {
                "GlobalID": plant,
                "species": "Test species",
                "flight_id": name,
                "source_image": name + ".img",
                "polygon_id": 1,
                "source_parquet": "/wrong_WREF_1999/"
                + name
                + "_polygons_merged_pixel_extraction.parquet",
                "aop_site": "NIWO",
                "corr_wl400nm": value,
                "corr_wl405nm": -value,
                "corr_wl1400nm": np.nan,
                "pixel_count": 100 if value == 2 else 1,
            }
        )
    return pd.DataFrame(rows)


def test_source_basename_gives_acquisition_year_not_folder_or_field_year():
    name = "/2020/WREF/NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance_polygons.parquet"
    assert _acquisition_group(name) == ("NIWO", 2023)
    assert _acquisition_group(
        "NEON_D13_NIWO_DP1_20200807_155314_reflectance_polygons.parquet"
    ) == ("NIWO", 2020)
    with pytest.raises(ValueError):
        _acquisition_group(name.replace("20230815", "20230231"))


def test_plant_medians_are_separate_by_year_and_ignore_pixel_counts():
    table, columns, _ = _year_plant_spectra(observations(), "corr")
    a = table[table.GlobalID == "A"].set_index("year")
    assert a.loc[2020, "corr_wl400nm"] == 5
    assert a.loc[2023, "corr_wl400nm"] == 20
    assert a.loc[2020, "corr_wl405nm"] == -5
    assert a.flight_observations.to_dict() == {2020: 2, 2023: 1}
    assert table[columns[-1]].isna().all()
    assert len(table) == 3


def test_conflicting_source_flight_year_and_duplicate_observations_rejected():
    d = observations()
    d.loc[0, "source_parquet"] = d.loc[0, "source_parquet"].replace(
        "20200815", "20210815"
    )
    with pytest.raises(ValueError, match="disagree"):
        _year_plant_spectra(d, "corr")
    d = observations()
    with pytest.raises(ValueError, match="Duplicate"):
        _year_plant_spectra(pd.concat([d, d.iloc[:1]], ignore_index=True), "corr")


def test_year_site_panels_refit_correct_cohorts_and_mark_missing_acquisitions(
    tmp_path, monkeypatch
):
    pytest.importorskip("xgboost", reason="optional quantile-models extra")
    import spectralbridge.plant_spectral_years as module
    from spectralbridge.plant_spectral_quantiles import QuantileModelConfig
    import matplotlib.pyplot as plt

    d = observations()
    extra = d[d.GlobalID == "B"].copy()
    extra["GlobalID"] = "C"
    extra["aop_site"] = "WREF"
    for col in ["flight_id", "source_image", "source_parquet"]:
        extra[col] = (
            extra[col].str.replace("NIWO", "WREF").str.replace("20200815", "20230815")
        )
    second = extra.copy()
    second["GlobalID"] = "D"
    repeat = d[d.GlobalID == "B"].copy()
    for col in ["flight_id", "source_image", "source_parquet"]:
        repeat[col] = repeat[col].str.replace("20200815", "20230815")
    d = pd.concat([d, extra, second, repeat], ignore_index=True)
    monkeypatch.setattr(
        module,
        "_model_inputs",
        lambda root: (None, None, {"corr": (d, [])}, None, {"synthetic": "hash"}),
    )
    captured = []

    def save(fig, *args):
        captured.append(fig)

    monkeypatch.setattr(module, "_save", save)
    config = QuantileModelConfig(
        stages=("corr",), workers=1, boosting_rounds=2, min_plants_per_species=2
    )
    result = module.run_year_site_quantiles(tmp_path, tmp_path / "out", config=config)
    assert result["models"] == 3
    assert result["plants_observed_multiple_years"] == 2
    plants = pd.read_parquet(tmp_path / "out" / "plant_year_site_cohorts.parquet")
    assert len(plants) == 6
    assert [a.get_title() for a in captured[0].axes] == [
        "2020 · NIWO",
        "2020 · WREF",
        "2023 · NIWO",
        "2023 · WREF",
    ]
    assert any(t.get_text() == "No acquisition" for t in captured[0].axes[1].texts)
    paths = list((tmp_path / "out" / "checkpoints").glob("*.npz"))
    before = {p.name: p.stat().st_mtime_ns for p in paths}
    module.run_year_site_quantiles(tmp_path, tmp_path / "out", config=config)
    assert before == {p.name: p.stat().st_mtime_ns for p in paths}
    for fig in captured:
        plt.close(fig)
