"""In-memory-only API control for future calibrated float source replacement."""
from pathlib import Path
import json
import numpy as np,Metashape,rasterio
P=Path(__file__).resolve().parent;rows=json.loads((P/'observations_geometry.json').read_text());r=rows[0];d=Metashape.Document();d.open(r['project_path'],read_only=True,ignore_lock=True);chunk=d.chunks[0];cam=next(c for c in chunk.cameras if c.key==r['camera_key']);path=Path('/private/tmp/p184-calibrated-replacement-control.tif');shape=(cam.sensor.height,cam.sensor.width)
# Synthetic nonconstant fraction plane tests lossless API interpretation; no correction claim.
y,x=np.indices(shape);a=(.1+x*.0001+y*.00002).astype('float32')
with rasterio.open(path,'w',driver='GTiff',height=shape[0],width=shape[1],count=1,dtype='float32') as f:f.write(a,1)
original_transform=np.array([[cam.transform[i,j] for j in range(4)] for i in range(4)]);original_cal={k:getattr(cam.calibration,k) for k in ['f','cx','cy','k1','k2','k3','p1','p2']}
photo=Metashape.Photo();photo.path=str(path);cam.photo=photo
cam.sensor.normalize_sensitivity=False;cam.sensor.normalize_to_float=True;cam.sensor.black_level=[0.];cam.sensor.sensitivity=[1.]
# No raw-photo tags are copied; project camera calibration factors must also be cleared.
for key in list(cam.meta.keys()):
 if key.startswith('Reflectance'):del cam.meta[key]
print('VIGNETTING',cam.sensor.vignetting);cam.sensor.vignetting=[];cam.vignetting=None
image=cam.image();dtype={'F32':np.float32,'U16':np.uint16,'F64':np.float64}[image.data_type];out=np.frombuffer(image.tostring(),dtype).reshape(shape)
record=dict(status='IN_MEMORY_SYNTHETIC_REPLACEMENT_CONTROL',data_type=image.data_type,input_dtype=str(a.dtype),maximum_absolute_error=float(np.max(abs(out-a))),camera_transform_unchanged=bool(np.array_equal(original_transform,[[cam.transform[i,j] for j in range(4)] for i in range(4)])),calibration_unchanged=original_cal=={k:getattr(cam.calibration,k) for k in original_cal},project_saved=False,licensed_mosaic_run=False)
(P/'calibrated_photo_roundtrip.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
print('PHOTO META',dict(cam.photo.meta));print('SENSOR META',dict(cam.sensor.meta));print('SENSOR FIELDS',[x for x in dir(cam.sensor) if not x.startswith('_')]);print('CAM META',dict(cam.meta));print('ratios',out[0,0]/a[0,0],out[0,-1]/a[0,-1],out[-1,0]/a[-1,0],out[-1,-1]/a[-1,-1],out[shape[0]//2,shape[1]//2]/a[shape[0]//2,shape[1]//2])
