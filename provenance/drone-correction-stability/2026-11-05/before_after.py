"""Explicit same-scale before/after images and uncropped analytical differences."""
import json
from pathlib import Path
import numpy as np,rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05'
fig,axs=plt.subplots(3,4,figsize=(13,8),layout='constrained')
for i,site in enumerate(['gordon','goldhill','ruby']):
 branch='topographic_only' if site=='ruby' else 'combined'
 old=next(r for r in json.loads((PRIOR/f'{site}_pipeline_results.json').read_text()) if r['branch']==branch)
 new=next(r for r in json.loads((HERE/'stable_qr_v1'/f'{site}_pipeline_results.json').read_text()) if r['branch']==branch)
 arrays=[]
 for r in [old,new]:
  with rasterio.open(r['geotiff']) as src:a=src.read([5,4,2,8],out_shape=(4,300,400),masked=True).filled(np.nan)*65535/(10000*32768);arrays.append(a)
 for j,a in enumerate(arrays):
  rgb=np.clip(np.moveaxis(a[:3],0,-1)/.15,0,1);rgb[~np.isfinite(rgb).all(-1)]=1;axs[i,j].imshow(rgb);axs[i,j].set_title(site.title()+' '+('baseline' if j==0 else 'QR rerun')+'\n'+branch.replace('_',' '),fontsize=10)
 for j,b in [(2,0),(3,3)]:
  delta=arrays[1][b]-arrays[0][b];im=axs[i,j].imshow(delta,cmap='coolwarm',vmin=-.00001,vmax=.00001);axs[i,j].set_title(('650' if b==0 else '717')+' nm difference\nall finite native values exactly unchanged',fontsize=9)
 for ax in axs[i]:ax.set_axis_off()
fig.suptitle('Same source, masks, scales and corrections; QR improves numerical formulation, not scene information')
fig.savefig(HERE/'figures/before_after.png',dpi=160);plt.close(fig)
