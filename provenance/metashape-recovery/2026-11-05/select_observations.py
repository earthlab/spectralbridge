"""Select repeated Ruby/GH ground targets using official calibrated projections."""
import json,sys
from pathlib import Path
import numpy as np,pandas as pd,rasterio,Metashape
from geometry import ground_to_photo,photo_ray,viewing_angles,point_ray_distance
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';inventory=json.loads((HERE/'remote_inventory.json').read_text());remote_by_relative={r['relative_path']:r for r in inventory['objects']};records=[];targets=[];selection=set();checks=[]
for site in ['Ruby','Goldhill']:
 cfg=next(c for c in json.loads((PRIOR/'site_inputs.json').read_text()) if c['site']==site);project=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if 'NOGCPS' not in p.name);doc=Metashape.Document();doc.open(str(project),read_only=True,ignore_lock=True);chunk=doc.chunks[0];T=chunk.transform.matrix
 dem_path=project.with_suffix('.files')/'0/0/elevation/tile-0-0.tif'
 with rasterio.open(cfg['prepared']) as src:mask=src.dataset_mask()>0;transform=src.transform;shape=src.shape
 with rasterio.open(dem_path) as dem:
  # Fixed 4x3 target lattice over the prior validated source crop; no response tuning.
  choices=[(int(shape[0]*fy),int(shape[1]*fx)) for fy in [.2,.5,.8] for fx in [.15,.38,.62,.85]]
  for index,(row,col) in enumerate(choices):
   if not mask[row,col]:continue
   x,y=rasterio.transform.xy(transform,row,col);z=float(next(dem.sample([(x,y)]))[0]);ground=[x,y,z];ecef=chunk.crs.unproject(Metashape.Vector(ground));enu=chunk.crs.localframe(ecef);R=np.array([[enu[i,j] for j in range(3)] for i in range(3)]);target_id=site.lower()+'_'+str(index);master=None
   try:master=chunk.orthomosaic.camera(Metashape.Vector([x,y]))
   except Exception:pass
   target=dict(site=site,target_id=target_id,row=row,col=col,x=x,y=y,z=z,dem_source=str(dem_path),retained_primary_camera_key=master.key if master else None);targets.append(target)
   candidates=[]
   for camera in chunk.cameras:
    if camera.transform is None or camera.photo is None:continue
    wavelength=float(dict(camera.photo.meta).get('Pix4D/CentralWavelength','nan'))
    if wavelength!=650:continue
    uv,internal,geoc=ground_to_photo(chunk,camera,ground,Metashape)
    if uv is None or not (20<=uv.x<camera.sensor.width-20 and 20<=uv.y<camera.sensor.height-20):continue
    origin,ray=photo_ray(chunk,camera,uv);distance,forward=point_ray_distance(np.array(list(ecef)),origin,ray)
    if not forward:continue
    zen,az=viewing_angles(origin,np.array(list(ecef)),R);candidates.append((float(az),float(zen),camera,uv,float(distance)))
   # Eight azimuth sectors: take the largest available zenith within each, fixed rule.
   picked=[]
   for sector in range(8):
    group=[r for r in candidates if int(r[0]//45)==sector]
    if group:picked.append(max(group,key=lambda r:r[1]))
   for az,zen,camera,uv,err in picked:
    exposure_master=camera.master if camera.master is not None else camera
    # All ten bands for three Ruby targets; red elsewhere and at Goldhill.
    siblings=[cam for cam in chunk.cameras if cam.transform is not None and ((cam.master if cam.master is not None else cam).key==exposure_master.key)] if site=='Ruby' and index in [1,5,9] else [camera]
    for cam in siblings:
     pixel,_,_=ground_to_photo(chunk,cam,ground,Metashape)
     if pixel is None or not (5<=pixel.x<cam.sensor.width-5 and 5<=pixel.y<cam.sensor.height-5):continue
     photo=Path(cam.photo.path).resolve();relative=photo.relative_to(SRC).as_posix()
     if relative not in remote_by_relative:raise ValueError('Referenced photograph absent from inventory: '+relative)
     selection.add(remote_by_relative[relative]['remote_path']);o,d=photo_ray(chunk,cam,pixel);v,a=viewing_angles(o,np.array(list(ecef)),R);rayerr,fwd=point_ray_distance(np.array(list(ecef)),o,d)
     records.append(dict(**target,camera_key=cam.key,label=cam.label,sensor_key=cam.sensor.key,wavelength_nm=float(cam.photo.meta['Pix4D/CentralWavelength']),photo_path=str(photo),remote_path=remote_by_relative[relative]['remote_path'],u=pixel.x,v=pixel.y,view_zenith_deg=float(v),view_azimuth_deg=float(a),ray_target_distance_m=float(rayerr),camera_ecef=o.tolist(),camera_meta=dict(cam.meta),photo_meta=dict(cam.photo.meta)))
   print(site,target_id,'geometric red candidates',len(candidates),'selected exposures',len(picked),flush=True)
 (HERE/'overlap_observations_geometry.json').write_text(json.dumps(records,indent=2)+'\n');(HERE/'ground_targets.json').write_text(json.dumps(targets,indent=2)+'\n');(HERE/'photo_selection.json').write_text(json.dumps(sorted(selection),indent=2)+'\n')
print('Selected unique photos',len(selection),'GB',sum(r['bytes'] for r in inventory['objects'] if r['remote_path'] in selection)/1e9,flush=True)
