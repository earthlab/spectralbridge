"""Compact reusable observations and nested spatial calibration-size comparisons."""
from pathlib import Path
import json,time,resource
import numpy as np,pandas as pd,pyarrow as pa,pyarrow.parquet as pq
from spectralbridge.drone_original import fit_target_amplitudes,reference_design,reference_in_hull
P=Path(__file__).resolve().parent;R=P.parents[1];start=time.monotonic();source=R/'provenance/ruby-correction-recovery-2026-11-06/observations_enriched.csv';d=pd.read_csv(source);manifest=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/retrieval_manifest.json').read_text());sha={r['local_path']:r['sha256'] for r in manifest};d['source_photo_sha256']=d.photo_path.map(sha)
columns=['target_id','x','y','z','camera_key','master_key','wavelength_nm','timestamp_utc_scenario','observed_fraction','vendor_fraction_median','vendor_fraction_std','view_zenith_deg','view_azimuth_deg','solar_zenith_deg','solar_azimuth_deg','ross','li','quality_supported','patch_cv','master_track_reprojection_error_px','source_photo_sha256','spectral_stratum','holdout_fold','spatial_group','exposure_seconds','ISO','reflectance_factor','DLS_horizontal_irradiance','ground_dtm_chunk_slope_deg','ground_dtm_chunk_aspect_deg','ground_dtm_chunk_incidence']
table=pa.Table.from_pandas(d[columns],preserve_index=False);metadata=dict(table.schema.metadata or {});metadata.update({b'spectralbridge.reflectance_units':b'physical_reflectance_v1',b'spectralbridge.calibration_context':b'Ruby 2023 one flight; vendor calibrated, independent accuracy unverified',b'spectralbridge.status':b'EXPERIMENTAL_COMPACT_BRDF_OBSERVATIONS_NOT_APPROVED_CORRECTION',b'spectralbridge.processing_stage':b'vendor_calibrated_pre_topographic_pre_BRDF',b'spectralbridge.project_fingerprint':json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/baseline.json').read_text())['project_fingerprint'].encode(),b'spectralbridge.reference_geometry':b'{"solar_zenith_deg":45,"view_zenith_deg":0}'});pq.write_table(table.replace_schema_metadata(metadata),P/'ruby_compact_calibration.parquet',compression='zstd')
# Same data read from the compact artifact; no original photos or Metashape needed.
d=pd.read_parquet(P/'ruby_compact_calibration.parquet');d=d[d.quality_supported].copy();counts=d.groupby(['target_id','wavelength_nm']).size();eligible=set(counts[counts>=3].index);d=d[[tuple(v) in eligible for v in d[['target_id','wavelength_nm']].to_numpy()]]
reference=reference_design();configs=[dict(targets=n,views=v,design=design) for n in [8,16,32,48,64] for v in [3,5,99] for design in ['spatial','concentrated','angular']];rows=[];summaries=[];selected=[];rng=np.random.default_rng(186)

from compact_helpers import select,evaluate

full_config=dict(targets=64,views=99,design='spatial')
for outer in range(4):
 train=d[d.holdout_fold!=outer];test=d[d.holdout_fold==outer];innerfolds=sorted(train.holdout_fold.unique());inner_results=[];inner_full=[]
 for inner in innerfolds:
  s,_,_=evaluate(train[train.holdout_fold!=inner],train[train.holdout_fold==inner],full_config);s['inner']=int(inner);inner_full.append(s)
 reference_inner=pd.concat(inner_full).dropna(subset=['ratio']);reference_inner=reference_inner.set_index(['inner','target_id','wavelength_nm'])['ratio']
 for ci,config in enumerate(configs):
  scores=[];costs=[]
  for inner in innerfolds:
   s,a,_=evaluate(train[train.holdout_fold!=inner],train[train.holdout_fold==inner],config);s['inner']=int(inner);scores.append(s);costs.append(len(a))
  candidate=pd.concat(scores).dropna(subset=['ratio']).set_index(['inner','target_id','wavelength_nm'])['ratio'];common=pd.concat([reference_inner.rename('full'),candidate.rename('candidate')],axis=1).dropna();coverage=len(common)/max(1,len(reference_inner));relative=float(np.exp(np.mean(np.log(np.maximum(common.candidate,1e-12)/np.maximum(common.full,1e-12))))) if len(common) else float('inf');inner_results.append(dict(outer=outer,config=ci,**config,rows=float(np.mean(costs)),relative_cv2_geomean=relative,coverage=coverage,eligible=coverage>=.9 and relative<=1.1))
  result,calibration,betas=evaluate(train,test,config)
  for r in result.to_dict('records'):rows.append(dict(outer=outer,config=ci,**config,calibration_rows=len(calibration),**r))
  summaries.append(dict(outer=outer,config=ci,**config,calibration_rows=len(calibration),calibration_targets=int(calibration.target_id.nunique()),bytes_dataframe=int(calibration.memory_usage(deep=True).sum()),model_support=betas))
 good=[r for r in inner_results if r['eligible']];chosen=min(good,key=lambda r:(r['rows'],r['relative_cv2_geomean'])) if good else None
 selected.append(dict(outer=outer,selected=chosen,inner_choices=inner_results,outer_full_targets=int(train.target_id.nunique()),protocol='Inner 90% support and <=10% relative geometric-mean CV2 loss are predeclared study tolerances, not universal scientific thresholds'))
 print('Nested calibration outer fold',outer,'selected',chosen,flush=True)
pd.DataFrame(rows).to_csv(P/'compact_outer_results.csv',index=False);(P/'compact_models.json').write_text(json.dumps(summaries,indent=2)+'\n');(P/'compact_nested_selection.json').write_text(json.dumps(selected,indent=2)+'\n');cost=dict(compact_bytes=(P/'ruby_compact_calibration.parquet').stat().st_size,records=len(table),photo_subset_bytes=sum(r['bytes'] for r in manifest),photos=len(manifest),runtime_seconds=time.monotonic()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,calibration_contexts=1,notes='No additional independent context is present; band subsets are independent model subsets, not multiband pooling');(P/'compact_cost.json').write_text(json.dumps(cost,indent=2)+'\n');print(cost,flush=True)
