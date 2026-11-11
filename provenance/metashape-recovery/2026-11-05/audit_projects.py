"""Project identity, surface lineage and panel evidence; preserves remote objects."""
import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,rasterio,Metashape
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';inventory=json.loads((HERE/'remote_inventory.json').read_text());remote={r['relative_path']:r for r in inventory['objects']};cfgs=json.loads((ROOT/'provenance/drone-camera-rerun/2026-11-05/site_inputs.json').read_text());panels=[];projects=[];selection=set()
for path in SRC.rglob('*.psx'):
 doc=Metashape.Document();doc.open(str(path),read_only=True,ignore_lock=True);chunk=doc.chunks[0];site='Ruby' if 'RUBY' in path.name else 'Goldhill';cfg=next(c for c in cfgs if c['site']==site);old=pd.read_csv(cfg['camera_positions']);new=pd.read_parquet(HERE/'extracted'/(path.stem+'_chunk_0')/'cameras.parquet');m=new[new.aligned].merge(old,left_on='label',right_on='PhotoID');difference=np.array([json.loads(s) for s in m.center_project])-m[['X','Y','Z']].to_numpy();surfaces=[]
 with rasterio.open(cfg['prepared']) as source:
  rr,cc=np.mgrid[50:source.height-50:100,50:source.width-50:100];x,y=rasterio.transform.xy(source.transform,rr.ravel(),cc.ravel());xy=list(zip(x,y));source_grid=dict(transform=list(source.transform),bounds=list(source.bounds),resolution=list(source.res))
 with rasterio.open(cfg['terrain']) as old_dem:old_z=np.array([r[0] for r in old_dem.sample(xy)])
 for e in chunk.elevations:
  surfaces.append(dict(key=e.key,label=e.label,minimum=e.min,maximum=e.max,meta=dict(e.meta),active=chunk.elevation.key==e.key))
 dem_path=path.with_suffix('.files')/'0/0/elevation/tile-0-0.tif'
 with rasterio.open(dem_path) as dem:
  z=np.array([r[0] for r in dem.sample(xy)]);valid=np.isfinite(z)&np.isfinite(old_z)&(abs(z)<10000)&(abs(old_z)<10000);dz=np.quantile((z-old_z)[valid],[0,.1,.5,.9,1]).tolist()
 descriptor_paths=[path,path.with_suffix('.files')/'project.zip']+sorted(path.with_suffix('.files').rglob('chunk.zip'))+sorted(path.with_suffix('.files').rglob('frame.zip'));fingerprint=hashlib.sha256(json.dumps([(str(p.relative_to(path.parent)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in descriptor_paths],sort_keys=True).encode()).hexdigest()
 rec=dict(site=site,project_path=str(path),project_fingerprint=fingerprint,descriptor_count=len(descriptor_paths),camera_delta_xyz_median=np.median(difference,axis=0).tolist(),camera_delta_distance_quantiles=np.quantile(np.linalg.norm(difference,axis=1),[0,.5,1]).tolist(),project_DEM_minus_previous_terrain_quantiles=dz,surfaces=surfaces,previous_original_grid=source_grid,orthomosaic=dict(chunk.orthomosaic.meta) if chunk.orthomosaic else None,markers=[dict(label=m.label,reference_enabled=m.reference.enabled,reference_location=list(m.reference.location) if m.reference.location else None,estimated_chunk=list(m.position) if m.position else None) for m in chunk.markers]);projects.append(rec)
 for camera in chunk.cameras:
  if camera.group and camera.group.label=='Calibration images':
   local=Path(camera.photo.path).resolve();rel=local.relative_to(SRC).as_posix();assert rel in remote
   record=dict(site=site,project_path=str(path),camera_key=camera.key,label=camera.label,wavelength_nm=float(camera.photo.meta['Pix4D/CentralWavelength']),photo_path=str(local),remote_path=remote[rel]['remote_path'],metadata=dict(camera.meta),sensor_normalize_sensitivity=camera.sensor.normalize_sensitivity);panels.append(record)
   # One version per site suffices for original panel photos; shared raw paths deduplicate.
   selection.add(remote[rel]['remote_path'])
(HERE/'project_identity_and_surfaces.json').write_text(json.dumps(projects,indent=2)+'\n');(HERE/'panel_metadata.json').write_text(json.dumps(panels,indent=2)+'\n')
# Also retrieve the full-resolution main mosaic tiles to bind exported original TIFFs to a project.
for r in inventory['objects']:
 if r['relative_path'].endswith('/0/0/orthomosaic/tile-0-0.tif'):selection.add(r['remote_path'])
(HERE/'panel_and_mosaic_selection.json').write_text(json.dumps(sorted(selection),indent=2)+'\n');print('Panels',len(panels),'unique panel/mosaic assets',len(selection),'GB',sum(r['bytes'] for r in inventory['objects'] if r['remote_path'] in selection)/1e9)
