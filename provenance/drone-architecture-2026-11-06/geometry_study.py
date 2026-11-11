"""Recovered-pose reference comparisons; no original photograph transfer required."""
from pathlib import Path
import json
import numpy as np,pandas as pd,Metashape
from spectralbridge.drone_original import ross_li_design,reference_design
P=Path(__file__).resolve().parent;R=P.parents[1];old=R/'provenance/metashape-recovery/2026-11-05';ruby=pd.read_csv(R/'provenance/ruby-correction-recovery-2026-11-06/observations_enriched.csv');gold=pd.read_csv(old/'tie_observations.csv');gold=gold[gold.site=='Goldhill'];data=pd.concat([ruby.assign(site='Ruby'),gold],ignore_index=True);models=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/brdf_models.json').read_text());beta=next(v['coefficients'] for v in models if v['wavelength_nm']==650 and v['model']=='multiplicative_target_amplitudes');beta=np.array(beta);ref=reference_design();rows=[]
for site,df in data[data.wavelength_nm==650].groupby('site'):
 root=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources')/('AOP-'+site.upper()+'-08-14-23');project=next(p for p in root.rglob('*.psx') if 'NOGCPS' not in p.name);doc=Metashape.Document();doc.open(str(project),read_only=True,ignore_lock=True);c=doc.chunks[0];T=c.transform.matrix;cams={cam.key:cam for cam in c.cameras};red={}
 for cam in c.cameras:
  if cam.transform is not None and cam.photo and float(dict(cam.photo.meta).get('Pix4D/CentralWavelength','nan'))==650:red[(cam.master or cam).key]=cam
 agl=[]
 for _,r in df.iterrows():
  cam=cams[int(r.camera_key)];position=c.crs.project(T.mulp(cam.center));agl.append(position.z-r.z)
 nominal_altitude=float(np.median(agl))
 for _,r in df.iterrows():
  cam=cams[int(r.camera_key)];target=c.crs.unproject(Metashape.Vector([r.x,r.y,r.z]));local=c.crs.localframe(target);origin=T.mulp(cam.center);delta=local.mulv(origin-target);ground=np.array([delta.x,delta.y,delta.z]);horizontal=np.hypot(delta.x,delta.y);nomzen=float(np.rad2deg(np.arctan2(horizontal,nominal_altitude)));nomaz=float(np.rad2deg(np.arctan2(delta.x,delta.y))%360)
  primary=c.orthomosaic.camera(Metashape.Vector([r.x,r.y]));pcam=red.get(primary.key) if primary else None
  variants=[('nadir',0.,0.),('actual_position_nominal_altitude',nomzen,nomaz)]
  if pcam:
   v=local.mulv(T.mulp(pcam.center)-target);variants.append(('retained_primary_camera',float(np.rad2deg(np.arctan2(np.hypot(v.x,v.y),v.z))),float(np.rad2deg(np.arctan2(v.x,v.y))%360)))
  actual=ross_li_design([r.solar_azimuth_deg],[r.solar_zenith_deg],[r.view_azimuth_deg],[r.view_zenith_deg])[0];actual_vector=np.array([np.sin(np.deg2rad(r.view_zenith_deg))*np.sin(np.deg2rad(r.view_azimuth_deg)),np.sin(np.deg2rad(r.view_zenith_deg))*np.cos(np.deg2rad(r.view_azimuth_deg)),np.cos(np.deg2rad(r.view_zenith_deg))])
  for name,zen,az in variants:
   unit=np.array([np.sin(np.deg2rad(zen))*np.sin(np.deg2rad(az)),np.sin(np.deg2rad(zen))*np.cos(np.deg2rad(az)),np.cos(np.deg2rad(zen))]);design=ross_li_design([r.solar_azimuth_deg],[r.solar_zenith_deg],[az],[zen])[0];record=dict(site=site,target_id=r.target_id,camera_key=int(r.camera_key),method=name,actual_view_zenith=float(r.view_zenith_deg),approx_view_zenith=zen,angular_error_degrees=float(np.rad2deg(np.arccos(np.clip(unit@actual_vector,-1,1)))),ross_error=float(design[1]-actual[1]),li_error=float(design[2]-actual[2]),primary_is_actual=pcam.key==cam.key if pcam else None,reference_status='Adjusted poses/internal reconstruction, not independent ground truth')
   if site=='Ruby':
    pa=float(actual@beta);pn=float(design@beta);record.update(conditional_shape_relative_error=(pn-pa)/pa if pa else None,conditional_normalization_relative_error=(pa/pn-1) if pn>0 and pa>0 else None,response_model='P184 shared red shape diagnostic; not accepted correction')
   rows.append(record)
  # Assume nadir orientation but retain actual image-axis heading. This changes pixel-to-ground mapping, not the view of a known fixed target.
  pixel=Metashape.Vector([r.u,r.v]);ray_cam=np.array(list(cam.calibration.unproject(pixel)));basis=np.array([[local[i,j] for j in range(3)] for i in range(3)])@np.array([[T[i,j] for j in range(3)] for i in range(3)])@np.array([[cam.transform[i,j] for j in range(3)] for i in range(3)]);axis=basis[:,0].copy();axis[2]=0;axis/=np.linalg.norm(axis);down=np.array([0,0,-1]);nominal=np.column_stack([axis,np.cross(down,axis),down]);ray=nominal@ray_cam;t=-ground[2]/ray[2];hit=ground+t*ray
  rows.append(dict(site=site,target_id=r.target_id,camera_key=int(r.camera_key),method='nominal_nadir_pose_pixel_mapping',ground_displacement_m=float(np.linalg.norm(hit[:2])),reference_status='Horizontal tangent plane at tracked target; adjusted intrinsic calibration retained; not an observed location'))
 print('Geometry reference',site,len(df),flush=True)
pd.DataFrame(rows).to_csv(P/'viewing_geometry_comparison.csv',index=False)
(P/'geometry_limits.json').write_text(json.dumps(dict(primary_weights='NOT_RECOVERED; primary-source geometry is not effective blend geometry',orientation='At a known ground point, viewing direction depends on camera center, not its rotation. Rotation matters for pixel-to-ground assignment.',independent_ground_accuracy='UNVERIFIED',goldhill_sample='P183 overlap-enriched sample, not representative census',universal_nadir_tolerance='NOT_ESTABLISHED'),indent=2)+'\n')
