"""Stored-panel resubstitution and in-memory API calibration controls; never saves projects."""
import json,hashlib
from pathlib import Path
import numpy as np,Metashape
from PIL import Image
HERE=Path(__file__).resolve().parent;SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');rows=[];controls=[];originals=[]
def image_array(image):
 return np.frombuffer(image.tostring(),dtype={'U8':np.uint8,'U16':np.uint16,'F32':np.float32,'F64':np.float64}[image.data_type]).reshape(image.height,image.width,-1)[...,0]
for site in ['Ruby','Goldhill']:
 path=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if 'NOGCPS' not in p.name);before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,path.with_suffix('.files')/'0/chunk.zip',path.with_suffix('.files')/'0/0/frame.zip']};doc=Metashape.Document();doc.open(str(path),read_only=True,ignore_lock=True);chunk=doc.chunks[0]
 for camera in chunk.cameras:
  if not camera.group or camera.group.label!='Calibration images':continue
  metadata=dict(camera.meta)
  if 'ReflectancePanel/Calibration' not in metadata:
   rows.append(dict(site=site,camera_key=camera.key,label=camera.label,wavelength_nm=float(camera.photo.meta['Pix4D/CentralWavelength']),status='NO_STORED_PANEL_REFERENCE',scope='In calibration group, but no panel albedo/serial recovered for this image'))
   continue
  im=image_array(camera.image());mask=image_array(camera.mask.image()) if camera.mask else None;metadata=dict(camera.meta);expected=float(metadata['ReflectancePanel/Calibration']);valid=(mask>0) if mask is not None else np.ones(im.shape,bool);values=im[valid].astype(float)/(1 if camera.sensor.normalize_to_float else 32768)
  rows.append(dict(site=site,camera_key=camera.key,label=camera.label,wavelength_nm=float(camera.photo.meta['Pix4D/CentralWavelength']),panel_serial=metadata['ReflectancePanel/SerialNumber'],stored_panel_reflectance=expected,masked_pixels=int(valid.sum()),mean=float(values.mean()),median=float(np.median(values)),mean_minus_stored=float(values.mean()-expected),mask_recovered=mask is not None,scope='Resubstitution on the calibration panel, not independent validation'))
 # One red photo already in the repeated-target selection.
 target=next(r for r in json.loads((HERE/'tie_observations_geometry.json').read_text()) if r['site']==site and r['wavelength_nm']==650);camera=next(c for c in chunk.cameras if c.label==target['label']);photo=Path(camera.photo.path).resolve()
 with Image.open(photo) as raw_image:raw=np.asarray(raw_image).copy()
 api_raw=image_array(camera.photo.image());assert np.array_equal(raw,api_raw)
 base=image_array(camera.image()).copy();factor=camera.meta['ReflectanceFactor'];camera.meta['ReflectanceFactor']=str(float(factor)*2);doubled=image_array(camera.image()).copy();camera.meta['ReflectanceFactor']=factor;delta=doubled.astype(float)-np.minimum(base.astype(float)*2,65535)
 # Edge locations in raw and calibrated planes should remain registered.
 shifts=[]
 for cy in [120,480,840]:
  for cx in [160,640,1120]:
   patch=raw[cy-35:cy+36,cx-35:cx+36].astype(float);derivative=np.diff(patch,axis=1);best=(-float('inf'),0,0)
   for dy in range(-3,4):
    for dx in range(-3,4):
     p=base[cy-35+dy:cy+36+dy,cx-35+dx:cx+36+dx].astype(float);q=np.diff(p,axis=1);score=float(np.corrcoef(derivative.ravel(),q.ravel())[0,1])
     if score>best[0]:best=(score,dx,dy)
   shifts.append(dict(x=cx,y=cy,correlation=best[0],dx=best[1],dy=best[2]))
 controls.append(dict(site=site,camera_key=camera.key,raw_Photo_image_exact_PIL=True,reflectance_factor_double_error_quantiles=np.quantile(delta,[0,.5,1]).tolist(),raw_to_calibrated_gradient_registration=shifts,read_only=True,in_memory_control_not_saved=True))
 after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before};assert before==after;originals.append(dict(site=site,source_descriptors_unchanged=True,sha256=before))
 print(site,'panels and source-preserving radiometric controls complete',flush=True)
(HERE/'panel_validation.json').write_text(json.dumps(rows,indent=2)+'\n');(HERE/'radiometric_controls.json').write_text(json.dumps(dict(controls=controls,source_immutability=originals),indent=2)+'\n')
