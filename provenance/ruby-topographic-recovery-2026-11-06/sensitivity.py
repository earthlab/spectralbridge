"""Source registration/height/solar scenarios, field strata and matched comparisons."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio
from scipy.ndimage import map_coordinates,gaussian_filter
from spectralbridge.drone_topography import terrain_geometry,solar_incidence,fit_topographic_model
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';g=np.load(OUT/'common_grid.npz');b=json.loads((P/'baseline.json').read_text());old=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/baseline.json').read_text());rng=np.random.default_rng(1851)
with rasterio.open(old['terrain_assets']['ground_dtm_chunk']['path']) as src:z=src.read(1).astype(float);z[z==src.nodata]=np.nan;tr=src.transform;pixel=src.res[0]
def sample(a,dx=0,dy=0):
 col,row=(~tr)*(g['x']+dx,g['y']+dy);return map_coordinates(a,[row-.5,col-.5],order=1,mode='constant',cval=np.nan)
rows=[]
for label,dx,dy,amp,dsz,dsa in [('baseline',0,0,0,0,0),('east_plus_0.5m',.5,0,0,0,0),('east_minus_0.5m',-.5,0,0,0,0),('north_plus_0.5m',0,.5,0,0,0),('north_minus_0.5m',0,-.5,0,0,0),('correlated_elevation_0.1m',0,0,.1,0,0),('correlated_elevation_0.5m',0,0,.5,0,0),('zenith_plus_0.25deg',0,0,0,.25,0),('zenith_minus_0.25deg',0,0,0,-.25,0),('azimuth_plus_0.25deg',0,0,0,0,.25)]:
 error=gaussian_filter(rng.normal(size=z.shape),2/pixel);error/=np.nanstd(error);geo=terrain_geometry(z+amp*error,pixel_size=pixel);sl=sample(geo['slope_deg'],dx,dy);az=np.deg2rad(geo['aspect_deg']);asp=np.rad2deg(np.arctan2(sample(np.sin(az),dx,dy),sample(np.cos(az),dx,dy)))%360;ci=solar_incidence(sl,asp,b['solar_zenith_deg']+dsz,b['solar_azimuth_deg']+dsa);use=g['valid']&(sl>=5)&(ci>0)&~g['field_buffer'];m=fit_topographic_model(ci[use],g['raw'][4][use],g['groups'][use]);rows.append(dict(scenario=label,C=m.get('C'),C_interval=m.get('C_interval'),status=m['status'],interpretation='Explicit sensitivity scenario, not measured DEM or clock error'))
(P/'input_sensitivity.json').write_text(json.dumps(rows,indent=2)+'\n')
# Field-labelled cover context, distinct from independently measured reflectance.
fields=json.loads((P/'field_polygon_context.json').read_text());fieldrows=[]
for f in fields:
 mask=(g['field_polygon']==f['polygon_id'])&g['valid']
 if not mask.any():continue
 counts=np.bincount(g['stratum'][mask],minlength=5);fieldrows.append(dict(**f,pixels=int(mask.sum()),median_ndvi=float(np.nanmedian(g['ndvi'][mask])),median_height_proxy=float(np.nanmedian(g['height_above_dtm'][mask])),canopy_proxy_fraction=float(counts[1]/mask.sum()),herbaceous_proxy_fraction=float(counts[2]/mask.sum()),exposed_proxy_fraction=float(counts[3]/mask.sum())))
pd.DataFrame(fieldrows).to_csv(P/'field_stratum_validation.csv',index=False)
# Identical paired support across methods; compare combined to BRDF-only too.
d=pd.read_csv(P/'matched_holdouts.csv');d['combined_to_brdf_variance']=(d.combined_cv/d.brdf_cv)**2;d.to_csv(P/'matched_comparisons.csv',index=False);pivot=d.pivot_table(index=['sigma','population','fold','target_id','wavelength_nm'],columns='method',values='combined_variance_ratio');paired=pivot.dropna();paired.to_csv(P/'matched_common_support.csv')
# Spatial dependence summaries are descriptive; block count is not certified independence.
y=g['raw'][4];mask=g['valid'];a=y[:,:-1];c=y[:,1:];choose=mask[:,:-1]&mask[:,1:];autocorr=float(np.corrcoef(a[choose],c[choose])[0,1]);stats=[]
for i in range(1,5):
 use=mask&(g['stratum']==i)&np.isfinite(g['ground_dtm_chunk_sigma0_incidence']);xx=g['ground_dtm_chunk_sigma0_incidence'][use];yy=y[use];stats.append(dict(stratum=i,n=int(use.sum()),spatial_blocks=len(np.unique(g['groups'][use])),incidence_range=np.quantile(xx,[0,.5,1]).tolist() if len(xx) else None,red_incidence_correlation=float(np.corrcoef(xx,yy)[0,1]) if len(xx)>2 else None))
(P/'dependence_summary.json').write_text(json.dumps(dict(adjacent_1m_red_correlation=autocorr,spatial_uncertainty_blocks=len(np.unique(g['groups'][mask])),spatial_folds=4,original_flight_calibration_sets=1,strata=stats,effective_independent_observations='Not identifiable from neighbour count; block covariance is conditional on supplied blocks'),indent=2)+'\n');print('Sensitivity and paired comparisons complete')
