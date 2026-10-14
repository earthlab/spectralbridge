"""Build the two manuscript figures from verified local scientific outputs.

Run from repository root:
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \\
 .venv/bin/python -m examples.publication_figures.build_spectral_library_figures
"""
from pathlib import Path
import argparse
import json
import platform
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from spectralbridge.plant_spectral_atlas import _file_hash
from examples.publication_figures.figure_data import load_figure_data, CATEGORIES
from examples.publication_figures.figure_panels import (
    style, plot_spectral_atlas, plot_library_structure, plot_morphospace,
    plot_sensor_representation, plot_effect_matrix, plot_spectral_localization,
    plot_sensor_retention, plot_real_landsat_validation,
)

F1 = 'Figure_1_spectral_library'
F2 = 'Figure_2_ecological_information'
FUNCTIONS = [plot_spectral_atlas, plot_library_structure, plot_morphospace,
             plot_sensor_representation, plot_effect_matrix, plot_spectral_localization,
             plot_sensor_retention, plot_real_landsat_validation]


def save(fig, path):
    # Fixed authoring metadata / SVG hashsalt make reruns byte reproducible.
    date = datetime(2026, 10, 14, tzinfo=timezone.utc)
    for extension in ['pdf', 'png', 'svg']:
        metadata = ({'Creator': 'SpectralBridge reproducible publication figures',
                     'CreationDate': date, 'ModDate': date} if extension == 'pdf' else
                    {'Date': '2026-10-14'} if extension == 'svg' else None)
        fig.savefig(path.with_suffix('.' + extension), dpi=400, metadata=metadata)
    plt.close(fig)


def build_figure1(d, out):
    fig = plt.figure(figsize=(7.2, 6.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.3, 1], hspace=.52,
                         left=.095, right=.975, top=.94, bottom=.085)
    top = gs[0].subgridspec(1, 2, width_ratios=[2.5, 1], wspace=.34)
    bottom = gs[1].subgridspec(1, 2, wspace=.42)
    for fn, slot in zip(FUNCTIONS[:4], [top[0], top[1], bottom[0], bottom[1]]):
        fn(fig, slot, d)
    save(fig, out / F1)


def build_figure2(d, out):
    fig = plt.figure(figsize=(7.2, 6.65))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.25], height_ratios=[1, 1.3],
                         hspace=.52, wspace=.54, left=.115, right=.975, top=.94, bottom=.09)
    for fn, slot in zip(FUNCTIONS[4:], [gs[0, 0], gs[0, 1], gs[1, 0], gs[1, 1]]):
        fn(fig, slot, d)
    save(fig, out / F2)


def export_tables(d, evidence):
    table = d['table']
    keys = ['site', 'year', 'GlobalID', 'species', 'cover_category']
    pca = table[keys].copy()
    pca[['PC1', 'PC2']] = d['scores']
    pca.to_csv(evidence / 'pca_scores.csv', index=False)
    pd.DataFrame({'wavelength_nm': d['waves']['NEON'], 'PC1_weighted_loading': d['loadings'][0],
                  'PC2_weighted_loading': d['loadings'][1]}).to_csv(evidence / 'pca_loadings.csv', index=False)
    representative = table.loc[list(d['representatives'].values()), keys].copy()
    representative.to_csv(evidence / 'representatives.csv', index=False)
    atlas = []
    for cat in CATEGORIES:
        y = d['spectra']['NEON'][table.cover_category.eq(cat)]
        q = np.quantile(y, [.25, .5, .75], axis=0)
        atlas.append(pd.DataFrame({'cover_category': cat, 'wavelength_nm': d['waves']['NEON'],
                                  'N': len(y), 'q25': q[0], 'median': q[1], 'q75': q[2]}))
    pd.concat(atlas).to_csv(evidence / 'atlas_summary.csv', index=False)
    table.groupby(['site', 'year', 'cover_category']).agg(
        polygon_years=('GlobalID', 'size'), identities=('GlobalID', 'nunique')
    ).to_csv(evidence / 'sampling_counts.csv')
    d['effects'].to_csv(evidence / 'plotted_effects.csv', index=False)
    d['localization'].to_csv(evidence / 'plotted_localization.csv', index=False)


def write_captions(d, out):
    c = d['counts']
    reps = pd.read_csv(d['evidence'] / 'representatives.csv')
    f1 = f'''**Figure 1. An empirical polygon spectral library spans ecological groups and sensor representations.**
(A) Corrected NEON category medians and empirical 25–75% wavelength-wise intervals for all {c['polygon_years']:,} polygon/year spectra. Colors and line styles identify five researcher cover categories throughout A, C and D. Shaded vertical regions are excluded atmospheric domains (1340–1450 and 1790–2000 nm); curves do not bridge gaps. Values retain stored corrected reflectance units because absolute library scaling is unresolved.
(B) Observational hierarchy and verified counts: {c['identities']:,} polygon/plant identities, {c['pixel_rows']:,} source pixel records, {c['species_identified']:,} identities with species recorded and {c['species_missing']:,} without, across {c['sites']} sites and {c['years']} acquisition years. A polygon/year curve is the equal-observation median of polygon/flight spectra, themselves pixel medians. NIWO recurs across years; years are not independent plants.
(C) Centered, unscaled, wavelength-quadrature-weighted principal component analysis (PCA) on {len(d['waves']['NEON'])} common finite NEON coordinates; PC1/PC2 explain {d['variance'][0]*100:.1f}%/{d['variance'][1]*100:.1f}% of weighted spectral variance. Color denotes category; shape denotes site. All observations and extreme values are retained. PCA is descriptive and not a significance test.
(D) One observed curve nearest each category median under the same wavelength metric, with its paired undarkened synthetic Operational Land Imager (OLI) values (diamonds) at validated physical band centers (443, 482, 561.4, 654.6, 864.7, 1608.9 and 2200.7 nm). Examples are selected deterministically; full identities are in representatives.csv. These are NEON-derived sensor representations, not independent satellite measurements. Category overlap, unequal sampling and potential species/acquisition confounding preclude interpreting these views as classification or population accuracy.
'''
    assert len(reps) == len(CATEGORIES)
    (out / 'Figure_1_caption.md').write_text(f1)
    r, f, m = d['retention'], d['flight'], d['metrics']
    f2 = f'''**Figure 2. Conditional ecological spectral contrasts largely survive reduction to synthetic OLI, with a separate real-Landsat pilot agreement check.**
(A) Corrected NEON standardized root-mean-square (RMS) contrasts, sqrt(sum w(β/s)²), for all {len(d['effects'])} eligible inferred plant functional type (PFT) comparisons within four site/year cohorts matched on exact acquisition histories. D/E denote deciduous/evergreen; B/C denote broadleaf/conifer; S/T denote shrub/tree. These inferred PFTs differ from researcher cover categories. Dots denote Holm-adjusted synchronized maximum-plus-integrated nonparametric combination (NPC) p < 0.05 in the declared primary family; gray cells lack sufficient matched support. Exact polygon/year counts and p-values are in plotted_effects.csv.
(B) Signed block-centered standardized mean contrasts β/s for two previously examined strong comparisons at NIWO 2023. Thick segments exceed the canonical family-controlled simultaneous maximum null envelope (Bonferroni across 21 matched contrasts), not an effect confidence interval. OLI diamonds mark seven actual channel centers. Atmospheric domains remain disconnected; no pointwise uncertainty is promoted to simultaneous evidence.
(C) Paired NEON/OLI effects for the same 21 dependent contrast/cohort comparisons; marker shape and color encode support. {int(r.retained)}/{int(r.NEON_supported)} NEON-supported contrasts retain OLI support; NIWO 2023 DBS–DBT loses borderline support. NEON uses disconnected wavelength weights and OLI equal-channel weights: these effects and their ratios are representation-specific separation measures, not fractions of total ecological information or classification accuracy.
(D) One R10C acquisition pair: NEON 15 September 2021 and actual Landsat 8 Collection 2 Level-2 surface reflectance on 16 September. RGB uses red/green/blue, identical 0–0.4 stretch, full common extent, EPSG:32613 native 30 m cells and common validity mask (gray excluded). NIR is near-infrared; residual = synthetic minus real, colors bounded at ±0.15 with all values retained numerically. Metrics use all {int(f.N):,} accepted footprints ({int(f.spatial_blocks)} spatial blocks): pooled seven-band RMSE {f.pooled_seven_band_RMSE:.4f}, median spectral angle {f.median_spectral_angle_deg:.2f}°, bandwise r {m.Pearson_r.min():.2f}–{m.Pearson_r.max():.2f}. This separate flight is not a direct observation of the library polygons. The approximately {f.delta_time_hours:.1f} h lag is conditional on the legacy NEON UTC interpretation; one pilot and high correlation do not establish cross-site radiometric interchangeability, causal PFT mechanisms or mixture recoverability.
'''
    (out / 'Figure_2_caption.md').write_text(f2)


def write_manifest(d, out, evidence):
    source_groups = [
        ['compact/corr_polygon_year.parquet'], ['.parquet', 'compact/corr_polygon_year.parquet'],
        ['compact/corr_polygon_year.parquet'], ['compact/corr_polygon_year.parquet', 'compact/olioli_undarkened_polygon_year.parquet', 'landsat_band_parameters.json'],
        ['effect_retention.csv'], ['neon_signed_contrasts.csv', 'envelopes.csv', 'neon_region_coverage.csv', 'landsat_band_parameters.json'],
        ['effect_retention.csv', 'cross_sensor_correlations.csv', 'retention_summary.csv'],
        ['matched_grid.npz', 'grid.json', 'flight_metrics.csv', 'band_metrics.csv', 'pixel_metrics.parquet']]
    statistics = ['Median and empirical IQR', 'Exact counts', 'Centered wavelength-weighted PCA',
                  'Observed median-nearest representative and paired OLI', 'Standardized RMS beta/s, adjusted NPC support',
                  'Signed beta/s; family-controlled simultaneous null excursions',
                  'Paired standardized RMS effects; canonical Pearson/Spearman/support retention', 'Matched RGB/NIR signed residual; pooled RMSE, median angle, bandwise Pearson']
    panels = []
    for i, fn in enumerate(FUNCTIONS):
        fig, panel = (1 if i < 4 else 2), 'ABCD'[i % 4]
        names = [k for k in d['sources'] if any(k.endswith(x) for x in source_groups[i])]
        names += [k for k in d['sources'] if k.endswith('manifest.json')]
        names = sorted(set(names))
        n = d['counts'] if i == 1 else ({'polygon_years': len(d['table']), 'wavelengths': len(d['waves']['NEON'])} if i in [0, 2] else
             {'representatives': len(d['representatives']), 'OLI_bands': 7} if i == 3 else
             {'eligible_comparisons': len(d['effects']), 'counts_table': str((evidence / 'plotted_effects.csv').relative_to(d['repo']))} if i in [4, 6] else
             {'contrasts': 2, 'points_per_contrast': d['localization'].groupby('contrast').size().to_dict(), 'counts_table': str((evidence / 'plotted_effects.csv').relative_to(d['repo']))} if i == 5 else
             {'flight_pairs': 1, 'footprints': int(d['flight'].N), 'blocks': int(d['flight'].spatial_blocks)})
        panels.append(dict(figure=fig, panel=panel, source_files=names, source_hashes={k: d['sources'][k] for k in names},
            sample_unit='Polygon/year; repeated years not independent' if i < 7 else 'Actual 30 m Landsat footprint',
            sensor_representation='Corrected NEON / synthetic undarkened OLI' if i < 7 else 'Verified unitless SR; synthetic OLI versus actual Landsat C2 L2',
            filters='See predeclared FIGURE_SOURCE_AUDIT.md; all canonical eligible observations retained',
            statistic=statistics[i], N=n, code_function=fn.__module__ + '.' + fn.__name__,
            generated_file=[str((out / 'panels' / f'Figure_{fig}_{panel}.{ext}').relative_to(d['repo'])) for ext in ['pdf', 'png', 'svg']]))
    outputs = sorted(list(out.glob('*.*')) + list((out / 'panels').glob('*.*')) + list(evidence.glob('*.csv')))
    manifest = dict(status='complete', data_sources=d['sources'], panels=panels,
        source_audit='FIGURE_SOURCE_AUDIT.md', source_library_read_in_place=True,
        upstream_owned_files_verified=d['upstream_verified'],
        PCA=dict(N=len(d['table']), support=len(d['waves']['NEON']), explained_variance=d['variance'].tolist(), method='Centered unscaled wavelength-quadrature-weighted SVD; all singular values denominator'),
        runtime=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, matplotlib=matplotlib.__version__),
        code_hashes={str(p.relative_to(d['repo'])): _file_hash(p) for p in Path(__file__).parent.glob('*.py')},
        output_hashes={str(p.relative_to(d['repo'])): _file_hash(p) for p in outputs})
    (evidence / 'figure_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = repo / 'output/pdf/publication_figures'
    evidence = repo / 'provenance/publication-figures/2026-10-14'
    (out / 'panels').mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    print('Verifying canonical manifests and loading compact inputs', flush=True)
    d = load_figure_data(repo)
    d['evidence'] = evidence
    print('Verified', d['upstream_verified'], 'owned outputs;', d['counts'], 'PCA', d['variance'], flush=True)
    export_tables(d, evidence)
    style()
    build_figure1(d, out)
    build_figure2(d, out)
    for i, fn in enumerate(FUNCTIONS):
        fig = plt.figure(figsize=(4.1, 3.9))
        slot = fig.add_gridspec(1, 1, left=.2 if i == 4 else .18, right=.83 if i == 4 else .94, top=.88, bottom=.23)[0]
        fn(fig, slot, d)
        save(fig, out / 'panels' / f'Figure_{1 if i < 4 else 2}_{"ABCD"[i % 4]}')
    first, second = [Image.open(out / f'{name}.png').convert('RGB') for name in [F1, F2]]
    preview = Image.new('RGB', (first.width + second.width + 100, max(first.height, second.height)), 'white')
    preview.paste(first, (0, 0))
    preview.paste(second, (first.width + 100, 0))
    preview.save(out / 'combined_preview.png', dpi=(400, 400))
    write_captions(d, out)
    write_manifest(d, out, evidence)
    print('Figures and tables written:', out, flush=True)


if __name__ == '__main__':
    main()
