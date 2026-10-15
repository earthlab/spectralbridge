"""Source labels, crosswalk integrity and plant-level PFT model inputs."""

import numpy as np
import pandas as pd
import pytest
from spectralbridge.plant_spectral_pfts import (
    load_pft_crosswalk,
    tag_pfts,
    _requests_for_pfts,
)
from spectralbridge.plant_spectral_quantiles import QuantileModelConfig
from spectralbridge.mesma_readiness import _folds, _pool, ReadinessConfig
from spectralbridge.mixtures import grouped_identity_split, validate_holdout

pytestmark = pytest.mark.scientific


@pytest.mark.parametrize(
    "problem", ["fields", "duplicate", "blank", "source", "code", "mapping"]
)
def test_crosswalk_rejects_invalid_or_unprovenanced_assignments(tmp_path, problem):
    crosswalk = load_pft_crosswalk().copy()
    if problem == "fields":
        crosswalk = crosswalk.drop(columns="source_url")
    elif problem == "duplicate":
        crosswalk = pd.concat([crosswalk, crosswalk.iloc[:1]], ignore_index=True)
    elif problem == "blank":
        crosswalk.loc[0, "species"] = "  "
    else:
        assigned = crosswalk.index[crosswalk.pft.ne("Unassigned")]
        if problem == "source":
            crosswalk.loc[assigned[0], "source_url"] = ""
        elif problem == "code":
            crosswalk.loc[assigned[0], "pft_code"] = ""
        else:
            crosswalk.loc[assigned[0], "pft_code"] = "CONFLICTING_CODE"
    path = tmp_path / "bad.csv"
    crosswalk.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_pft_crosswalk(path)


def test_taxon_normalization_preserves_source_names_and_unassigned_metadata():
    source = pd.DataFrame(
        {
            "GlobalID": ["a", "a", "b", "c"],
            "species": [" Abies   grandis ", " Abies   grandis ", None, "unknown"],
            "year": [2020, 2023, 2023, 2023],
            "cover_category": ["Evergreen"] * 4,
        }
    )
    tagged = tag_pfts(source, load_pft_crosswalk())
    pd.testing.assert_frame_equal(tagged[source.columns], source)
    assert tagged.pft_code.tolist() == ["ECT", "ECT", "UNASSIGNED", "UNASSIGNED"]
    with pytest.raises(ValueError):
        tag_pfts(tagged, load_pft_crosswalk())
    with pytest.raises(ValueError):
        tag_pfts(source, pd.concat([load_pft_crosswalk()] * 2))


def test_pft_quantile_inputs_are_individual_plants_and_train_partition_only():
    plants = pd.DataFrame(
        {
            "GlobalID": ["a", "b", "c", "d"],
            "species": ["taxon1", "taxon1", "taxon2", "taxon2"],
            "pft": ["PFT"] * 4,
            "pft_code": ["X"] * 4,
            "region": ["NIWO"] * 4,
            "source_position": range(4),
        }
    )
    values = np.array([[1, 2], [3, 4], [10, 20], [30, 40]], float)
    years = plants.assign(
        site="NIWO", year=2023, corr_wl400nm=values[:, 0], corr_wl405nm=values[:, 1]
    )
    cohort = pd.DataFrame(
        {
            "GlobalID": ["a", "b", "c", "d"],
            "partition": ["train", "test", "train", "test"],
        }
    )
    requests, counts = _requests_for_pfts(
        plants,
        {"corr": (np.array([400, 405]), values)},
        {"corr": years},
        {"corr": ["corr_wl400nm", "corr_wl405nm"]},
        cohort,
        QuantileModelConfig(stages=("corr",), min_plants_per_species=2),
    )
    training = [r for r in requests if r[0]["partition"] == "train"]
    assert training
    for metadata, _, spectra in training:
        assert (
            metadata["independent_plants"] == 2 and metadata["contributing_taxa"] == 2
        )
        np.testing.assert_array_equal(spectra, values[[0, 2]])
    full = [r for r in requests if r[0]["partition"] == "full"]
    assert all(len(r[2]) == 4 for r in full)
    assert counts.plants.eq(4).all()


@pytest.mark.parametrize("kind", ["plant", "site", "flight"])
def test_actual_readiness_folds_and_candidate_pool_respect_global_identity(kind):
    table = pd.DataFrame(
        [
            dict(GlobalID="a", label="X", site="S1", year=2020, flights=("f0",)),
            dict(GlobalID="a", label="X", site="S1", year=2023, flights=("f1",)),
            dict(GlobalID="b", label="Y", site="S1", year=2023, flights=("f1",)),
            dict(GlobalID="c", label="X", site="S2", year=2023, flights=("f2",)),
            dict(GlobalID="d", label="Y", site="S2", year=2023, flights=("f2",)),
        ]
    )
    config = ReadinessConfig(plant_folds=2, candidate_per_class=2)
    folds = [r for r in _folds(table, "test", config) if r[1] == kind]
    assert folds
    for _, _, test in folds:
        train, test = grouped_identity_split(table.GlobalID, test)
        pool = _pool(table, train, config, np.random.default_rng(3))
        validate_holdout(table.GlobalID, train, test, pool)
        assert set(table.iloc[pool].GlobalID).isdisjoint(table.loc[test].GlobalID)
        if kind == "site":
            assert set(table.iloc[pool].site).isdisjoint(table.loc[test].site)
        if kind == "flight":
            assert set(table.iloc[pool].flights.explode()).isdisjoint(
                table.loc[test].flights.explode()
            )
        if not test.any():
            continue  # A singleton label/site stratum can leave a fold empty.
        corrupted = train.copy()
        corrupted[np.flatnonzero(test)[0]] = True
        with pytest.raises(ValueError, match="leakage"):
            validate_holdout(table.GlobalID, corrupted, test, pool)
