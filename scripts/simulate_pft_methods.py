"""Design-aware simulation audit; distinguishes strong/weak nulls and H4 stress."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from spectralbridge.pft_method_audit import AuditConfig, METHODS, method_statistics
from spectralbridge.plant_pft_statistics import _write_json, contrast
from spectralbridge.plant_spectral_atlas import _file_hash

_LOG=logging.getLogger(__name__)
SCENARIOS=(
    'exchangeable_null','block_confounded_null','localized','broad_weak',
    'amplitude','shape','mean_null_unequal_covariance','H4_null_species_clusters',
    'repeated_plant_null','extreme_imbalance_null','extreme_imbalance_broad',
)


def wilson(k,n):
    z=norm.ppf(.975)
    p=k/n
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return center-half,center+half


def simulate(scenario,rng):
    w=np.arange(385,2511,25,dtype=float)
    # Unequal within-block counts; shared acquisition exposure within each block.
    n_a,n_b=([3,8,12],[16,8,4]) if scenario=="block_confounded_null" else ([6,8,10],[12,15,16])
    if scenario.startswith("extreme_imbalance"):
        n_a,n_b=[3,4,3],[120,130,140]
    z=np.concatenate([np.r_[np.ones(a),np.zeros(b)] for a,b in zip(n_a,n_b)])
    blocks=np.concatenate([np.full(a+b,i) for i,(a,b) in enumerate(zip(n_a,n_b))])
    basis=np.exp(-((w[None,:]-np.linspace(400,2500,12)[:,None])/230)**2)
    baseline=.15+.45/(1+np.exp(-(w-720)/35))-.15*np.exp(-((w-1600)/300)**2)
    latent=rng.normal(0,.14,(len(z),12))@basis
    if scenario=='mean_null_unequal_covariance':
        latent*=np.where(z[:,None]==1,2.5,.65)
    if scenario=='H4_null_species_clusters':
        # No PFT coefficient, but shared latent species functions; PFT labels are
        # constant within taxon. This stress case is NOT an exchangeable H1 null.
        species=np.empty(len(z),int)
        for block in np.unique(blocks):
            for label in (0,1):
                ix=np.flatnonzero((blocks==block)&(z==label))
                species[ix]=int(block)*4+int(label)*2+np.arange(len(ix))%2
        latent+=rng.normal(0,.2,(12,12))[species]@basis
    effect=np.zeros(len(w))
    if scenario=='localized':
        effect=.35*np.exp(-((w-1700)/35)**2)
    elif scenario in ('broad_weak','extreme_imbalance_broad'):
        effect=.075*np.ones(len(w))
    elif scenario=='amplitude':
        effect=.25*baseline
    elif scenario=='shape':
        effect=.18*np.exp(-((w-800)/140)**2)-.18*np.exp(-((w-1650)/220)**2)
    # Four repeated observations share a plant curve, plus block/flight effects.
    acquisition=rng.normal(0,.08,(3,4,12))@basis
    if scenario=='block_confounded_null':
        acquisition+=np.arange(3)[:,None,None]*.8
    noise=rng.normal(0,.025,(len(z),4,12))@basis
    repeated=baseline+latent[:,None,:]+z[:,None,None]*effect+acquisition[blocks]+noise
    values=np.median(repeated,axis=1)
    unsupported=((w>=1340)&(w<=1450))|((w>=1790)&(w<=2000))
    values[:,unsupported]=np.nan
    repeated[:,:,unsupported]=np.nan
    # An isolated unsupported measurement drops a feature; nothing is imputed.
    values[0,4]=np.nan
    return values,z,blocks,w,repeated


def run(output,*,replicates=200,permutations=499):
    root=Path(output)
    root.mkdir(parents=True,exist_ok=True)
    identity={'replicates':replicates,'permutations':permutations,'seed':20261014,
              'simulation_code':_file_hash(Path(__file__)),
              'method_code':_file_hash(Path(__file__).parents[1]/'src/spectralbridge/pft_method_audit.py')}
    all_rows=[]
    for scenario in SCENARIOS:
        path=root/(scenario+'.csv')
        metadata=path.with_suffix('.json')
        saved=json.loads(metadata.read_text()) if metadata.exists() else {}
        rows=[]
        if saved.get('identity')==identity and path.exists():
            if _file_hash(path)!=saved['sha256']:
                raise ValueError('Simulation checkpoint checksum mismatch')
            rows=pd.read_csv(path).to_dict('records')
        done={int(r['replicate']) for r in rows}
        for rep in range(replicates):
            if rep in done:
                continue
            seed=int(hashlib.sha256(f'20261014-{scenario}-{rep}'.encode()).hexdigest()[:8],16)
            y,z,b,w,repeated=simulate(scenario,np.random.default_rng(seed))
            cfg=AuditConfig(permutations=permutations,max_gap_nm=30)
            result=method_statistics(y,z,b,w,config=cfg,seed=seed+1)
            rows.append({'scenario':scenario,'replicate':rep,**{'p_'+k:v for k,v in result['p'].items()}})
            if scenario in ('repeated_plant_null','block_confounded_null'):
                if scenario=='repeated_plant_null':
                    naive_y=repeated.reshape(-1,len(w))
                    naive_z=np.repeat(z,4)
                    naive_b=np.repeat(b,4)
                else:
                    naive_y,naive_z,naive_b=y,z,np.zeros(len(z))
                naive=contrast(naive_y,naive_z,naive_b,permutations=permutations,bootstraps=19,seed=seed+2)
                rows[-1]['p_naive_max']=naive['p']
            if (rep+1)%20==0 or rep==replicates-1:
                pd.DataFrame(rows).to_csv(path.with_suffix('.tmp.csv'),index=False)
                path.with_suffix('.tmp.csv').replace(path)
                _write_json(metadata,{'identity':identity,'sha256':_file_hash(path)})
                _LOG.info('%s | completed %s/%s',scenario,rep+1,replicates)
        all_rows.extend(rows)
    results=pd.DataFrame(all_rows)
    results.to_csv(root/'replicate_results.csv',index=False)
    summary=[]
    for scenario,group in results.groupby('scenario',sort=False):
        for method in (*METHODS,'naive_max'):
            col='p_'+method
            vals=group[col].dropna() if col in group else pd.Series(dtype=float)
            if vals.empty:
                continue
            k=int(vals.le(.05).sum())
            lo,hi=wilson(k,len(vals))
            target=('strong_exchangeability_null' if scenario in ('exchangeable_null','block_confounded_null','repeated_plant_null','extreme_imbalance_null') else
                    'mean_null_but_distribution_alternative' if scenario=='mean_null_unequal_covariance' else
                    'species_independent_null_not_H1_exchangeable' if scenario=='H4_null_species_clusters' else 'alternative')
            summary.append({'scenario':scenario,'method':method,'rejections':k,'replicates':len(vals),'rate':k/len(vals),
                            'wilson_low':lo,'wilson_high':hi,'target':target})
    pd.DataFrame(summary).to_csv(root/'simulation_summary.csv',index=False)
    owned = [root/(s+ext) for s in SCENARIOS for ext in ('.csv','.json')]
    owned += [root/'replicate_results.csv', root/'simulation_summary.csv']
    _write_json(root/'simulation_manifest.json',{'identity':identity,'outputs':{p.name:_file_hash(p) for p in owned}})
    return pd.DataFrame(summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--replicates',type=int,default=200)
    parser.add_argument('--permutations',type=int,default=499)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    run(args.output,replicates=args.replicates,permutations=args.permutations)
