"""Compact causal tables and standardized sensitivity figures."""
from pathlib import Path
import json
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';FIG=HERE/'figures'
tr=pd.read_csv(HERE/'traced_extreme_pixels.csv');ci=tr.incidence.to_numpy();reference=tr.topo_reference.to_numpy();lo=tr.C_low.to_numpy();hi=tr.C_high.to_numpy();end1=(reference+lo)/(ci+lo);end2=(reference+hi)/(ci+hi);tr['topographic_factor_interval_low']=np.minimum(end1,end2);tr['topographic_factor_interval_high']=np.maximum(end1,end2);tr.to_csv(HERE/'traced_extreme_pixels.csv',index=False)
fits=[]
for site in ['gordon','goldhill','ruby']:
 for stage in ['brdf_only','combined']:
  m=json.loads((HERE/'stable_qr_v1'/f'{site}_{stage}_brdf_model.json').read_text())
  for r in m['validation']['fits']:
   fits.append(dict(site=site.title(),stage=stage,band_nm=m['wavelengths_nm'][r['band']],status=r['status'],reference=r['reference_prediction'],reference_se=r['reference_standard_error'],reference_z=r['reference_prediction']/r['reference_standard_error'],condition=r['condition_number'],groups=r['uncertainty_groups'],reference_resolved=r['reference_prediction_resolved'],unresolved_observed=r['unresolved_observed_geometry_predictions'],reference_outside_bounds=r['reference_outside_kernel_bounds'],rmse=r['residual_rmse'],excluded_above_max=r['excluded_above_max'],eligible=r['eligible']))
pd.DataFrame(fits).to_csv(HERE/'native_fit_support.csv',index=False)
fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for site,color in zip(['Gordon','Goldhill','Ruby'],['#227a55','#bc6a24','#6244a0']):
 for ax,stage in zip(axs,['brdf_only','combined']):
  rows=[r for r in fits if r['site']==site and r['stage']==stage];ax.errorbar([r['band_nm'] for r in rows],[r['reference'] for r in rows],yerr=[1.96*r['reference_se'] for r in rows],label=site,color=color,marker='.',capsize=3);ax.axhline(0,color='black',lw=.7);ax.set(title=stage.replace('_',' '),xlabel='Wavelength (nm)',ylabel='Reference prediction +/- 1.96 cluster SE')
axs[0].legend();fig.suptitle('Ruby fails at the normalization reference; uncertainty is conditional on spatial groups');fig.savefig(FIG/'reference_uncertainty.png',dpi=160);plt.close(fig)
sens=json.loads((HERE/'sensitivity_experiments.json').read_text());cv=pd.DataFrame([r for r in sens if r['method'].startswith('spatial_holdout_')]);cv.to_csv(HERE/'spatial_holdout_errors.csv',index=False)
fig,axs=plt.subplots(1,3,figsize=(12,4),layout='constrained')
for ax,site in zip(axs,['Gordon','Goldhill','Ruby']):
 a=cv[(cv.site==site)&(cv.stage=='brdf_only')].groupby('method').test_rmse.mean();a.index=[s.replace('spatial_holdout_','').replace('nonnegative_coefficients','Nonnegative').replace('ridge_0.01','Ridge') for s in a.index];a.plot.bar(ax=ax,color='#3b7889');ax.set(title=site,ylabel='Mean held-out spatial-fold RMSE');ax.tick_params(axis='x',rotation=25)
fig.suptitle('Alternative fits do not establish an independent directional calibration');fig.savefig(FIG/'spatial_holdout.png',dpi=160);plt.close(fig)
# Direct covariance numerical comparison against an independent SVD influence calculation.
from spectralbridge.topographic import cluster_covariance
rng=np.random.default_rng(83);x=rng.normal(size=800);X=np.c_[np.ones(800),x,x+rng.normal(size=800)*1e-7];e=rng.normal(size=800);g=np.repeat(np.arange(40),20);inv=np.linalg.pinv(X);influence=np.stack([inv[:,g==k]@e[g==k] for k in range(40)]);truth=40/39*799/797*(influence.T@influence);qr,_=cluster_covariance(X,e,g);score=np.stack([np.bincount(g,weights=X[:,j]*e) for j in range(3)],axis=-1);bread=np.linalg.inv(X.T@X);normal=40/39*799/797*(bread@score.T@score@bread)
(HERE/'numerical_control.json').write_text(json.dumps(dict(design_condition=float(np.linalg.cond(X)),normal_relative_matrix_error=float(np.linalg.norm(normal-truth)/np.linalg.norm(truth)),qr_relative_matrix_error=float(np.linalg.norm(qr-truth)/np.linalg.norm(truth)),scope='Synthetic near-collinear control; not an accepted BRDF angular design or an explanation of Ruby'),indent=2)+'\n')
# Correct metadata to identify the actually executed frozen source snapshots.
for label in ['baseline_frozen_v2','stable_qr_v1']:
 p=HERE/label/'run_complete.json';r=json.loads(p.read_text());import hashlib
 r['sources']={m:hashlib.sha256((HERE/label/('source_'+m)).read_bytes()).hexdigest() for m in ['corrections.py','topographic.py']};r['source_identity_scope']='Actual frozen source snapshots used for this run';p.write_text(json.dumps(r,indent=2)+'\n')
print(tr[(tr.band_nm==650)&(tr.kind=='factor_maximum')][['site','baseline_stage','topographic_factor_interval_low','topographic_factor_interval_high']].to_string(index=False));print(cv.groupby(['site','stage','method']).test_rmse.mean().to_string())
