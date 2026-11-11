"""Internal tie-point reprojection and external-table/DEM consistency, not field truth."""
import json
from pathlib import Path
import numpy as np,pandas as pd,rasterio,Metashape
from geometry import ground_to_photo,photo_ray,point_ray_distance
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';results=[]
for site in ['Ruby','Goldhill']:
 p=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if 'NOGCPS' not in p.name);doc=Metashape.Document();doc.open(str(p),read_only=True,ignore_lock=True);chunk=doc.chunks[0];tp=chunk.tie_points;selected=[];masters=[c for c in chunk.cameras if c.transform is not None and c.master==c]
 for camera in masters[::max(1,len(masters)//24)]:
  projections=tp.projections[camera]
  for j in range(0,len(projections),max(1,len(projections)//100)):
   projection=projections[j];selected.append((camera,projection.track_id,projection.coord))
 needed={r[1] for r in selected};points={p.track_id:p.coord for p in tp.points if p.valid and p.track_id in needed};errors=[]
 for cam,key,obs in selected:
  if key in points:
   predicted=cam.project(points[key])
   if predicted is not None:errors.append((predicted-obs).norm())
 cfg=next(r for r in json.loads((PRIOR/'site_inputs.json').read_text()) if r['site']==site);old=pd.read_csv(cfg['camera_positions']);table=pd.read_parquet(HERE/'extracted'/(p.stem+'_chunk_0')/'cameras.parquet');new=table[table.aligned].copy();new['PhotoID']=new.label;merged=new.merge(old,on='PhotoID');delta=np.array([json.loads(v) for v in merged.center_project])-merged[['X','Y','Z']].to_numpy();centers=np.linalg.norm(delta,axis=1)
 targets=[r for r in json.loads((HERE/'ground_targets.json').read_text()) if r['site']==site];dem=chunk.elevations[0];ray_checks=[]
 for target in targets:
  ground=[target['x'],target['y'],target['z']];ecef=chunk.crs.unproject(Metashape.Vector(ground));cam=chunk.orthomosaic.camera(Metashape.Vector(ground[:2]));pixel,internal,_=ground_to_photo(chunk,cam,ground,Metashape);origin,direction=photo_ray(chunk,cam,pixel);world_origin=Metashape.Vector(origin.tolist());world_far=Metashape.Vector((origin+direction*500).tolist());a=Metashape.OrthoProjection.transform(world_origin,chunk.crs.geoccs,dem.projection);b=Metashape.OrthoProjection.transform(world_far,chunk.crs.geoccs,dem.projection);hit=dem.pickPoint(a,b)
  if hit is not None:ray_checks.append(float(np.linalg.norm(np.array(list(hit))-np.array(ground))))
 result=dict(site=site,estimated_camera_vs_previous_csv_n=len(centers),estimated_position_delta_m_quantiles=np.quantile(centers,[0,.5,.99,1]).tolist(),tiepoint_reprojection_n=len(errors),tiepoint_pixel_error_quantiles=np.quantile(errors,[0,.5,.9,.99,1]).tolist(),tiepoint_scope='Internal bundle observations, not independent held-out accuracy',dem_ray_intersection_n=len(ray_checks),dem_ray_vs_sampled_target_m_quantiles=np.quantile(ray_checks,[0,.5,.99,1]).tolist(),reference_location_example=list(masters[0].reference.location),markers=len(chunk.markers),project_optimize_sigma0=dict(chunk.meta).get('OptimizeCameras/sigma0'))
 results.append(result);(HERE/'geometry_validation.json').write_text(json.dumps(results,indent=2)+'\n');print(site,result,flush=True)
