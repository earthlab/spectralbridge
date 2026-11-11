"""Shared frozen selection/evaluation definitions for nested compact calibration."""
import numpy as np
import pandas as pd
from spectralbridge.drone_original import fit_target_amplitudes,reference_design,reference_in_hull
reference=reference_design()

def select(train,config):
 targets=train.groupby('target_id')[['x','y']].first();xy=targets.to_numpy();names=targets.index.to_numpy();n=min(config['targets'],len(names))
 if config['design']=='concentrated':order=np.argsort(np.linalg.norm(xy-xy.mean(0),axis=1))[:n]
 else:
  order=[int(np.lexsort((xy[:,1],xy[:,0]))[0])]
  while len(order)<n:
   distances=np.min(np.linalg.norm(xy[:,None,:]-xy[np.array(order)][None,:,:],axis=2),axis=1);distances[order]=-1;order.append(int(np.argmax(distances)))
 subset=train[train.target_id.isin(names[order])];out=[]
 for _,g in subset.groupby(['target_id','wavelength_nm']):
  g=g.sort_values('timestamp_utc_scenario');v=min(config['views'],len(g))
  if config['design']=='angular' and v<len(g):
   z=g[['ross','li']].to_numpy();scale=np.maximum(np.std(z,axis=0),1e-8);z=z/scale;indices=[int(np.argmin(g.view_zenith_deg))]
   while len(indices)<v:
    dist=np.min(np.linalg.norm(z[:,None]-z[np.array(indices)][None,:],axis=2),axis=1);dist[indices]=-1;indices.append(int(np.argmax(dist)))
  else:indices=np.unique(np.linspace(0,len(g)-1,v).round().astype(int))
  if len(indices)>=3:out.append(g.iloc[indices])
 return pd.concat(out) if out else subset.iloc[:0]

def evaluate(train,test,config):
 calibration=select(train,config);out=[];betas=[]
 for nm,a in calibration.groupby('wavelength_nm'):
  b=test[test.wavelength_nm==nm]
  if len(a)<8 or len(b)<3:continue
  X=np.c_[np.ones(len(a)),a.ross,a.li];Xt=np.c_[np.ones(len(b)),b.ross,b.li]
  try:
   fit=fit_target_amplitudes(X,a.observed_fraction.to_numpy(),a.target_id.to_numpy());shape=Xt@fit['beta'];ref=float(reference@fit['beta']);support=reference_in_hull(X,reference)&(shape>0)&(ref>0);corrected=np.where(support,b.observed_fraction.to_numpy()*ref/shape,np.nan)
   betas.append(dict(wavelength_nm=float(nm),beta=fit['beta'].tolist(),condition=fit['condition'],reference_joint_support=reference_in_hull(X,reference),reference_prediction=ref))
   for target,g in b.assign(corrected=corrected).groupby('target_id'):
    if len(g)<2:continue
    raw=g.observed_fraction.to_numpy();corr=g.corrected.to_numpy();rawcv=np.std(raw)/abs(np.mean(raw));newcv=np.std(corr)/abs(np.mean(corr)) if np.isfinite(corr).all() and np.mean(corr)!=0 else np.nan
    ratio=(newcv/rawcv)**2 if rawcv>1e-10 else np.nan
    out.append(dict(target_id=target,wavelength_nm=float(nm),ratio=float(ratio),supported=bool(np.isfinite(ratio)),observations=len(g),raw_sd=float(np.std(raw)),corrected_sd=float(np.std(corr)),absolute_variance_ratio=float((np.std(corr)/np.std(raw))**2) if np.std(raw)>1e-10 else np.nan))
  except (ValueError,np.linalg.LinAlgError):continue
 return pd.DataFrame(out),calibration,betas

