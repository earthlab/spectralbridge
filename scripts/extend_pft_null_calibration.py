"""Extend the exchangeable-null check without rerunning alternative scenarios."""
from pathlib import Path
import hashlib
import json
import logging

import numpy as np
import pandas as pd

from scripts.simulate_pft_methods import simulate, wilson
from spectralbridge.pft_method_audit import AuditConfig, METHODS, method_statistics
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.plant_pft_statistics import _write_json

_LOG=logging.getLogger(__name__)


def run(root,replicates=5000):
    root=Path(root)
    source=root/'replicate_results.csv'
    result_path=root/'exchangeable_null_extended.csv'
    base=pd.read_csv(source).query('scenario=="exchangeable_null"')
    rows=base.to_dict('records')
    identity={'source':_file_hash(source),'code':_file_hash(Path(__file__)),
              'generator':_file_hash(Path(__file__).with_name('simulate_pft_methods.py')),
              'method':_file_hash(Path(__file__).parents[1]/'src/spectralbridge/pft_method_audit.py'),
              'replicates':replicates}
    metadata=result_path.with_suffix('.json')
    if metadata.exists():
        saved=json.loads(metadata.read_text())
        if saved.get('identity')==identity and _file_hash(result_path)==saved['sha256']:
            rows=pd.read_csv(result_path).to_dict('records')
    done={int(r['replicate']) for r in rows}
    for rep in range(replicates):
        if rep in done:
            continue
        seed=int(hashlib.sha256(f'20261014-exchangeable_null-{rep}'.encode()).hexdigest()[:8],16)
        y,z,b,w,_=simulate('exchangeable_null',np.random.default_rng(seed))
        result=method_statistics(y,z,b,w,config=AuditConfig(permutations=499,max_gap_nm=30),seed=seed+1)
        rows.append({'scenario':'exchangeable_null','replicate':rep,**{'p_'+k:v for k,v in result['p'].items()}})
        if (rep+1)%100==0 or rep==replicates-1:
            temp=result_path.with_suffix('.tmp.csv')
            pd.DataFrame(rows).to_csv(temp,index=False)
            temp.replace(result_path)
            _write_json(metadata,{'identity':identity,'sha256':_file_hash(result_path)})
            _LOG.info('Exchangeable null %s/%s',rep+1,replicates)
    frame=pd.DataFrame(rows)
    summary=[]
    for method in METHODS:
        k=int(frame['p_'+method].le(.05).sum())
        lo,hi=wilson(k,len(frame))
        summary.append({'method':method,'replicates':len(frame),'rejections':k,'rate':k/len(frame),'wilson_low':lo,'wilson_high':hi})
    pd.DataFrame(summary).to_csv(root/'extended_null_summary.csv',index=False)
    return pd.DataFrame(summary)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    run('artifacts/plant_spectral_atlas/pft_method_audit/simulations')
