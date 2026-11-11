"""Per-band input radiometry, spatial contract and unchanged production checks."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd,rasterio
from affine import Affine
P=Path(__file__).resolve().parent;R=P.parents[1];b=json.loads((P/'baseline.json').read_text());path=R/'archive/local/ruby-correction-recovery-2026-11-06/ruby_vendor_fraction_x10000_10cm_v1.tif';rows=[]
with rasterio.open(path) as src:
 spatial=dict(shape=list(src.shape),crs=src.crs.to_string(),transform=list(src.transform),matches_established_processing_grid=src.shape==tuple(b['baseline_site']['shape']) and src.transform==Affine(*b['baseline_site']['transform'][:6]),scale=list(src.scales),offset=list(src.offsets),mask_valid=int((src.dataset_mask()>0).sum()),independent_geolocation_accuracy='UNVERIFIED')
 for band,nm in enumerate(b['radiometric_product']['configuration']['wavelengths_nm'],1):
  a=src.read(band).astype(float)*src.scales[band-1]+src.offsets[band-1];good=np.isfinite(a);v=a[good];rows.append(dict(wavelength_nm=nm,valid=int(good.sum()),nodata=int((~good).sum()),negative=int((v<0).sum()),above_one=int((v>1).sum()),minimum=float(v.min()),maximum=float(v.max()),q01=float(np.quantile(v,.01)),median=float(np.median(v)),q99=float(np.quantile(v,.99))))
pd.DataFrame(rows).to_csv(P/'input_radiometry_by_band.csv',index=False)
unchanged={name:hashlib.sha256(Path(name).read_bytes()).hexdigest()==value for name,value in b['production_source_hashes'].items()};spatial['production_sources_unchanged']=unchanged
(P/'product_validation.json').write_text(json.dumps(spatial,indent=2)+'\n');assert spatial['matches_established_processing_grid'] and all(unchanged.values());print('Input spatial contract and production source hashes verified')
