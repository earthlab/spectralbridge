from itertools import product

import numpy as np
import pandas as pd
import pytest

from spectralbridge.plant_pft_statistics import (
    PFTStatisticsConfig, _history_keys, contrast, holm, permute_within,
)
from spectralbridge.plant_spectral_pfts import load_pft_crosswalk, tag_pfts


def test_holm_monotonic_original_order_and_dependent_family():
    np.testing.assert_allclose(holm([.03, .001, .2, .02]), [.06, .004, .2, .06])
    np.testing.assert_allclose(holm([]), [])
    with pytest.raises(ValueError):
        holm([np.nan])


def test_label_permutations_preserve_counts_and_band_alignment():
    z = np.array([0, 1, 1, 0, 0, 1])
    b = np.array([0, 0, 0, 1, 1, 2])
    shuffled = permute_within(z, b, np.random.default_rng(3))
    for block in np.unique(b):
        assert shuffled[b == block].sum() == z[b == block].sum()
    assert shuffled[-1] == z[-1]


def test_block_confounding_disappears_and_gaps_and_negatives_retained():
    # Identical within each block, huge site shift and unequal PFT proportions.
    y = np.array([-100.] * 6 + [1000.] * 6)
    z = np.array([0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1])
    b = np.repeat([0, 1], 6)
    # Some variation shared equally by the PFTs within blocks.
    y += np.array([0, 0, 0, 0, 0, 0, -1, -1, 0, 0, 0, 1])
    x = np.column_stack([y, y, np.full(12, np.nan), np.ones(12)])
    result = contrast(x, z, b, permutations=99, bootstraps=39, seed=9)
    np.testing.assert_array_equal(result['columns'], [0, 1])
    assert result['p'] > .05
    assert len(result['rows']) == 12
    np.testing.assert_allclose(result['beta'][0], result['beta'][1])


def test_known_separation_direction_multiplicity_and_restart_determinism():
    z = np.repeat([0, 1], 20)
    b = np.zeros(40)
    rng = np.random.default_rng(3)
    y = rng.normal(0, .1, (40, 3)) + z[:, None] * [3, -3, 0]
    result = contrast(y, z, b, permutations=999, bootstraps=49, seed=4)
    repeated = contrast(y, z, b, permutations=999, bootstraps=49, seed=4)
    assert result['p'] <= .01
    assert result['beta'][0] > 0 and result['beta'][1] < 0
    assert result['p_band'][2] > .05
    np.testing.assert_array_equal(result['p_band'], repeated['p_band'])
    assert result['p'] >= 1 / 1000
    np.testing.assert_allclose(result['beta'], y[z == 1].mean(0) - y[z == 0].mean(0))


def test_mixed_overlap_only_and_no_false_replicates():
    z = np.array([0, 1, 0, 1, 0, 0])
    b = np.array([0, 0, 0, 0, 1, 1])
    r = contrast(np.arange(12).reshape(6, 2), z, b, permutations=39, bootstraps=39, seed=3)
    np.testing.assert_array_equal(r['rows'], [0, 1, 2, 3])
    assert r['mixed_blocks'] == 1
    with pytest.raises(ValueError, match='No within-block'):
        contrast(np.arange(8).reshape(4, 2), [0, 0, 1, 1], [0, 0, 1, 1], permutations=39, bootstraps=39, seed=3)


def test_flight_history_keys_ignore_local_polygon_numbers():
    records = []
    for plant, flight in product(['a', 'b'], ['f1', 'f2']):
        records.append(dict(GlobalID=plant, year=2023, flight_id=flight,
                            source_image=flight + '.img', polygon_id=plant))
    keys = _history_keys(pd.DataFrame(records))
    assert keys.loc[('a', 2023)] == keys.loc[('b', 2023)]


def test_tags_are_auditable_do_not_assign_unresolved_or_duplicate_plants():
    d = pd.DataFrame({'GlobalID': ['a', 'b', 'c'], 'species': ['Abies', 'Abies grandis', 'Missing taxon']})
    out = tag_pfts(d, load_pft_crosswalk())
    assert out.GlobalID.tolist() == d.GlobalID.tolist()
    assert out.pft_code.tolist() == ['UNASSIGNED', 'ECT', 'UNASSIGNED']


def test_config_excludes_unverified_physical_micasense_inference():
    with pytest.raises(ValueError, match='MicaSense'):
        PFTStatisticsConfig(stages=('micasense',)).validate()


def test_monte_carlo_matches_small_exact_two_sided_randomization():
    # There are six allocations of two labels; two are as extreme as observed.
    result = contrast(np.array([-1., 0., 2., 3.])[:, None], [0, 0, 1, 1],
                      [0, 0, 0, 0], permutations=9999, bootstraps=19, seed=123)
    assert abs(result['p'] - 2 / 6) < .02


def test_pipeline_checkpoint_reuse_and_tamper_rejection(tmp_path, monkeypatch):
    import json
    import spectralbridge.plant_pft_statistics as module
    name = 'NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance'
    records = []
    for i, species in enumerate(['Abies grandis'] * 3 + ['Alnus rubra'] * 3):
        records.append(dict(GlobalID=str(i), species=species, flight_id=name,
                            source_image=name + '.img', source_parquet=name + '_polygons_merged_pixel_extraction.parquet',
                            polygon_id=i, corr_wl450nm=float(i), corr_wl550nm=-float(i),
                            corr_wl700nm=float(i)**2))
    obs = pd.DataFrame(records)
    monkeypatch.setattr(module, '_model_inputs', lambda _: (
        None, None, {'corr': (obs, [])}, {}, {'source': 'synthetic-source'}))
    monkeypatch.setattr(module, '_plot_summary', lambda *_: None)
    monkeypatch.setattr(module, '_plot_effects', lambda *_: None)
    config = PFTStatisticsConfig(stages=('corr',), permutations=39, bootstraps=39, min_plants=2)
    out = tmp_path / 'statistics'
    result = module.run_pft_statistics(tmp_path, out, config=config)
    assert len(result) == 2 and result.status.eq('tested').all()
    assert len(pd.read_parquet(out / 'test_membership.parquet')) == 12
    checkpoint = next((out / 'checkpoints').glob('*.json'))
    before = checkpoint.stat().st_mtime_ns
    module.run_pft_statistics(tmp_path, out, config=config)
    assert checkpoint.stat().st_mtime_ns == before
    saved = json.loads(checkpoint.read_text())
    saved['result']['p'] = .123
    checkpoint.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='checksum mismatch'):
        module.run_pft_statistics(tmp_path, out, config=config)


def test_rank_sensitivity_is_invariant_to_monotone_amplitude_change():
    rng = np.random.default_rng(33)
    y = rng.normal(size=(30, 2))
    z = np.tile([0, 1], 15)
    blocks = np.repeat([0, 1, 2], 10)
    a = contrast(y, z, blocks, permutations=199, bootstraps=19, seed=71)
    b = contrast(np.exp(y), z, blocks, permutations=199, bootstraps=19, seed=71)
    assert a['p_rank'] == b['p_rank']
