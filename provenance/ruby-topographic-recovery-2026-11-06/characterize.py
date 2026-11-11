"""Common-grid terrain, finite-radius shadow, texture and field-context evidence."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd,rasterio,geopandas as gpd
from affine import Affine
from scipy.ndimage import map_coordinates,uniform_filter,distance_transform_edt
from rasterio.features import rasterize
from spectralbridge.drone_topography import terrain_geometry,solar_incidence,solar_visibility
P=Path(__file__).resolve().parent;R=P.parents[1];PRIOR=R/'provenance/ruby-correction-recovery-2026-11-06';OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';OUT.mkdir(parents=True,exist_ok=True)
b=json.loads((PRIOR/'baseline.json').read_text());source=R/'archive/local/ruby-correction-recovery-2026-11-06/ruby_vendor_fraction_x10000_10cm_v1.tif';d=pd.read_csv(PRIOR/'observations_enriched.csv');p183=pd.read_csv(R/'provenance/metashape-recovery/2026-11-05/tie_observations.csv');p183=p183[p183.site=='Ruby'];sz=float(p183.solar_zenith_deg.median());sa=float(p183.solar_azimuth_deg.median());waves=[444,475,531,560,650,668,705,717,740,842]
with rasterio.open(source) as src:
 raw=src.read()[:,::10,::10].astype(float)*.0001;rr,cc=np.indices(raw.shape[1:]);xx,yy=src.transform*(cc*10+.5,rr*10+.5);tr=Affine(1,0,float(xx[0,0])-.5,0,-1,float(yy[0,0])+.5);crs=src.crs
 # Physical 0.5m source-patch variability, not variable-size image footprints.
 texture=[]
 for band in [4,6,10]:
  a=src.read(band).astype(float)*.0001;good=np.isfinite(a);mu=uniform_filter(np.where(good,a,0.),5)/np.maximum(uniform_filter(good.astype(float),5),1e-9);sq=uniform_filter(np.where(good,a*a,0.),5)/np.maximum(uniform_filter(good.astype(float),5),1e-9);cv=np.sqrt(np.maximum(sq-mu*mu,0))/np.maximum(abs(mu),1e-9);texture.append(cv[::10,::10])
 texture=np.max(texture,axis=0)
arrays=dict(raw=raw,x=xx,y=yy,texture_cv=texture,solar_zenith_deg=np.array(sz),solar_azimuth_deg=np.array(sa),transform=np.array(tr))
native={};metadata={}
for name in ['viewing_absolute','ground_dtm_chunk']:
 path=Path(b['terrain_assets'][name]['path'])
 with rasterio.open(path) as src:
  z=src.read(1).astype(float);z[z==src.nodata]=np.nan;transform=src.transform;pixel=src.res[0]
 def sample(a,x=xx,y=yy,transform=transform):
  col,row=(~transform)*(x,y);return map_coordinates(a,[row-.5,col-.5],order=1,mode='constant',cval=np.nan)
 native[name]=(z,transform,pixel)
 for sigma in [0.,1.,3.,10.]:
  g=terrain_geometry(z,pixel_size=pixel,smoothing_sigma_m=sigma);key=name+'_sigma'+str(int(sigma))
  for field in ['elevation','slope_deg','curvature','roughness']:arrays[key+'_'+field]=sample(g[field])
  # Circular aspect interpolation.
  a=np.deg2rad(g['aspect_deg']);arrays[key+'_aspect_deg']=np.rad2deg(np.arctan2(sample(np.sin(a)),sample(np.cos(a))))%360
  arrays[key+'_incidence']=solar_incidence(arrays[key+'_slope_deg'],arrays[key+'_aspect_deg'],sz,sa)
  print('Terrain',key,flush=True)
# Geometry shadows: ground terrain and top-of-canopy obstruction separately; no spectral-darkness shortcut.
for name,(z,transform,pixel) in native.items():
 def sampler(x,y,z=z,transform=transform):
  col,row=(~transform)*(x,y);return map_coordinates(z,[row-.5,col-.5],order=1,mode='constant',cval=np.nan)
 visibility=solar_visibility(xx,yy,arrays[name+'_sigma0_elevation'],solar_zenith_deg=sz,solar_azimuth_deg=sa,sample_surface=sampler,maximum_distance=100,step_metres=.5)
 for field in ['shadow','covered','obstruction_m']:arrays[name+'_'+field]=visibility[field]
 print('Shadow',name,'obstructed',int(visibility['shadow'].sum()),'covered',int(visibility['covered'].sum()),flush=True)
height=arrays['viewing_absolute_sigma0_elevation']-arrays['ground_dtm_chunk_sigma0_elevation'];ndvi=(raw[9]-raw[5])/(raw[9]+raw[5]);brightness=np.mean(raw[[0,1,3,4,5]],axis=0);valid=np.isfinite(raw).all(0);stratum=np.full(valid.shape,4,np.uint8);stratum[(ndvi>.5)&(height>2)]=1;stratum[(ndvi>.5)&(height<=2)&(height>=-1)]=2;stratum[(ndvi<.2)&(height<2)&(brightness>.015)]=3;stratum[~valid]=0
arrays.update(height_above_dtm=height,ndvi=ndvi,brightness=brightness,spectral_dark=brightness<.01,stratum=stratum,valid=valid,groups=(rr//20)*100+(cc//20),fold=(rr//max(1,rr.shape[0]//2)).clip(0,1)*2+(cc//max(1,cc.shape[1]//2)).clip(0,1))
# Field polygons supply independent cover/species context, not measured reflectance.
fields=gpd.read_file(b['baseline_site']['polygons']).to_crs(crs);fields=fields[fields.intersects(__import__('shapely').geometry.box(xx.min(),yy.min(),xx.max(),yy.max()))].copy();records=[];shapes=[]
for i,(_,row) in enumerate(fields.iterrows(),1):
 shapes.append((row.geometry,i));records.append(dict(polygon_id=i,global_id=row.GlobalID,species=str(row.species),cover_category=str(row.cover_category),cover_subcategory=str(row.cover_subcategory),location=str(row.location),date=str(row.collection_date)))
poly=rasterize(shapes,out_shape=valid.shape,transform=tr,fill=0,dtype='int32') if shapes else np.zeros(valid.shape,'int32');arrays['field_polygon']=poly;arrays['field_buffer']=distance_transform_edt(poly==0)<=2
np.savez_compressed(OUT/'common_grid.npz',**arrays)
# Raw metadata from every stored surface, not the active CHM alone.
meta=[]
for chunk in [0,3]:
 f=next((R/'provenance/metashape-recovery/2026-11-05/extracted').glob(f'*RUBY*chunk_{chunk}/chunk.json'));meta.append(json.loads(f.read_text()))
(P/'surface_provenance.json').write_text(json.dumps(meta,indent=2)+'\n');(P/'field_polygon_context.json').write_text(json.dumps(records,indent=2)+'\n')
identity=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),project_fingerprint=b['project_fingerprint'],shape=list(valid.shape),sample='Every tenth 10cm pixel at its exact center; 1m spacing, not a 1m average',solar_zenith_deg=sz,solar_azimuth_deg=sa,original_photo_solar_zenith_range=[float(d.solar_zenith_deg.min()),float(d.solar_zenith_deg.max())],scales_sigma_m=[0,1,3,10],shadow_radius_m=100,shadow_step_m=.5,ground_accuracy='UNVERIFIED',strata={'1':'elevated high-NDVI canopy proxy','2':'low-height high-NDVI herbaceous proxy','3':'low-height low-NDVI exposed-surface proxy','4':'mixed/other'},field_polygons=len(records),valid=int(valid.sum()),production_hashes=b['production_source_hashes'])
(P/'baseline.json').write_text(json.dumps(identity,indent=2)+'\n');print('Common grid complete',identity['shape'],identity['field_polygons'],flush=True)
