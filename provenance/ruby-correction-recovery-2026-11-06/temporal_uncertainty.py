"""Explicit missing time-pairs bootstrap and separate time-cluster wild control.

Pairs resampling may leave single-observation targets, which the original
candidate fitting contract rejects. Such missing uncertainty is not a pass.
A separate Rademacher residual wild bootstrap retains the complete observed
angular design. Both remain conditional single-flight uncertainty diagnostics.
"""
from pathlib import Path
import json
import numpy as np,pandas as pd
from spectralbridge.drone_original import fit_target_amplitudes,temporal_minute_groups,reference_design,reference_in_hull
P=Path(__file__).resolve().parent;d=pd.read_csv(P/'observations_enriched.csv');existing=json.loads((P/'bootstrap_uncertainty.json').read_text());out=[];rng=np.random.default_rng(1846);ref=reference_design()
for nm,b in d[d.quality_supported].groupby('wavelength_nm'):
 counts=b.groupby('target_id').size();b=b[b.target_id.isin(counts[counts>=3].index)];X=np.c_[np.ones(len(b)),b.ross,b.li];y=b.observed_fraction.to_numpy();targets=b.target_id.to_numpy();groups=temporal_minute_groups(b.timestamp_utc_scenario);unique,ind=np.unique(groups,return_inverse=True);fit=fit_target_amplitudes(X,y,targets);fitted=y-fit['residual'];betas=[]
 for _ in range(120):
  pseudo=fitted+fit['residual']*rng.choice([-1.,1.],size=len(unique))[ind]
  try:betas.append(fit_target_amplitudes(X,pseudo,targets)['beta'])
  except (ValueError,np.linalg.LinAlgError):pass
 pairs_present=any(r['wavelength_nm']==nm and r['clustering']=='time_minute' for r in existing)
 record=dict(wavelength_nm=float(nm),groups=len(unique),clustering='time_minute_wild',time_pairs_status='REPORTED' if pairs_present else 'INSUFFICIENT_SUCCESSFUL_REPLICATES_NOT_A_PASS',successful_replicates=len(betas),method='Rademacher minute-cluster residual wild bootstrap; full design retained',independent_calibration_validation=False)
 if len(betas)>=60:
  betas=np.array(betas);p=X@betas.T;r=betas@ref;record.update(reference_interval=np.quantile(r,[.025,.975]).tolist(),coefficient_interval=np.quantile(betas,[.025,.975],axis=0).tolist(),nonpositive_lower_application=int((np.quantile(p,.025,axis=1)<=0).sum()),reference_joint_support=reference_in_hull(X,ref));record['normalization_supported']=bool(record['nonpositive_lower_application']==0 and record['reference_interval'][0]>0 and record['reference_joint_support'])
 else:record.update(normalization_supported=False,status='INSUFFICIENT_REPLICATES')
 out.append(record)
(P/'temporal_wild_uncertainty.json').write_text(json.dumps(out,indent=2)+'\n');print('Temporal control completed',len(out))
