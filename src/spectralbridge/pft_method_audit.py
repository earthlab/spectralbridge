"""Additive, design-conditional audit of PFT whole-curve inference.

Established scaled-MAD envelopes and synchronized nonparametric combination;
explicit blocked energy/FPCA adaptations. Does not claim species-independent effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import logging
import platform

import numpy as np
import pandas as pd
import scipy
from scipy.spatial.distance import cdist
from scipy.stats import rankdata

from .plant_pft_statistics import (
    _center, _history_keys, _seed, _write_json, holm, permute_within,
)
from .plant_spectral_atlas import _file_hash
from .plant_spectral_pfts import UNASSIGNED, load_pft_crosswalk, tag_pfts
from .plant_spectral_quantiles import _model_inputs
from .plant_spectral_years import _year_plant_spectra

_LOG = logging.getLogger(__name__)
METHODS = ("max", "integrated", "npc", "energy", "fpca")


@dataclass(frozen=True)
class AuditConfig:
    """Configure the historical whole-spectrum PFT method audit and its explicit resampling budgets."""

    permutations: int = 9999
    seed: int = 20261014
    pc_variance: float = .95
    pc_cap: int = 10
    max_gap_nm: float = 8

    def validate(self):
        if self.permutations < 19 or not 0 < self.pc_variance <= 1 or self.pc_cap < 1:
            raise ValueError("Invalid audit resampling/projection settings")


def wavelength_weights(w, max_gap=8):
    """Trapezoidal weights on disconnected supported segments, never across gaps."""
    w = np.asarray(w, float)
    if len(w) < 2 or np.any(~np.isfinite(w)) or np.any(np.diff(w) <= 0):
        raise ValueError("Need unique ordered finite wavelengths")
    result = np.zeros(len(w))
    for i, delta in enumerate(np.diff(w)):
        if delta <= max_gap:
            result[i:i+2] += delta / 2
    if result.sum() <= 0:
        raise ValueError("No supported spectral intervals")
    # Isolated points retain max-test support, but have zero integration length.
    return result / result.sum()


def upper_p(values):
    """Exchangeable ensemble upper-tail ranks, inclusive of identity and ties."""
    a = np.asarray(values, float)
    rounded = np.round(a / max(1., float(np.max(np.abs(a)))), 12)
    return rankdata(-rounded, method="max") / len(a)


def npc_probability(statistics):
    """Synchronized Tippett combination; calibrate min partial p on same ensemble."""
    partial = np.column_stack([upper_p(statistics[:, j]) for j in range(statistics.shape[1])])
    smallest = partial.min(axis=1)
    return float(np.count_nonzero(smallest <= smallest[0] + 1e-15) / len(smallest))


def envelope_critical(maxima, alpha):
    """Conservative Monte Carlo MAD multiplier with strict excursion/tie rule."""
    null = np.asarray(maxima, float)
    if not 0 < alpha < 1 or not len(null):
        raise ValueError("Invalid envelope inputs")
    k = int(np.ceil((len(null) + 1) * (1 - alpha)))
    return float(np.sort(null)[k-1]) if k <= len(null) else float("inf")


def method_statistics(values, labels, blocks, wavelengths, *, config=None, seed=None, integration_weights=None) -> dict:
    """Evaluate synchronized conditional whole-spectrum permutation statistics.

    Args:
        values (array-like): Stored reflectance matrix (N polygon/year curves, B
            wavelengths). Units remain unchanged; finite common variable columns
            within eligible mixed blocks are used, without imputation.
        labels (array-like): Binary 0/1 group labels, shape (N,).
        blocks (array-like): Nonmissing exact-history block labels, shape (N,).
        wavelengths (array-like): Increasing coordinates in nm, shape (B,).
        config (AuditConfig, optional): Permutations, rank and gap settings.
        seed (int, optional): Overrides the config seed.
        integration_weights (array-like, optional): Nonnegative weights (B,).
            Default is disconnected wavelength quadrature; use explicit discrete
            sensor weights for widely spaced channels.

    Returns:
        dict: Observed/permuted curves and four statistics, component/NPC p-values,
            rows/columns retained, scale, SE, normalized weights and FPCA diagnostics.

    Raises:
        ValueError: Invalid dimensions/labels/blocks/weights or insufficient
            complete variable support / exchangeable mixed blocks.

    Labels move as whole curves within blocks. Conditional exchangeability is an
    assumption; results do not establish causal PFT mechanisms. NPC calibrates a
    joint probability combination, not an uncorrected minimum p. Multiplicity
    adjustment and family envelopes belong to the calling analysis.
    """
    config = config or AuditConfig()
    config.validate()
    y, z, b, w = np.asarray(values, float), np.asarray(labels, float), np.asarray(blocks), np.asarray(wavelengths, float)
    if y.ndim != 2 or y.shape != (len(z), len(w)) or len(b) != len(z):
        raise ValueError("Inconsistent data dimensions")
    if set(np.unique(z)) != {0., 1.} or pd.isna(b).any():
        raise ValueError("Need binary labels and nonmissing blocks")
    mixed = [v for v in np.unique(b) if len(np.unique(z[b == v])) == 2]
    rows = np.flatnonzero(np.isin(b, mixed))
    y, z, b = y[rows], z[rows], b[rows]
    if not len(y):
        raise ValueError("No exchangeable mixed blocks")
    complete = np.isfinite(y).all(axis=0)
    centered = _center(y[:, complete], b)
    variance = np.sum(centered**2, axis=0) / (len(y) - len(mixed))
    informative = variance > 0
    columns = np.flatnonzero(complete)[informative]
    yc = centered[:, informative]
    scale = np.sqrt(variance[informative])
    if len(columns) < 2:
        raise ValueError("No complete variable spectral domain")
    if integration_weights is None:
        weights = wavelength_weights(w[columns], config.max_gap_nm)
    else:
        supplied = np.asarray(integration_weights, float)
        if (supplied.shape != w.shape or not np.isfinite(supplied).all()
                or np.any(supplied < 0) or supplied[columns].sum() <= 0):
            raise ValueError("Integration weights must be finite nonnegative band weights with positive retained sum")
        weights = supplied[columns] / supplied[columns].sum()
    x = _center(z[:, None], b).ravel()
    xx = x @ x
    standardized = yc / scale
    se = scale / np.sqrt(xx)
    weighted = standardized * np.sqrt(weights)
    # PCA uses responses/blocks only, not labels; keep the same projection for
    # every permutation. Scores are covariance-whitened in the retained subspace.
    u, singular, _ = np.linalg.svd(weighted, full_matrices=False)
    rank = int((singular > singular[0] * 1e-10).sum())
    k95 = int(np.searchsorted(np.cumsum(singular**2) / np.sum(singular**2), config.pc_variance) + 1)
    pcs = max(1, min(config.pc_cap, rank, len(y)-len(mixed)-2, k95))
    score_y = u[:, :pcs] * np.sqrt(len(y)-len(mixed))
    explained = float(np.sum(singular[:pcs]**2) / np.sum(singular**2))
    # Block energy metric is fixed under label permutation. Offset subtraction
    # does not change within-block Euclidean distances.
    energy_blocks = []
    for block in mixed:
        ix = np.flatnonzero(b == block)
        n1 = int(z[ix].sum())
        n0 = len(ix) - n1
        block_weight = n1 * n0 / len(ix) / xx
        distances = cdist(weighted[ix], weighted[ix])
        energy_blocks.append((ix, n1, n0, block_weight, distances))
    count = config.permutations + 1
    curves = np.empty((count, len(columns)))
    stats = np.empty((count, 4))
    rng = np.random.default_rng(config.seed if seed is None else seed)
    for start in range(0, count, 128):
        size = min(128, count-start)
        # Identity must not consume a random permutation: legacy draws then match.
        zz = np.stack([z if start+i == 0 else permute_within(z, b, rng) for i in range(size)])
        # Y is block-centered, so the block mean of z need not be subtracted here.
        t = zz @ standardized / np.sqrt(xx)
        curves[start:start+size] = t * se
        stats[start:start+size, 0] = np.abs(t).max(axis=1)
        stats[start:start+size, 1] = (t*t) @ weights
        pc = zz @ score_y / np.sqrt(xx)
        stats[start:start+size, 3] = np.sum(pc*pc, axis=1)
        energy = np.zeros(size)
        for ix, n1, n0, bw, distance in energy_blocks:
            contrast_weights = zz[:, ix] / n1 - (1 - zz[:, ix]) / n0
            energy -= bw * np.sum((contrast_weights @ distance) * contrast_weights, axis=1)
        stats[start:start+size, 2] = np.maximum(0, energy)
    # Tolerances only account for floating ties, not a scientific threshold.
    probabilities = {}
    for name, j in [("max", 0), ("integrated", 1), ("energy", 2), ("fpca", 3)]:
        threshold = stats[0, j] - 1e-12 * max(1, abs(stats[0, j]))
        probabilities[name] = float((1 + np.count_nonzero(stats[1:, j] >= threshold)) / count)
    probabilities['npc'] = npc_probability(stats[:, :2])
    return {"p": probabilities, "curves": curves, "stats": stats, "se": se,
            "scale": scale, "columns": columns, "rows": rows,
            "weights": weights, "pcs": pcs, "pc_variance_retained": explained}


def _plot_envelopes(root, summary, records, family):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cohorts = sorted(summary.cohort.unique())
    pairs = sorted(summary.pair.unique())
    fig, axes = plt.subplots(len(pairs), len(cohorts), figsize=(16, 2.2*len(pairs)), squeeze=False)
    for i, pair in enumerate(pairs):
        for j, cohort in enumerate(cohorts):
            ax = axes[i, j]
            rows = summary[(summary.pair == pair) & (summary.cohort == cohort) & (summary.blocking == 'flight_history')]
            rec = None if rows.empty else rows.iloc[0]
            if rec is None or rec.status != 'tested':
                ax.text(.5,.5,'Insufficient matched support',ha='center',transform=ax.transAxes,fontsize=7)
                ax.set(xticks=[],yticks=[])
            else:
                result, w = records[rec.test_id]
                maxes = result['stats'][1:,0]
                c95 = envelope_critical(maxes,.05)
                cfamily = envelope_critical(maxes,.05/family)
                obs = result['curves'][0] / result['se']
                for ix in np.split(np.arange(len(w)),np.flatnonzero(np.diff(w)>8)+1):
                    ax.fill_between(w[ix],-cfamily,cfamily,color='#d2d6dc',alpha=.7)
                    ax.fill_between(w[ix],-c95,c95,color='#a6c9e4',alpha=.8)
                    ax.plot(w[ix],obs[ix],color='#114b72',lw=.8)
                sig = np.abs(obs)>cfamily
                ax.scatter(w[sig],obs[sig],s=3,color='#bd253e')
                ax.text(.02,.96,f"NPC adj p={rec.p_npc_holm:.3g}; max adj p={rec.p_max_holm:.3g}",va='top',transform=ax.transAxes,fontsize=6.5)
                ax.axhline(0,color='grey',lw=.5)
            if i==0:
                ax.set_title(cohort)
            if j==0:
                ax.set_ylabel(pair+'\nA−B / fixed scale',fontsize=8)
            if i==len(pairs)-1:
                ax.set_xlabel('Wavelength (nm)')
    fig.suptitle('Corrected NEON: observed contrast and simultaneous null envelopes\nBlue: 95% over wavelengths; grey/red excursions: Bonferroni over primary matched contrasts\nEnvelope represents MAX component; NPC can reject without an excursion. Local y limits.',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.96))
    fig.savefig(root/'simultaneous_envelopes.png',dpi=140)
    fig.savefig(root/'simultaneous_envelopes.pdf')
    plt.close(fig)


def run_method_audit(comparisons, legacy, output, *, config=None):
    """Audit historical PFT comparisons against checksum-verified prior results with restart checkpoints."""

    config = config or AuditConfig()
    config.validate()
    comparisons, legacy, root = map(Path,(comparisons,legacy,output))
    root.mkdir(parents=True,exist_ok=True)
    (root/'checkpoints').mkdir(exist_ok=True)
    old_manifest = json.loads((legacy/'statistics_manifest.json').read_text())
    if not all(_file_hash(legacy/n)==h for n,h in old_manifest['outputs'].items()):
        raise ValueError('Legacy output checksum mismatch')
    old = pd.read_csv(legacy/'pairwise_tests.csv')
    old = old[old.stage=='corr'].copy()
    _,_,observations,_,hashes = _model_inputs(comparisons)
    mapping = load_pft_crosswalk()
    table, cols, source = _year_plant_spectra(observations['corr'][0],'corr')
    table = tag_pfts(table,mapping).join(_history_keys(source),on=['GlobalID','year'])
    table = table[table.pft!=UNASSIGNED].sort_values(['site','year','GlobalID']).reset_index(drop=True)
    w = np.array([float(c.split('_wl')[1][:-2]) for c in cols])
    identity = {'config':asdict(config),'sources':hashes,'legacy':_file_hash(legacy/'statistics_manifest.json'),
                'code':_file_hash(Path(__file__)), 'legacy_code':_file_hash(Path(__file__).with_name('plant_pft_statistics.py')),
                'year_code':_file_hash(Path(__file__).with_name('plant_spectral_years.py')),
                'mapping':hashlib.sha256(mapping.to_csv(index=False).encode()).hexdigest(),
                'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}}
    manifest_path=root/'audit_manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        if manifest['identity']==identity and all((root/n).is_file() and _file_hash(root/n)==h for n,h in manifest['outputs'].items()):
            return pd.read_csv(root/'method_comparison.csv')
    summaries=[]
    records={}
    memberships=[]
    for row in old.itertuples():
        meta={k:getattr(row,k) for k in ['test_id','cohort','pair','site','year','a','b','blocking','status','n_a','n_b']}
        meta['legacy_max_p']=row.p
        meta['legacy_max_holm_324']=row.p_holm
        meta['legacy_rank_holm_324']=row.p_rank_holm
        if row.status!='tested':
            summaries.append(meta)
            continue
        pair=table[(table.site==row.site)&(table.year==row.year)&table.pft_code.isin([row.a,row.b])].reset_index(drop=True)
        z=pair.pft_code.eq(row.a).astype(int).to_numpy()
        blocks=np.zeros(len(pair),int) if row.blocking=='site_year' else pd.factorize(pair.flight_history)[0]
        path=root/'checkpoints'/(row.test_id+'.npz')
        meta_path=path.with_suffix('.json')
        saved=json.loads(meta_path.read_text()) if meta_path.exists() else {}
        _LOG.info('%s | n=%s/%s | ensemble=%s',row.test_id,row.n_a,row.n_b,config.permutations+1)
        if saved.get('identity')==identity:
            if _file_hash(path)!=saved['sha256']:
                raise ValueError('Audit checkpoint checksum mismatch')
            with np.load(path) as f:
                result={k:f[k] for k in f.files}
            result['p']=saved['p']
        else:
            result=method_statistics(pair[cols].to_numpy(float),z,blocks,w,config=config,seed=_seed(config,row.test_id))
            # Only the observed function is needed after null maxima/statistics
            # are retained; do not persist gigabytes of redundant null curves.
            result["curves"]=result["curves"][:1].copy()
            temp=path.with_suffix('.tmp.npz')
            np.savez_compressed(temp,**{k:v for k,v in result.items() if k!='p'})
            temp.replace(path)
            _write_json(meta_path,{'identity':identity,'sha256':_file_hash(path),'p':result['p']})
        if config.permutations==old_manifest['identity']['config']['permutations'] and config.seed==old_manifest['identity']['config']['seed']:
            if abs(result['p']['max']-row.p)>1e-12:
                raise ValueError(f'Legacy maximum probability not reproduced: {row.test_id}')
        actual=pair.iloc[result['rows']].copy()
        actual['test_id']=row.test_id
        memberships.append(actual[['test_id','GlobalID','species','pft_code','site','year','flight_history']])
        if (actual.pft_code==row.a).sum()!=row.n_a or (actual.pft_code==row.b).sum()!=row.n_b:
            raise ValueError('Audit and legacy membership counts differ')
        for method,p in result['p'].items():
            meta['p_'+method]=p
        meta['pcs']=int(result['pcs'])
        meta['pc_variance_retained']=float(result['pc_variance_retained'])
        meta['bands']=len(result['columns'])
        summaries.append(meta)
        records[row.test_id]=(result,w[result['columns']])
    summary=pd.DataFrame(summaries)
    # Scientific families are predeclared by conditioning target, per method;
    # methods are sensitivities, never an uncorrected union of positive claims.
    for blocking in ['site_year','flight_history']:
        use=(summary.status=='tested')&(summary.blocking==blocking)
        for method in METHODS:
            summary.loc[use,'p_'+method+'_holm']=holm(summary.loc[use,'p_'+method])
    summary.to_csv(root/'method_comparison.csv',index=False)
    pd.concat(memberships,ignore_index=True).to_parquet(root/'audit_membership.parquet',index=False)
    family=int(((summary.status=='tested')&(summary.blocking=='flight_history')).sum())
    envelope=[]
    for row in summary[summary.status=='tested'].itertuples():
        result,ww=records[row.test_id]
        m=int(((summary.status=='tested')&(summary.blocking==row.blocking)).sum())
        c95=envelope_critical(result['stats'][1:,0],.05)
        cf=envelope_critical(result['stats'][1:,0],.05/m)
        for j,wave in enumerate(ww):
            envelope.append({'test_id':row.test_id,'wavelength_nm':wave,'observed_beta':result['curves'][0,j],
                             'null_se':result['se'][j], 'lower_simultaneous_95':-c95*result['se'][j],
                             'upper_simultaneous_95':c95*result['se'][j],
                             'lower_family':-cf*result['se'][j],'upper_family':cf*result['se'][j],
                             'excursion_family':abs(result['curves'][0,j])>cf*result['se'][j]})
    pd.DataFrame(envelope).to_csv(root/'envelopes.csv',index=False)
    _plot_envelopes(root,summary,records,family)
    _consistency(root,summary,records)
    outputs={str(p.relative_to(root)):_file_hash(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=manifest_path}
    _write_json(manifest_path,{'identity':identity,'outputs':outputs,'primary_family':family,
                             'claim':'H1/H2 conditional sampled-mixture association; not H4-H6'})
    return summary


def _consistency(root,summary,records):
    rows=[]
    for pair,group in summary[(summary.blocking=='flight_history')&(summary.year==2023)&(summary.status=='tested')].groupby('pair'):
        for i,a in enumerate(list(group.itertuples())):
            for b in list(group.itertuples())[i+1:]:
                ra,wa=records[a.test_id]
                rb,wb=records[b.test_id]
                common,ia,ib=np.intersect1d(wa,wb,return_indices=True)
                aa,bb=ra['curves'][0,ia],rb['curves'][0,ib]
                rows.append({'pair':pair,'site_a':a.site,'site_b':b.site,'bands':len(common),
                             'cosine':float(aa@bb/(np.linalg.norm(aa)*np.linalg.norm(bb))),
                             'pearson_shape':float(np.corrcoef(aa,bb)[0,1]),
                             'sign_agreement':float(np.mean(np.sign(aa)==np.sign(bb)))})
    pd.DataFrame(rows).to_csv(root/'cross_site_curve_consistency.csv',index=False)
