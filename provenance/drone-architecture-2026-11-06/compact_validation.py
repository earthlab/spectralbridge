"""Outer-only paired performance and target-cluster parameter/support uncertainty."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from compact_helpers import select
from spectralbridge.drone_original import fit_target_amplitudes,reference_design,reference_in_hull
P=Path(__file__).resolve().parent;d=pd.read_parquet(P/'ruby_compact_calibration.parquet');d=d[d.quality_supported];counts=d.groupby(['target_id','wavelength_nm']).size();eligible=set(counts[counts>=3].index);d=d[[tuple(v) in eligible for v in d[['target_id','wavelength_nm']].to_numpy()]];choices=json.loads((P/'compact_nested_selection.json').read_text());rng=np.random.default_rng(1861);ref=reference_design();rows=[]
for choice in choices:
 outer=choice['outer'];train=d[d.holdout_fold!=outer];test=d[d.holdout_fold==outer]
 for name,config in [('full',dict(targets=64,views=99,design='spatial')),('nested_selected',choice['selected'])]:
  if config is None:continue
  calibration=select(train,config)
  for nm,a in calibration.groupby('wavelength_nm'):
   b=test[test.wavelength_nm==nm];X=np.c_[np.ones(len(a)),a.ross,a.li];Xt=np.c_[np.ones(len(b)),b.ross,b.li];y=a.observed_fraction.to_numpy();targets=a.target_id.to_numpy();unique=np.unique(targets);betas=[]
   for _ in range(60):
    indices=np.concatenate([np.flatnonzero(targets==v) for v in rng.choice(unique,len(unique),replace=True)])
    try:betas.append(fit_target_amplitudes(X[indices],y[indices],targets[indices])['beta'])
    except (ValueError,np.linalg.LinAlgError):pass
   r=dict(outer=outer,design=name,wavelength_nm=float(nm),targets=len(unique),observations=len(a),bootstrap_replicates=len(betas),reference_joint_support=reference_in_hull(X,ref))
   if len(betas)>=30:
    betas=np.array(betas);reference=betas@ref;lower=np.quantile(Xt@betas.T,.025,axis=1);r.update(beta_interval=np.quantile(betas,[.025,.975],axis=0).tolist(),reference_interval=np.quantile(reference,[.025,.975]).tolist(),unsupported_test_predictions=int((lower<=0).sum()),normalization_supported=bool((lower>0).all() and np.quantile(reference,.025)>0 and r['reference_joint_support']))
   else:r['normalization_supported']=False
   rows.append(r)
(P/'compact_uncertainty.json').write_text(json.dumps(rows,indent=2)+'\n')
r=pd.read_csv(P/'compact_outer_results.csv');full=r[(r.targets==64)&(r.views==99)&(r.design=='spatial')].set_index(['outer','target_id','wavelength_nm']);paired=[]
for c in choices:
 if not c['selected']:continue
 outer=c['outer'];s=r[(r.outer==outer)&(r.config==c['selected']['config'])].set_index(['outer','target_id','wavelength_nm']);both=full[['ratio']].rename(columns={'ratio':'full'}).join(s[['ratio']].rename(columns={'ratio':'compact'}),how='inner').dropna();both=both[both.index.get_level_values('outer')==outer]
 for index,row in both.iterrows():paired.append(dict(outer=index[0],target_id=index[1],wavelength_nm=index[2],full=row.full,compact=row.compact,relative=row.compact/row.full))
pd.DataFrame(paired).to_csv(P/'compact_selected_outer_comparison.csv',index=False);print('Outer bootstrap models',len(rows),'paired target-band cases',len(paired),flush=True)
