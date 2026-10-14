"""Verified inputs and small deterministic descriptive calculations for figures.

No inference reruns, source copies, scaling guesses or exported pixel cache.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import pearsonr, spearmanr

from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.sensor_pft_transfer import OLI_CENTERS

CATEGORIES = ['Deciduous', 'Evergreen', 'Herbaceous', 'Non-vegetated & dead', 'Woody shrub']
COLORS = dict(zip(CATEGORIES, ['#D55E00', '#0072B2', '#009E73', '#777777', '#CC79A7']))
STYLES = dict(zip(CATEGORIES, ['-', '--', '-.', ':', (0, (5, 2, 1, 2))]))


def segments(w, max_gap=8):
    """Connected wavelength slices; never draw across atmospheric/missing bands."""
    w = np.asarray(w, float)
    if len(w) < 2 or not np.isfinite(w).all() or np.any(np.diff(w) <= 0):
        raise ValueError('Need sorted unique finite wavelengths')
    return np.split(np.arange(len(w)), np.flatnonzero(np.diff(w) > max_gap) + 1)


def weighted_pca(y, w):
    """Centered covariance PCA in disconnected wavelength quadrature, no scaling.

    Scores preserve all observations. Sign fixed by largest absolute loading.
    The variance denominator includes all singular values, not just displayed PCs.
    """
    y = np.asarray(y, float)
    weights = wavelength_weights(w)
    if y.ndim != 2 or y.shape[1] != len(weights) or len(y) < 2 or not np.isfinite(y).all():
        raise ValueError('PCA requires finite complete common-support spectra')
    centered = (y - y.mean(0)) * np.sqrt(weights)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    if not np.any(s > 0):
        raise ValueError('No spectral variance')
    signs = np.sign(vt[np.arange(len(vt)), np.argmax(np.abs(vt), axis=1)])
    scores = u[:, :2] * s[:2] * signs[:2]
    return scores, s[:2] ** 2 / np.sum(s ** 2), vt[:2] * signs[:2, None]


def representative_indices(table, y, w):
    """Observed curve nearest each category median in wavelength-weighted RMS.

    Exact distance ties broken by site/year/GlobalID, not input row order.
    """
    weights = wavelength_weights(w)
    y = np.asarray(y, float)
    if y.shape != (len(table), len(w)) or not np.isfinite(y).all():
        raise ValueError('Representative selection needs complete aligned data')
    chosen = {}
    for category, group in table.groupby('cover_category', sort=True):
        ix = group.index.to_numpy()
        distance = np.sum((y[ix] - np.median(y[ix], axis=0)) ** 2 * weights, axis=1)
        candidates = group.assign(_distance=distance, _index=ix)
        chosen[category] = int(candidates.sort_values(['_distance', 'site', 'year', 'GlobalID'])._index.iloc[0])
    return chosen


def verify_manifest(root, filename):
    root = Path(root)
    manifest = json.loads((root / filename).read_text())
    for name, expected in manifest['outputs'].items():
        if _file_hash(root / name) != expected:
            raise ValueError(f'Changed upstream output: {root / name}')
    return manifest


def load_figure_data(repo):
    repo = Path(repo)
    source = repo / 'Aug_2026_all_polygons_merged_pixel_extraction.parquet'
    sensor = repo / 'artifacts/plant_spectral_atlas/sensor_pft_transfer'
    audit = repo / 'artifacts/plant_spectral_atlas/pft_method_audit/empirical'
    real = repo / 'artifacts/real_landsat_validation/R10C_20210915'
    evidence = repo / 'provenance/sensor-pft-transfer/2026-10-14'
    pilot = repo / 'provenance/real-landsat-validation/2026-10-14'
    upstream = [verify_manifest(sensor, 'statistics_manifest.json'),
                verify_manifest(audit, 'audit_manifest.json'),
                verify_manifest(real, 'statistics_manifest.json')]
    source_hash = _file_hash(source)
    if source_hash != upstream[0]['identity']['source']:
        raise ValueError('Library does not match canonical sensor analysis')
    # Published evidence must reproduce the canonical owned tables exactly.
    evidence_manifest = json.loads((evidence / 'statistics_manifest.json').read_text())
    for name, expected in evidence_manifest['evidence_outputs'].items():
        if _file_hash(evidence / name) != expected:
            raise ValueError('Changed sensor evidence: ' + name)
    sensor_files = ['effect_retention.csv', 'neon_signed_contrasts.csv',
                    'cross_sensor_correlations.csv', 'retention_summary.csv']
    real_files = ['grid.json', 'flight_metrics.csv', 'band_metrics.csv', 'pixel_metrics.parquet']
    for folder, origin, names in [(evidence, sensor, sensor_files), (pilot, real, real_files)]:
        for name in names:
            if not (origin / name).exists() and name in evidence_manifest['evidence_outputs']:
                continue
            if _file_hash(folder / name) != _file_hash(origin / name):
                if name == 'cross_sensor_correlations.csv':
                    published = pd.read_csv(folder / name).query("sensors == 'NEON_vs_OLI'")
                    canonical = pd.read_csv(origin / name)
                    pd.testing.assert_frame_equal(published[canonical.columns].reset_index(drop=True), canonical)
                else:
                    raise ValueError(f'Evidence differs from canonical analysis: {name}')
    table, spectra, waves = load_compact_inputs(source, sensor / 'compact')
    if sorted(table.cover_category.unique()) != sorted(CATEGORIES):
        raise ValueError('Cover labels changed; audit palette and narrative')
    # Project metadata only; the original library is never copied or materialized.
    meta = pq.read_table(source, columns=['GlobalID', 'species']).to_pandas().drop_duplicates()
    if meta.duplicated('GlobalID').any():
        raise ValueError('Conflicting species metadata')
    counts = dict(pixel_rows=pq.ParquetFile(source).metadata.num_rows,
                  identities=len(meta), polygon_years=len(table),
                  species_identified=int(meta.species.notna().sum()),
                  species_missing=int(meta.species.isna().sum()),
                  sites=table.site.nunique(), years=table.year.nunique(),
                  cover_categories=table.cover_category.nunique())
    if set(meta.GlobalID) != set(table.GlobalID):
        raise ValueError('Compact library dropped identities')
    scores, variance, loadings = weighted_pca(spectra['NEON'], waves['NEON'])
    representatives = representative_indices(table, spectra['NEON'], waves['NEON'])
    effects = pd.read_csv(evidence / 'effect_retention.csv').query("scheme == 'inferred_pft'").copy()
    correlations = pd.read_csv(evidence / 'cross_sensor_correlations.csv').query("scheme == 'inferred_pft' and cohort == 'all'")
    retention = pd.read_csv(evidence / 'retention_summary.csv').query("scheme == 'inferred_pft'").iloc[0]
    np.testing.assert_allclose(pearsonr(effects.NEON_effect, effects.OLI_effect).statistic,
                               correlations.query("method == 'Pearson'").correlation.iloc[0], atol=1e-12)
    np.testing.assert_allclose(spearmanr(effects.NEON_effect, effects.OLI_effect).statistic,
                               correlations.query("method == 'Spearman'").correlation.iloc[0], atol=1e-12)
    assert int((effects.NEON_supported & effects.OLI_supported).sum()) == int(retention.retained)
    signed = pd.read_csv(evidence / 'neon_signed_contrasts.csv')
    envelopes = pd.read_csv(audit / 'envelopes.csv')
    local = []
    for a in ['DBS', 'DBT']:
        row = effects.query("cohort == 'NIWO-2023' and a == @a and b == 'ECT'").iloc[0]
        curve = signed[signed.test_id.eq(row.test_id)].sort_values('wavelength_nm').copy()
        env = envelopes[envelopes.test_id.eq(row.test_id.removeprefix('inferred_pft__'))].sort_values('wavelength_nm')
        np.testing.assert_array_equal(curve.wavelength_nm, env.wavelength_nm)
        np.testing.assert_allclose(curve.beta, env.observed_beta, rtol=1e-12, atol=1e-9)
        curve['excursion_family'] = env.excursion_family.to_numpy()
        local.append(curve)
    local = pd.concat(local, ignore_index=True)
    regions = pd.read_csv(evidence / 'neon_region_coverage.csv')
    for row in regions.drop_duplicates(['a', 'b', 'region_start_nm', 'region_end_nm']).itertuples():
        eligible = effects[effects.a.eq(row.a) & effects.b.eq(row.b)]
        fractions = []
        for item in eligible.itertuples():
            sub = envelopes[envelopes.test_id.eq(item.test_id.removeprefix('inferred_pft__'))]
            window = sub[sub.wavelength_nm.between(row.region_start_nm, row.region_end_nm)]
            fractions.append(window.excursion_family.mean())
        assert len(fractions) == row.cohorts
        np.testing.assert_allclose(min(fractions), row.minimum_fraction_family_excursions)

    with np.load(real / 'matched_grid.npz') as z:
        images = {k: z[k] for k in ['actual', 'undarkened', 'common']}
    pixel = pd.read_parquet(pilot / 'pixel_metrics.parquet')
    common = images['common']
    for i, band in enumerate(['coastal', 'blue', 'green', 'red', 'nir08', 'swir16', 'swir22']):
        for key, prefix in [('actual', 'real'), ('undarkened', 'undarkened')]:
            np.testing.assert_allclose(images[key][i][common], pixel[f'{prefix}_{band}'], atol=1e-12)
    flight = pd.read_csv(pilot / 'flight_metrics.csv').query("variant == 'undarkened'").iloc[0]
    metrics = pd.read_csv(pilot / 'band_metrics.csv').query("variant == 'undarkened'")
    assert common.sum() == len(pixel) == flight.N
    residual = images['undarkened'][:, common] - images['actual'][:, common]
    np.testing.assert_allclose(np.sqrt(np.mean(residual ** 2)), flight.pooled_seven_band_RMSE, rtol=1e-12)
    np.testing.assert_allclose(np.median(pixel.undarkened_spectral_angle_deg), flight.median_spectral_angle_deg)
    for i, row in enumerate(metrics.itertuples()):
        np.testing.assert_allclose(pearsonr(images['actual'][i, common], images['undarkened'][i, common]).statistic, row.Pearson_r, atol=1e-12)
    files = [source, sensor / 'statistics_manifest.json', audit / 'audit_manifest.json',
             real / 'statistics_manifest.json', sensor / 'compact/corr_polygon_year.parquet',
             sensor / 'compact/olioli_undarkened_polygon_year.parquet', audit / 'envelopes.csv',
             evidence / 'neon_region_coverage.csv', evidence / 'statistics_manifest.json', real / 'matched_grid.npz',
             repo / 'src/spectralbridge/data/landsat_band_parameters.json']
    files += [evidence / f for f in sensor_files] + [pilot / f for f in real_files]
    return dict(repo=repo, table=table, spectra=spectra, waves=waves, counts=counts,
                scores=scores, variance=variance, loadings=loadings, representatives=representatives,
                effects=effects, correlations=correlations, retention=retention,
                localization=local, images=images, flight=flight, metrics=metrics,
                grid=json.loads((pilot / 'grid.json').read_text()),
                sources={str(p.relative_to(repo)): _file_hash(p) for p in files},
                upstream_verified=sum(len(m['outputs']) for m in upstream), oli_centers=OLI_CENTERS)
