"""Numerical and format QA for the two source-specific manuscript figures."""
from pathlib import Path
import json
from xml.etree import ElementTree

import numpy as np
import pandas as pd
from PIL import Image

from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.pft_method_audit import wavelength_weights
from examples.publication_figures.figure_data import load_figure_data


def main():
    repo = Path(__file__).resolve().parents[2]
    evidence = repo / 'provenance/publication-figures/2026-10-14'
    out = repo / 'output/pdf/publication_figures'
    manifest = json.loads((evidence / 'figure_manifest.json').read_text())
    for path, expected in {**manifest['data_sources'], **manifest['code_hashes'], **manifest['output_hashes']}.items():
        assert _file_hash(repo / path) == expected, path
    d = load_figure_data(repo)
    table, y, w = d['table'], d['spectra']['NEON'], d['waves']['NEON']
    atlas = pd.read_csv(evidence / 'atlas_summary.csv')
    assert sum(atlas.groupby('cover_category').N.first()) == len(table)
    for cat, group in atlas.groupby('cover_category'):
        actual = np.quantile(y[table.cover_category.eq(cat)], [.25, .5, .75], axis=0)
        np.testing.assert_allclose(group[['q25', 'median', 'q75']].to_numpy().T, actual, rtol=1e-12)
    weights = wavelength_weights(w)
    centered = (y - y.mean(0)) * np.sqrt(weights)
    eigen = np.linalg.eigvalsh(np.cov(centered, rowvar=False))[::-1]
    np.testing.assert_allclose(d['variance'], eigen[:2] / eigen.sum(), rtol=1e-12)
    np.testing.assert_allclose(np.cov(d['scores'], rowvar=False), np.diag(eigen[:2]), atol=1e-6)
    scores = pd.read_csv(evidence / 'pca_scores.csv')
    assert len(scores) == len(table)
    assert scores[['site', 'year', 'GlobalID']].equals(table[['site', 'year', 'GlobalID']])
    np.testing.assert_allclose(scores[['PC1', 'PC2']], d['scores'], rtol=1e-10, atol=1e-10)
    representatives = pd.read_csv(evidence / 'representatives.csv')
    for row in representatives.itertuples():
        i = table.index[(table.GlobalID.eq(row.GlobalID)) & table.year.eq(row.year) & table.site.eq(row.site)][0]
        group = y[table.cover_category.eq(row.cover_category)]
        median = np.median(group, axis=0)
        distance = np.sum((group - median) ** 2 * weights, axis=1)
        np.testing.assert_allclose(np.sum((y[i] - median) ** 2 * weights), distance.min(), atol=1e-9)
    pd.testing.assert_frame_equal(pd.read_csv(evidence / 'plotted_effects.csv'), d['effects'].reset_index(drop=True))
    pd.testing.assert_frame_equal(pd.read_csv(evidence / 'plotted_localization.csv'), d['localization'])
    formats = []
    for path in sorted(out.rglob('*.png')):
        image = Image.open(path)
        assert min(image.info['dpi']) >= 300
        formats.append(dict(file=path.name, pixels=image.size, dpi=image.info['dpi']))
    assert Image.open(out / 'Figure_1_spectral_library.png').size == (2880, 2600)
    assert Image.open(out / 'Figure_2_ecological_information.png').size == (2880, 2660)
    for path in sorted(out.rglob('*.svg')):
        svg = ElementTree.parse(path).getroot()
        assert len(svg.findall('.//{http://www.w3.org/2000/svg}text')) > 10
    assert len(list(out.rglob('*.pdf'))) == 10
    assert len(list(out.rglob('*.svg'))) == 10
    assert len(list(out.rglob('*.png'))) == 11
    common = d['images']['common']
    residual = d['images']['undarkened'][4] - d['images']['actual'][4]
    result = dict(status='passed', upstream_owned_files_verified=d['upstream_verified'],
        counts=d['counts'], PCA_variance=d['variance'].tolist(),
        independent_PCA_covariance_check=True, all_exported_medians_IQRs_equal=True,
        representatives_observed_minimum_distance=True, all_canonical_effects_and_localization_equal=True,
        original_source_sha256=manifest['data_sources']['Aug_2026_all_polygons_merged_pixel_extraction.parquet'],
        NIR_residual_outside_display_limits=int(np.count_nonzero(common & (abs(residual) > .15))),
        RGB_pixels_display_clipped={k: int(np.count_nonzero(common & np.any((d['images'][k][[3, 2, 1]] < 0) | (d['images'][k][[3, 2, 1]] > .4), axis=0))) for k in ['actual', 'undarkened']},
        format_checks=formats)
    (evidence / 'numerical_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'format_checks'}, indent=2))


if __name__ == '__main__':
    main()
