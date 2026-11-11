"""Common-polygon software controls, not unmeasured corrected-level accuracy."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio,geopandas as gpd
from rasterio.features import rasterize
P=Path(__file__).resolve().parent;R=P.parents[1];b=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/baseline.json').read_text());fields=gpd.read_file(b['baseline_site']['polygons'])
source=R/'archive/local/ruby-correction-recovery-2026-11-06/ruby_vendor_fraction_x10000_10cm_v1.tif'
with rasterio.open(source) as src:
 a=src.read().astype(np.float32)*.0001;g=fields.to_crs(src.crs);g=g[g.intersects(__import__('shapely').geometry.box(*src.bounds))].copy();g['id']=np.arange(1,len(g)+1);grid=rasterize(zip(g.geometry,g.id),out_shape=src.shape,transform=src.transform,fill=0,dtype='int32')
common_valid=np.isfinite(a).all(0)&np.isfinite(a[:,::-1,:]).all(0)
rows=[]
for name,data in [('verified_calibrated_input',a),('fixed_range_misread_as_divide_10000',a*(32768/65535)),('controlled_vertical_reflection',a[:,::-1,:])]:
 for _,f in g.iterrows():
  mask=(grid==f.id)&common_valid;values=data[:,mask].T;valid=np.isfinite(values).all(1);values=values[valid]
  if not len(values):continue
  mean=values.mean(0);sd=values.std(0);row=dict(configuration=name,polygon_id=int(f.id),global_id=f.GlobalID,cover_category=str(f.cover_category),species=str(f.species),pixels=len(values),mean_band_cv=float(np.mean(sd/np.maximum(abs(mean),1e-8))),ndvi=float((mean[9]-mean[5])/(mean[9]+mean[5])),reference='Raw calibrated source, not independent ground reflectance')
  for i,nm in enumerate([444,475,531,560,650,668,705,717,740,842]):row['rho_'+str(nm)]=float(mean[i])
  rows.append(row)
d=pd.DataFrame(rows);means=[];bandcols=['rho_'+str(n) for n in [444,475,531,560,650,668,705,717,740,842]];reference=d[d.configuration=='verified_calibrated_input'].set_index('polygon_id')
for name,g in d.groupby('configuration'):
 common=g.set_index('polygon_id').join(reference[bandcols],rsuffix='_reference',how='inner');x=common[bandcols].to_numpy();y=common[[c+'_reference' for c in bandcols]].to_numpy();angles=np.rad2deg(np.arccos(np.clip(np.einsum('ij,ij->i',x,y)/(np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1)),-1,1)))
 labels=g.cover_category.to_numpy();eligible=pd.Series(labels).value_counts();classes=eligible[eligible>=3].index;keep=np.isin(labels,classes);spectra=g[bandcols].to_numpy()[keep];labels=labels[keep];overall=spectra.mean(0);within=0.;between=0.
 for label in np.unique(labels):
  v=spectra[labels==label];center=v.mean(0);within+=float(np.sum((v-center)**2));between+=len(v)*float(np.sum((center-overall)**2))
 means.append(dict(configuration=name,polygons=g.polygon_id.nunique(),pixel_spectra=int(g.pixels.sum()),median_within_polygon_cv=float(g.mean_band_cv.median()),median_spectral_angle_to_verified_degrees=float(np.median(angles)),mean_absolute_reflectance_error=float(np.mean(abs(x-y))),cover_between_within_scatter_ratio=between/within if within else None,cover_labels=list(classes),interpretation='Field-assigned cover labels, not automatically inferred classes; controlled software comparisons only'))
d.to_csv(P/'polygon_common_support.csv',index=False);(P/'polygon_metrics.json').write_text(json.dumps(means,indent=2)+'\n');print(means,flush=True)
