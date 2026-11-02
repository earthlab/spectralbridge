"""Render only selected spectral channels; no correction or analytical rerun."""
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio
from PIL import Image

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
SOURCE = next((ROOT/'artifacts/real_landsat_validation/neon').rglob('*brdfandtopo_corrected_envi.img'))
with rasterio.open(SOURCE) as ds:
    wave = np.fromstring(ds.tags(ns='ENVI')['wavelength'].strip('{}'), sep=',')
    definitions = {'visible': [650,550,470], 'near_infrared': [850,650,550], 'shortwave_infrared': [1650,850,650]}
    indices = sorted({int(np.argmin(abs(wave-w)))+1 for bands in definitions.values() for w in bands})
    # Exactly six source bands, not the full 426-band cube.
    arrays = ds.read(indices)
    valid = np.all(np.isfinite(arrays) & (arrays != ds.nodata), axis=0)
    images = {}
    for name, bands in definitions.items():
        rgb = []
        limits = []
        for w in bands:
            index = int(np.argmin(abs(wave-w)))+1
            a = arrays[indices.index(index)]
            lo, hi = np.percentile(a[valid], [2,98])
            # Explicit display-only per-channel stretch and gamma.
            rgb.append(np.clip((a-lo)/(hi-lo),0,1)**0.8)
            limits.append({'requested_nm':w,'actual_nm':float(wave[index-1]),'one_based_band':index,'display_p2':float(lo),'display_p98':float(hi)})
        rgba = np.dstack(rgb+[valid.astype(float)])
        out = BASE/(name+'.png')
        Image.fromarray(np.round(rgba*255).astype('uint8')).save(out)
        images[name] = {'channels_RGB':limits,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    manifest = {'source':str(SOURCE.relative_to(ROOT)), 'source_size':SOURCE.stat().st_size, 'source_mtime_ns':SOURCE.stat().st_mtime_ns, 'shape':[ds.height,ds.width], 'transform':list(ds.transform), 'crs':str(ds.crs), 'source_header_sha256':hashlib.sha256(SOURCE.with_suffix('.hdr').read_bytes()).hexdigest(), 'valid_pixels':int(valid.sum()), 'images':images,'display_only':'Per-channel 2nd-98th percentile stretch, gamma 0.8; no scientific data modified; negative finite values retained.', 'orientation':'Original raster row/column orientation; no rotation, warp or resampling.'}
(BASE/'imagery_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Contact sheet only, not the print imagery.
thumbs=[]
for name in definitions:
    im=Image.open(BASE/(name+'.png')).convert('RGB');im.thumbnail((1400,400));thumbs.append(im)
sheet=Image.new('RGB',(1400,sum(i.height for i in thumbs)), '#0B1822');y=0
for im in thumbs:sheet.paste(im,(0,y));y+=im.height
sheet.save(BASE/'contact.png')
