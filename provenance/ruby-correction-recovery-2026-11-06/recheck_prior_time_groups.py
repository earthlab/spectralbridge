"""Correct P183 timestamp-resolution diagnostic without overwriting historical evidence."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from spectralbridge.drone_original import temporal_minute_groups,ross_li_design,reference_design
from spectralbridge.topographic import cluster_covariance
from spectralbridge.corrections import _brdf_predictions
P=Path(__file__).resolve().parent;R=P.parents[1];df=pd.read_csv(R/'provenance/metashape-recovery/2026-11-05/tie_observations.csv');rows=[]
for (site,target,nm),b in df.groupby(['site','target_id','wavelength_nm']):
 groups=temporal_minute_groups(b.timestamp_utc_scenario);X=ross_li_design(b.solar_azimuth_deg,b.solar_zenith_deg,b.view_azimuth_deg,b.view_zenith_deg);y=b.vendor_fraction_median.to_numpy();beta=np.linalg.lstsq(X,y,rcond=None)[0];record=dict(site=site,target_id=target,wavelength_nm=float(nm),corrected_minute_groups=len(np.unique(groups)),status='INSUFFICIENT_GROUPS')
 try:
  covariance,n=cluster_covariance(X,y-X@beta,groups);pred,ref,se,rse,valid=_brdf_predictions(X,reference_design(),beta,covariance);record.update(status='NUMERICALLY_SUPPORTED' if valid.all() else 'INVALID',reference=float(ref),reference_se=float(rse),unsupported_predictions=int((~valid).sum()))
 except ValueError as exc:record['reason']=str(exc)
 rows.append(record)
(P/'prior_temporal_group_recheck.json').write_text(json.dumps(rows,indent=2)+'\n');print(pd.DataFrame(rows).groupby(['site','status']).size().to_string())
