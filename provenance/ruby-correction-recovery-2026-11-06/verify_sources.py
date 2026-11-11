"""Freeze Ruby evidence and create a distinct, explicit-scale immutable input."""
import json,hashlib,importlib.util
from pathlib import Path
import numpy as np,rasterio
from spectralbridge.drone_original import prepare_calibrated_orthomosaic
from affine import Affine
P=Path(__file__).resolve().parent;R=P.parents[1];OLD=R/'provenance/metashape-recovery/2026-11-05';CACHE=Path('/private/tmp/spectralbridge-metashape-recovery-20261105');OUT=R/'archive/local/ruby-correction-recovery-2026-11-06';OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('geometry',OLD/'geometry.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
project=next((CACHE/'sources/AOP-RUBY-08-14-23').rglob('*.psx'));files=project.with_suffix('.files');source=CACHE/'originals/ruby.tif';fingerprint=g.project_descriptor_fingerprint(project)
site=next(x for x in json.loads((R/'provenance/drone-correction-stability/2026-11-05/site_inputs.json').read_text()) if x['site']=='Ruby')
waves=[444,475,531,560,650,668,705,717,740,842]
record=prepare_calibrated_orthomosaic(source,OUT/'ruby_vendor_fraction_x10000_10cm_v1.tif',wavelengths_nm=waves,source_scale=1/32768,source_offset=0.,provenance=dict(project_fingerprint=fingerprint,chunk_key=0,source='P183 original mosaic binding and project application controls',physical_accuracy='INDEPENDENT_VALIDATION_PENDING'),target_transform=Affine(*site['transform'][:6]),target_shape=site['shape'])
assets={}
for key,name in [(0,'viewing_absolute'),(3,'ground_dtm_chunk')]:
 path=files/str(key)/'0/elevation/tile-0-0.tif'
 with rasterio.open(path) as src:
  z=src.read(1).astype(float);z[z==src.nodata]=np.nan;dy,dx=np.gradient(z,abs(src.transform.e),src.transform.a);slope=np.rad2deg(np.arctan(np.hypot(dx,dy)));aspect=np.rad2deg(np.arctan2(-dx,dy))%360
  np.savez_compressed(OUT/(name+'_terrain.npz'),elevation=z,slope_deg=slope,aspect_deg=aspect,transform=np.array(src.transform),crs=src.crs.to_string())
  assets[name]=dict(path=str(path),shape=list(src.shape),crs=src.crs.to_string(),transform=list(src.transform),elevation_range=[float(np.nanmin(z)),float(np.nanmax(z))],slope_quantiles=np.nanpercentile(slope,[0,25,50,75,95,99,100]).tolist(),project_chunk=key,role='absolute viewing surface' if key==0 else 'ground-terrain candidate from saved DTM Chunk; independent ground accuracy unverified')
a=np.load(OUT/'viewing_absolute_terrain.npz')['elevation'];b=np.load(OUT/'ground_dtm_chunk_terrain.npz')['elevation'];delta=a-b
baseline=dict(project_path=str(project),project_fingerprint=fingerprint,source=str(source),radiometric_product=record,terrain_assets=assets,view_minus_ground_height_quantiles=np.nanpercentile(delta,[0,1,25,50,75,99,100]).tolist(),baseline_site=site,primary_model=next(v for v in json.loads((OLD/'primary_mosaic_fits.json').read_text()) if v['site']=='Ruby'),production_source_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'src/spectralbridge/corrections.py',R/'src/spectralbridge/topographic.py',R/'src/spectralbridge/pipelines/drone.py']})
(P/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n');print('Immutable radiometry and baseline recorded',flush=True)
