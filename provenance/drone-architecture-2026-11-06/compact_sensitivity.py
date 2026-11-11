"""Fixed outer-fold heterogeneity sensitivity and band-subset summaries."""
from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
from compact_helpers import evaluate
P=Path(__file__).resolve().parent;R=P.parents[1];d=pd.read_parquet(P/'ruby_compact_calibration.parquet');q=d[d.quality_supported].copy();counts=q.groupby(['target_id','wavelength_nm']).size();eligible=set(counts[counts>=3].index);q=q[[tuple(v) in eligible for v in q[['target_id','wavelength_nm']].to_numpy()]];rows=[]
# Measured patch CV stratification, not independent cover truth. Threshold is fixed before these fits.
for fold in sorted(q.holdout_fold.unique()):
 train=q[q.holdout_fold!=fold];test=q[q.holdout_fold==fold]
 for label,mask in [('all',np.ones(len(train),bool)),('patch_CV_at_most_0.25',train.patch_cv<=.25),('patch_CV_above_0.25',train.patch_cv>.25)]:
  a=train[mask]
  if a.empty:continue
  out,cal,models=evaluate(a,test,dict(targets=64,views=99,design='spatial'))
  if len(out):out['heterogeneity_training']=label;out['outer']=int(fold);out['calibration_rows']=len(cal);rows.append(out)
result=pd.concat(rows,ignore_index=True);result.to_csv(P/'compact_heterogeneity.csv',index=False)
reference=result[result.heterogeneity_training=='all'][['outer','target_id','wavelength_nm','ratio']].rename(columns={'ratio':'full_ratio'});paired=result.merge(reference,on=['outer','target_id','wavelength_nm']);paired['relative_cv2']=paired.ratio/paired.full_ratio;paired.to_csv(P/'compact_heterogeneity_paired.csv',index=False)
full=pd.read_csv(P/'compact_outer_results.csv');full=full[(full.targets==64)&(full.views==99)&(full.design=='spatial')];summ=[]
for label,bands in [('red_only',[650]),('five_common_bands',[475,560,668,717,842]),('all_ten',sorted(full.wavelength_nm.unique()))]:
 z=full[full.wavelength_nm.isin(bands)];summ.append(dict(bands=label,n_cases=len(z),cv2_median=float(z.ratio.median()),cv2_mean=float(z.ratio.mean()),absolute_variance_median=float(z.absolute_variance_ratio.median())))
(P/'compact_band_subsets.json').write_text(json.dumps(summ,indent=2)+'\n')
metadata=dict(schema='spectralbridge_compact_drone_calibration_research_v1',packet_sha256=hashlib.sha256((P/'ruby_compact_calibration.parquet').read_bytes()).hexdigest(),kernel_recipe='spectralbridge.drone_original.ross_li_design; RossThick/LiDenseR shared implementation; angles in degrees converted inside helper',helper_sha256=hashlib.sha256((R/'src/spectralbridge/drone_original.py').read_bytes()).hexdigest(),reference='solar zenith 45 degrees; view nadir; relative azimuth 0',processing_state='vendor_calibrated_pre_topo_pre_BRDF',contexts=1,independent_accuracy='UNVERIFIED',source='P184 actual repeated observations, not synthetic new truth')
(P/'compact_contract.json').write_text(json.dumps(metadata,indent=2)+'\n');print(summ);print(result.groupby('heterogeneity_training').ratio.agg(['count','median','mean']))
