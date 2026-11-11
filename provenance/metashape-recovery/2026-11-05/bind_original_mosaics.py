"""Bind previous original TIFF values to retained project mosaic tiles, read-only."""
import json
from pathlib import Path
import numpy as np,rasterio
from scipy.ndimage import map_coordinates
from geometry import open_native_orthomosaic_tile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');ORIG=SRC.parent/'originals';rows=[];FIG=HERE/'figures';FIG.mkdir(exist_ok=True)
for site in ['Goldhill','Ruby']:
 source=ORIG/(site.lower()+'.tif');paths=list((SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('tile-0-0.tif'));paths=[p for p in paths if '/0/0/orthomosaic/' in str(p)]
 if not paths:continue
 with rasterio.open(source) as original:
  rr,cc=np.mgrid[30:original.height-30:30,30:original.width-30:30];rr=rr.ravel();cc=cc.ravel();good=(original.read(11)[rr,cc]>0) if original.count==11 else (original.dataset_mask()[rr,cc]>0);rr=rr[good];cc=cc[good];x,y=rasterio.transform.xy(original.transform,rr,cc);x=np.array(x);y=np.array(y)
  for path in paths:
   variant='NOGCPS' if 'NOGCPS' in str(path) else 'WORKING'
   mask_path=path.with_name(path.stem+'-p.tif')
   with rasterio.open(mask_path) as mask_grid:expected_shape=mask_grid.shape
   with open_native_orthomosaic_tile(path,expected_shape=expected_shape) as tile:
    for offset,dx,dy in [('unshifted',0,0)]+([('pose_derived_translation',-1.57385263,1.75044979)] if variant=='NOGCPS' else []):
     inv=~tile.transform;columns=inv.a*(x+dx)+inv.b*(y+dy)+inv.c-.5;lines=inv.d*(x+dx)+inv.e*(y+dy)+inv.f-.5;inside=(columns>=2)&(columns<tile.width-3)&(lines>=2)&(lines<tile.height-3);coords=np.stack([lines[inside],columns[inside]])
     for band in range(1,11):
      mask_path=path.with_name(path.stem+'-p.tif')
      with rasterio.open(mask_path) as mask_src:codes=mask_src.read(1)[np.rint(lines[inside]).astype(int),np.rint(columns[inside]).astype(int)]
      data=tile.read(band);target=original.read(band)[rr[inside],cc[inside]].astype(float)
      for method,order in [('nearest',0),('linear',1),('cubic',3)]:
       pred=map_coordinates(data.astype('float32'),coords,order=order,prefilter=order>1).astype(float);valid=np.isfinite(target)&np.isfinite(pred)&(codes!=np.iinfo(np.uint32).max);a,b=target[valid],pred[valid];error=b-a;slope,intercept=np.polyfit(a,b,1);rows.append(dict(site=site,variant=variant,offset=offset,band=band,sampling=method,n=len(a),correlation=float(np.corrcoef(a,b)[0,1]),rmse_DN=float(np.sqrt(np.mean(error**2))),median_abs_error_DN=float(np.median(abs(error))),p99_abs_error_DN=float(np.quantile(abs(error),.99)),slope=float(slope),intercept=float(intercept),original_pixel_size=list(original.res),project_pixel_size=list(tile.res)))
      if band==5 and offset=='unshifted':
       fig,ax=plt.subplots(figsize=(5,4),layout='constrained');ax.hexbin(target,pred,gridsize=45,bins='log',mincnt=1);ax.set(xlabel='Previous original TIFF: red DN',ylabel='Stored project mosaic: red DN',title=site+' '+variant+' | fixed georeferenced samples');fig.savefig(FIG/(site.lower()+'_'+variant.lower()+'_mosaic_binding.png'),dpi=160);plt.close(fig)
   print(site,variant,'original export comparison complete',flush=True)
(HERE/'original_mosaic_binding.json').write_text(json.dumps(rows,indent=2)+'\n')
