"""Run fixed-library exhaustive benchmark without modifying the preceding packet."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np
import pandas as pd
from stream_mesma import search

OUT = Path(__file__).resolve().parent
PREVIOUS = OUT.parent / 'v1'
ROOT = OUT.parents[3]


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def load_targets():
    old = json.loads((PREVIOUS/'summary.json').read_text())
    for path, expected in old['input_sha256'].items():
        assert sha(path) == expected
    tables = PREVIOUS/'tables'
    members = pd.read_csv(tables/'selected_members.csv', float_precision='round_trip')
    primary = pd.read_csv(tables/'selected_synthetic_predictions.csv', float_precision='round_trip').sort_values('target')
    truth = primary[[f'truth_{j}' for j in range(1, 6)]].to_numpy()
    # Use archived source identity + original NPY spectra, as in independent P136 replay.
    source = pd.read_parquet(ROOT/'Aug_2026_all_polygons_merged_pixel_extraction.parquet',
                             columns=['GlobalID', 'cover_category', 'flight_id'])
    source['site'] = source.flight_id.str.extract(r'_([A-Z]{4})_DP1')[0]
    source['year'] = source.flight_id.str.extract(r'_(\d{8})_')[0].str[:4].astype(int)
    x = np.load('/Users/tuff/Downloads/library_oli_undarkened_10_12_26.npy', allow_pickle=False).T
    bands = [f'band_{i}' for i in range(7)]
    source[bands] = x
    parent = source.groupby(['GlobalID', 'cover_category', 'site', 'year', 'flight_id'])[bands].median()
    parent = parent.groupby(level=['GlobalID', 'cover_category', 'site', 'year']).median().reset_index()
    lookup = parent.set_index(['GlobalID', 'site', 'year'])
    targets = []
    used = set()
    for _, group in primary.groupby('bundle'):
        ids = group.parent_ids.iloc[0].split('|')
        assert set(ids).isdisjoint(used) and set(ids).isdisjoint(set(members.GlobalID))
        used.update(ids)
    for i, row in enumerate(primary.itertuples()):
        refs = np.array([lookup.loc[(j, row.site, row.year), bands].to_numpy(float)
                         for j in row.parent_ids.split('|')])
        targets.append(truth[i] @ refs)
    targets = np.asarray(targets)
    e = x[members.array_index.to_numpy()]
    codes = members.class_code.to_numpy()
    return targets, truth, e, codes, primary, members


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    started = time.time()
    y, truth, e, labels, primary, members = load_targets()
    prior_paths = sorted(p for p in PREVIOUS.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in prior_paths}
    (OUT/'previous_packet_hashes.json').write_text(json.dumps(preserved, indent=2)+'\n')
    # Twelve prespecified targets: pure, pair and triple in every observed domain.
    pilot = np.array([b*45+j for b in (0, 2, 4, 6) for j in (0, 30, 40)])
    use = pilot if args.pilot else np.arange(len(y))
    mode = 'pilot' if args.pilot else 'full'
    result = search(y[use], e, labels, directory=OUT/(mode+'_checkpoints'), chunk_models=1024)
    with (OUT/(mode+'_results.npz')).open('wb') as f:
        np.savez_compressed(f, **result, target_ids=use, targets=y[use], truth=truth[use])
    metadata = dict(mode=mode, targets=len(use), model_count=result['model_count'],
                    target_model_evaluations=len(use)*result['model_count'],
                    search_seconds=result['seconds'], elapsed_seconds=time.time()-started,
                    source_parquet_sha256=sha(ROOT/'Aug_2026_all_polygons_merged_pixel_extraction.parquet'),
                    previous_summary_sha256=sha(PREVIOUS/'summary.json'),
                    input_sha256=json.loads((PREVIOUS/'summary.json').read_text())['input_sha256'],
                    source_code_sha256={p.name: sha(p) for p in [Path(__file__), OUT/'stream_mesma.py']},
                    selection_blind=False, max_components=3, one_reference_per_category=True,
                    same_targets_as_P136=True,
                    near_set_warning='One best interior per class set; not all near-optimal fractions')
    if not args.pilot:
        record = primary.drop(columns=[c for c in primary if c.startswith('prediction_') or c in ('fraction_RMSE', 'method')]).copy()
        record['method'] = 'Exhaustive selected MESMA'
        for j in range(5):
            record[f'prediction_{j+1}'] = result['fractions'][:, j]
        record['fraction_RMSE'] = np.sqrt(np.mean((result['fractions']-truth)**2, axis=1))
        record['spectral_RMSE'] = result['direct_RMSE']
        record['complexity'] = result['complexity']
        for j in range(3):
            ix = result['model_indices'][:, j]
            record[f'array_index_{j+1}'] = np.where(ix >= 0, members.array_index.to_numpy()[np.maximum(ix, 0)], -1)
            record[f'member_fraction_{j+1}'] = result['member_fractions'][:, j]
        record.to_csv(OUT/'exhaustive_predictions.csv', index=False)
        for tolerance in (.001, .005, .01):
            near = result['composition_errors'] <= result['RMSE'][:, None] + tolerance
            record[f'near_class_sets_{tolerance}'] = near.sum(1)
        record.to_csv(OUT/'exhaustive_predictions.csv', index=False)
        metadata['fraction_RMSE'] = float(np.sqrt(np.mean((result['fractions']-truth)**2)))
        metadata['mean_spectral_RMSE'] = float(result['direct_RMSE'].mean())
    assert all(sha(ROOT/p) == h for p, h in preserved.items())
    (OUT/(mode+'_summary.json')).write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == '__main__':
    main()
