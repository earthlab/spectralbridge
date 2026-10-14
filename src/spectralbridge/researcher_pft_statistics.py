"""Researcher cover-category adapter for existing whole-spectrum inference."""
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
import json
import logging
import platform
import scipy

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .plant_spectral_atlas import run_plant_spectral_atlas, _file_hash
from .plant_spectral_years import _year_plant_spectra
from .plant_pft_statistics import _history_keys, _seed, _write_json, holm
from .pft_method_audit import (
    AuditConfig, METHODS, method_statistics, envelope_critical, _plot_envelopes,
)

LOG = logging.getLogger(__name__)


def category_metadata(source):
    """Validate labels without requiring taxonomic identification."""
    frame = pq.read_table(source, columns=['GlobalID', 'cover_category', 'species']).to_pandas()
    if frame[['GlobalID', 'cover_category']].isna().any().any():
        raise ValueError('Missing researcher category or polygon identity')
    if frame.cover_category.astype(str).str.strip().eq('').any():
        raise ValueError('Empty researcher category')
    if frame.groupby('GlobalID').cover_category.nunique().gt(1).any():
        raise ValueError('Conflicting researcher categories for a polygon identity')
    return frame.drop_duplicates().sort_values(['GlobalID', 'cover_category'])


def run_researcher_statistics(source, output, *, config=None, minimum=10):
    """Corrected NEON; exact acquisition history primary, site/year sensitivity.

    Groups are cover_category verbatim. Repeated observations are reduced to a
    polygon/year median; years are tested separately, never pooled as replicates.
    """
    config = config or AuditConfig()
    config.validate()
    if minimum < 2:
        raise ValueError('Minimum group support must be at least two')
    source, root = Path(source), Path(output)
    root.mkdir(parents=True, exist_ok=True)
    metadata = category_metadata(source)
    compact = root / 'compact'
    run_plant_spectral_atlas(source, compact, species_field='cover_category', make_figures=False)
    identity = {'source': _file_hash(source), 'compact': _file_hash(compact/'manifest.json'),
                'config': asdict(config), 'minimum': minimum,
                'code': _file_hash(__file__),
                'methods': _file_hash(Path(__file__).with_name('pft_method_audit.py')),
                'years': _file_hash(Path(__file__).with_name('plant_spectral_years.py')),
                'helpers': _file_hash(Path(__file__).with_name('plant_pft_statistics.py')),
                'numpy': np.__version__, 'pandas': pd.__version__,
                'scipy': scipy.__version__, 'python': platform.python_version()}
    manifest_path = root/'manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old['identity'] == identity and all((root/n).is_file() and _file_hash(root/n)==h for n,h in old['outputs'].items()):
            return pd.read_csv(root/'method_comparison.csv')
    observations = pd.read_parquet(compact/'plant_flight_spectra.parquet')
    # Existing reducer's internal species slot carries the explicit researcher
    # class only; original taxonomic labels are retained separately below.
    observations = observations.rename(columns={'cover_category': 'species'})
    table, columns, original = _year_plant_spectra(observations, 'corr')
    table = table.join(_history_keys(original), on=['GlobalID', 'year'])
    table = table.rename(columns={'species': 'cover_category'})
    table.to_parquet(root/'polygon_year_spectra.parquet', index=False)
    metadata.to_csv(root/'researcher_labels_and_species.csv', index=False)
    table.groupby(['site','year','cover_category']).agg(polygons=('GlobalID','nunique'), observations=('flight_observations','sum')).to_csv(root/'support.csv')
    w = np.array([float(c.split('_wl')[1][:-2]) for c in columns])
    summaries, records, memberships = [], {}, []
    checkpoints = root/'checkpoints'
    checkpoints.mkdir(exist_ok=True)
    for (site, year), cohort in table.groupby(['site', 'year'], sort=True):
        for pair_index, (a,b) in enumerate(combinations(sorted(table.cover_category.unique()),2)):
            for blocking in ['flight_history', 'site_year']:
                test_id = f'{site}_{year}_{pair_index}_{blocking}'
                pair = cohort[cohort.cover_category.isin([a,b])].sort_values('GlobalID').reset_index(drop=True)
                blocks = pd.factorize(pair.flight_history)[0] if blocking=='flight_history' else np.zeros(len(pair),int)
                z = pair.cover_category.eq(a).to_numpy(int)
                mixed = [v for v in np.unique(blocks) if len(np.unique(z[blocks==v]))==2]
                keep = np.isin(blocks,mixed)
                n_a, n_b = int(z[keep].sum()), int((1-z[keep]).sum())
                rec = dict(test_id=test_id,cohort=f'{site} {year}',site=site,year=year,a=a,b=b,pair=f'{a} / {b}',blocking=blocking,n_a=n_a,n_b=n_b,blocks=len(mixed),status='insufficient_support')
                if min(n_a,n_b)<minimum:
                    summaries.append(rec)
                    continue
                LOG.info('%s: %s vs %s; polygons %s/%s',test_id,a,b,n_a,n_b)
                path = checkpoints/(test_id+'.npz')
                ledger = path.with_suffix('.json')
                saved = json.loads(ledger.read_text()) if ledger.exists() else {}
                if saved.get('identity')==identity:
                    if not path.exists() or _file_hash(path)!=saved['sha256']:
                        raise ValueError('Checkpoint checksum mismatch')
                    with np.load(path) as archive:
                        result = {k: archive[k] for k in archive.files}
                    result['p'] = saved['p']
                else:
                    result = method_statistics(pair[columns].to_numpy(float),z,blocks,w,config=config,seed=_seed(config,test_id))
                    result['curves'] = result['curves'][:1].copy()
                    temp = path.with_suffix('.tmp.npz')
                    np.savez_compressed(temp,**{k:v for k,v in result.items() if k!='p'})
                    temp.replace(path)
                    _write_json(ledger,dict(identity=identity,sha256=_file_hash(path),p=result['p']))
                rec.update(status='tested',bands=len(result['columns']),pcs=int(result['pcs']),pc_variance_retained=float(result['pc_variance_retained']))
                rec.update({'p_'+k:v for k,v in result['p'].items()})
                actual = pair.iloc[result['rows']].copy()
                actual['test_id'] = test_id
                memberships.append(actual[['test_id','GlobalID','cover_category','site','year','flight_history']])
                records[test_id] = (result,w[result['columns']])
                summaries.append(rec)
    if not memberships:
        raise ValueError('No class contrasts meet minimum mixed-block support')
    summary = pd.DataFrame(summaries)
    for blocking in ['flight_history','site_year']:
        use = summary.status.eq('tested') & summary.blocking.eq(blocking)
        for method in METHODS:
            summary.loc[use,'p_'+method+'_holm'] = holm(summary.loc[use,'p_'+method])
    summary.to_csv(root/'method_comparison.csv',index=False)
    pd.concat(memberships,ignore_index=True).to_parquet(root/'membership.parquet',index=False)
    envelopes=[]
    for row in summary[summary.status.eq('tested')].itertuples():
        result,ww = records[row.test_id]
        family = int((summary.status.eq('tested') & summary.blocking.eq(row.blocking)).sum())
        for alpha,label in [(.05,'within_contrast'),(.05/family,'family')]:
            c = envelope_critical(result['stats'][1:,0],alpha)
            for j,wave in enumerate(ww):
                envelopes.append(dict(test_id=row.test_id,scope=label,wavelength_nm=wave,beta=result['curves'][0,j],lower=-c*result['se'][j],upper=c*result['se'][j],excursion=abs(result['curves'][0,j])>c*result['se'][j]))
    pd.DataFrame(envelopes).to_csv(root/'envelopes.csv',index=False)
    family = int((summary.status.eq('tested') & summary.blocking.eq('flight_history')).sum())
    if family:
        _plot_envelopes(root,summary,records,family)
    lines=['# Researcher-defined category spectral differences','',
           'Source field: `cover_category`, preserved verbatim. Corrected NEON only. Pixel medians per polygon/acquisition, then equally weighted observation medians per polygon/year. No species-name filtering. Non-vegetated & dead is a cover comparator, not a biological PFT.','',
           f'{table.GlobalID.nunique()} unique polygon identities; {len(table)} polygon/year spectra. Minimum {minimum} polygons per class across mixed blocks. {config.permutations:,} joint whole-curve label permutations per contrast.', '',
           'Primary: synchronized max + integrated NPC; Holm across all eligible exact-flight-history contrasts. Site/year-only blocks are a separate sensitivity family. Energy and label-blind FPCA are sensitivity methods, not extra chances to declare a result. Max envelopes localize departures from the exchangeability null; they are not confidence intervals for an effect.', '',
           '## Primary results','', '| Cohort | Classes (A / B) | n A / B | NPC adjusted p | Max | Energy | FPCA |','|---|---|---:|---:|---:|---:|---:|']
    for row in summary[(summary.status=='tested')&(summary.blocking=='flight_history')].itertuples():
        lines.append(f'| {row.cohort} | {row.pair} | {row.n_a}/{row.n_b} | {row.p_npc_holm:.4g} | {row.p_max_holm:.4g} | {row.p_energy_holm:.4g} | {row.p_fpca_holm:.4g} |')
    lines += ['', '## Interpretation limits','', 'These are conditional differences among sampled polygon mixtures. Spatial correlation, composition, mixed cover, dead material and observational label exchangeability remain limitations. Nonsignificance does not establish equivalence; significance does not measure classification accuracy or a universal PFT mechanism. Separate years can reuse identities and are not independent replications. Exact-history matching changes the target population. Synthetic sensor products are not independent observations. Generic method simulations from P117 support mechanics under their stated nulls, not validation of this new sample or exchangeability. See support.csv, researcher_labels_and_species.csv and membership.parquet for composition and provenance.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    if _file_hash(source)!=identity['source']:
        raise ValueError('Source changed during analysis')
    outputs={str(p.relative_to(root)):_file_hash(p) for p in root.rglob('*') if p.is_file() and p!=manifest_path and 'interpretation' not in p.relative_to(root).parts}
    _write_json(manifest_path,dict(identity=identity,outputs=outputs,primary_family=family))
    return summary
