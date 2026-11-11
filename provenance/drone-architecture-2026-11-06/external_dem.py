"""Small public 3DEP bare-earth comparison; no universal DEM adequacy claim."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd,rasterio
from scipy.ndimage import map_coordinates
from spectralbridge.drone_topography import terrain_geometry,solar_incidence,fit_topographic_model,topographic_factors
P=Path(__file__).resolve().parent;R=P.parents[1];source=Path('/private/tmp/p186-usgs-ruby-10m.tif');target=P/'usgs_3dep_ruby_10m.tif';shutil.copyfile(source,target);shutil.copyfile('/private/tmp/p186-usgs-service.json',P/'usgs_service_metadata.json');g=np.load(R/'archive/local/ruby-topographic-recovery-2026-11-06/common_grid.npz');b=json.loads((R/'provenance/ruby-topographic-recovery-2026-11-06/baseline.json').read_text());sz=b['solar_zenith_deg'];sa=b['solar_azimuth_deg'];maps={}
with rasterio.open(target) as src:
 assert src.crs.to_epsg()==26913 and src.res==(10.,10.)
 z=src.read(1).astype(float);z[z==src.nodata]=np.nan;geo=terrain_geometry(z,pixel_size=10);c,r=(~src.transform)*(g['x'],g['y']);coords=[r-.5,c-.5];sample=lambda a:map_coordinates(a,coords,order=1,mode='constant',cval=np.nan);slope=sample(geo['slope_deg']);asp=np.deg2rad(geo['aspect_deg']);aspect=np.rad2deg(np.arctan2(sample(np.sin(asp)),sample(np.cos(asp))))%360;ci=solar_incidence(slope,aspect,sz,sa);height=sample(z)
 maps['usgs_slope']=slope;maps['usgs_incidence']=ci;maps['usgs_elevation']=height
population=g['valid']&~g['spectral_dark']&~g['field_buffer']
for name,sl,x in [('USGS_3DEP_requested_10m',slope,ci),('Metashape_DTM_native',g['ground_dtm_chunk_sigma0_slope_deg'],g['ground_dtm_chunk_sigma0_incidence']),('Metashape_DTM_sigma3m',g['ground_dtm_chunk_sigma3_slope_deg'],g['ground_dtm_chunk_sigma3_incidence'])]:population &= np.isfinite(sl)&np.isfinite(x)&(sl>=5)&(x>0)
rows=[]
for name,sl,x in [('USGS_3DEP_requested_10m',slope,ci),('Metashape_DTM_native',g['ground_dtm_chunk_sigma0_slope_deg'],g['ground_dtm_chunk_sigma0_incidence']),('Metashape_DTM_sigma3m',g['ground_dtm_chunk_sigma3_slope_deg'],g['ground_dtm_chunk_sigma3_incidence'])]:
 for band,nm in enumerate([444,475,531,560,650,668,705,717,740,842]):
  m=fit_topographic_model(x[population],g['raw'][band][population],g['groups'][population]);app=topographic_factors(x,sl,sz,m);u=g['valid']&app['supported'];rows.append(dict(source=name,wavelength_nm=nm,common_fitting_n=int(population.sum()),C=m.get('C'),interval=m.get('C_interval'),status=m['status'],slope_median=float(np.nanmedian(sl[g['valid']])),numerical_support_fraction=float(u.sum()/g['valid'].sum()),gain_max=float(np.nanmax(app['factor'][u])) if u.any() else None))
np.savez_compressed(P/'external_dem_comparison_maps.npz',**maps);pd.DataFrame(rows).to_csv(P/'external_dem_comparison.csv',index=False)
metadata=dict(url='https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage?bbox=455625,4431900,456025,4432200&bboxSR=26913&size=40,30&imageSR=26913&format=tiff&pixelType=F32&noData=-999999&f=image&interpolation=RSP_BilinearInterpolation',retrieved='2026-11-06',bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source='USGS 3DEP Bare Earth DEM Dynamic Service, data published as of 26 October 2026 per service metadata',sampling='Requested 10m, mixed-resolution dynamic source; not a certified uniform-vintage 10m source tile',vertical_datum_comparison='Not independently reconciled; no fitted vertical offset applied',vertical_difference_quantiles=np.nanquantile(height-g['ground_dtm_chunk_sigma0_elevation'],[0,.5,1]).tolist(),scope='One Ruby crop only; comparison does not establish standard DEM sufficiency for most datasets')
(P/'external_dem_provenance.json').write_text(json.dumps(metadata,indent=2)+'\n');print(rows[4],flush=True)
