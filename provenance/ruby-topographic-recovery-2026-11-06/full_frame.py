"""Bounded 10cm factor/support diagnostics; never exports corrected reflectance."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio
from scipy.ndimage import map_coordinates
from spectralbridge.drone_topography import terrain_geometry,solar_incidence,solar_visibility,topographic_factors
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';prior=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/baseline.json').read_text());models=json.loads((P/'models.json').read_text());b=json.loads((P/'baseline.json').read_text());source=Path(b['source']);sz=b['solar_zenith_deg'];sa=b['solar_azimuth_deg'];surfaces={}
for name in ['viewing_absolute','ground_dtm_chunk']:
 with rasterio.open(prior['terrain_assets'][name]['path']) as ds:
  z=ds.read(1).astype(float);z[z==ds.nodata]=np.nan;surfaces[name]=(z,ds.transform,ds.res[0])
def sample(z,tr,x,y):
 col,row=(~tr)*(x,y);return map_coordinates(z,[row-.5,col-.5],order=1,mode='constant',cval=np.nan)
terrain={}
z,tr,pixel=surfaces['ground_dtm_chunk']
for sigma in [0,3]:terrain[sigma]=(terrain_geometry(z,pixel_size=pixel,smoothing_sigma_m=sigma),tr)
configs=[(0,'existing','scsc'),(3,'combined_screened','scsc'),(3,'combined_screened','c_correction'),(3,'combined_screened','minnaert')];counts={};outputs=[];handles={}
with rasterio.open(source) as src:
 for sigma,pop,method in configs:
  key=f'dtm_sigma{sigma}_{pop}_{method}';path=OUT/(key+'__red_support.tif');profile=src.profile.copy();profile.update(count=4,dtype='float32',nodata=np.nan,compress='deflate')
  handles[key]=rasterio.open(path,'w',**profile);handles[key].descriptions=('red_factor','factor_lower_parameter_bound','factor_upper_parameter_bound','supported_status_1_unsupported_2_supported');handles[key].update_tags(role='EXPERIMENTAL_FACTOR_DIAGNOSTICS_NOT_CORRECTED_REFLECTANCE',shadow_radius_m='100',shadow_step_m='.5',source_input_sha256=b['source_sha256']);outputs.append(str(path))
  for nm in [444,475,531,560,650,668,705,717,740,842]:counts[(key,nm)]=dict(valid=0,supported=0,shadow=0,unknown_shadow=0,ci_below_zero=0,factor_min=None,factor_max=None,negative_branch_or_pole=0)
 for start in range(0,src.height,64):
  stop=min(src.height,start+64);window=rasterio.windows.Window(0,start,src.width,stop-start);raw=src.read(window=window).astype(float)*.0001;rr,cc=np.indices(raw.shape[1:]);x,y=src.transform*(cc+.5,rr+start+.5);viewz,viewtr,_=surfaces['viewing_absolute'];height=sample(viewz,viewtr,x,y)
  vis=solar_visibility(x,y,height,solar_zenith_deg=sz,solar_azimuth_deg=sa,sample_surface=lambda xx,yy:sample(viewz,viewtr,xx,yy),maximum_distance=100,step_metres=.5);sun=vis['covered']&~vis['shadow'];dark=np.mean(raw[[0,1,3,4,5]],axis=0)<.01
  for sigma,pop,method in configs:
   key=f'dtm_sigma{sigma}_{pop}_{method}';geo,tr=terrain[sigma];slope=sample(geo['slope_deg'],tr,x,y);a=np.deg2rad(geo['aspect_deg']);aspect=np.rad2deg(np.arctan2(sample(np.sin(a),tr,x,y),sample(np.cos(a),tr,x,y)))%360;ci=solar_incidence(slope,aspect,sz,sa);domain=sun if pop=='existing' else sun&~dark
   for band,nm in enumerate([444,475,531,560,650,668,705,717,740,842]):
    model=next(v for v in models if v['surface']=='ground_dtm_chunk' and v['sigma']==sigma and v['population']==pop and v['method']==method and v['strategy']=='ols' and v['wavelength_nm']==nm);app=topographic_factors(ci,slope,sz,model,geometric_sunlit=domain);valid=np.isfinite(raw[band]);supported=valid&app['supported'];r=counts[(key,nm)];r['valid']+=int(valid.sum());r['supported']+=int(supported.sum());r['shadow']+=int((valid&vis['shadow']).sum());r['unknown_shadow']+=int((valid&~vis['covered']).sum());r['ci_below_zero']+=int((valid&(ci<=0)).sum())
    if model.get('C_interval'):r['negative_branch_or_pole']+=int((valid&(ci+model['C_interval'][0]<=.001)).sum())
    if supported.any():lo=float(app['factor'][supported].min());hi=float(app['factor'][supported].max());r['factor_min']=lo if r['factor_min'] is None else min(lo,r['factor_min']);r['factor_max']=hi if r['factor_max'] is None else max(hi,r['factor_max'])
    if nm==650:
     handles[key].write(np.stack([np.where(supported,app[k],np.nan) for k in ['factor','low','high']]+[np.where(valid,np.where(supported,2,1),np.nan)]).astype('float32'),window=window)
  print('Full 10cm diagnostic rows',stop,'/',src.height,flush=True)
for ds in handles.values():ds.close()
rows=[dict(candidate=k[0],wavelength_nm=k[1],**v,numerical_support_fraction=v['supported']/v['valid']) for k,v in counts.items()];pd.DataFrame(rows).to_csv(P/'full_frame_support.csv',index=False);(P/'full_frame_products.json').write_text(json.dumps(dict(products=outputs,role='Factors and support only; no corrected reflectance',resolution_m=.1,shadow_resolution_m=.1,shadow_radius_m=100,physical_approval=False),indent=2)+'\n')
