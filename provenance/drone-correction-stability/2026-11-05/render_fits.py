"""Readable fit plots from the saved systematic diagnostic sample."""
import json
from pathlib import Path
import numpy as np,rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';WORK=ROOT/'archive/local/drone-camera-rerun/2026-11-05/photo_clock_v1';fits=json.loads((HERE/'sampled_model_fits.json').read_text())
for cfg in json.loads((PRIOR/'site_inputs.json').read_text()):
 name=cfg['site'];folder=WORK/name.lower();train=np.load(folder/'training_mask.npy');rr,cc=np.indices(train.shape);ij=np.nonzero(train&(rr%10==0)&(cc%10==0));A=np.load(folder/'center_design.npy',mmap_mode='r')[ij];ref=np.array([1,-.04586202988221,-1]);paths={'brdf_only':cfg['prepared'],'combined':next(r['geotiff'] for r in json.loads((PRIOR/f'{name.lower()}_pipeline_results.json').read_text()) if r['branch']=='topographic_only')};fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained');fig.suptitle(name+': shared 1 m diagnostic sample (not new independent observations)')
 for row,stage in enumerate(['brdf_only','combined']):
  with rasterio.open(paths[stage]) as src:y=src.read(5)[ij]*65535/(10000*32768)
  good=np.isfinite(y)&(y>=0)&(y<=2)&np.isfinite(A).all(1);a=A[good];y=y[good];f=next(r for r in fits if r['site']==name and r['stage']==stage and r['band_nm']==650);pred=a@np.array(f['beta']);residual=y-pred
  ax=axs[row,0];sc=ax.scatter(a[:,1],a[:,2],c=y,s=1,cmap='viridis',rasterized=True);ax.scatter(ref[1],ref[2],marker='*',c='red',s=130,label='45 deg / nadir reference');ax.legend(fontsize=7);ax.set(xlabel='RossThick mixture',ylabel='LiDenseR mixture',title=stage+' | 650 nm');fig.colorbar(sc,ax=ax,label='Conditional fraction');ax.xaxis.set_major_locator(MaxNLocator(4))
  ax=axs[row,1];ax.hexbin(pred,y,gridsize=45,mincnt=1,bins='log');ax.set(xlabel='Fitted conditional fraction',ylabel='Observed conditional fraction',title=f"R2={f['r2']:.3f}; ref z={f['reference_z']:.2f}");ax.xaxis.set_major_locator(MaxNLocator(4))
  ax=axs[row,2];ax.scatter(ij[1][good],ij[0][good],c=residual,s=1,cmap='coolwarm',vmin=-.03,vmax=.03,rasterized=True);ax.invert_yaxis();ax.set(title='Spatial residuals (fixed +/-0.03)',xlabel='Column',ylabel='Row');ax.xaxis.set_major_locator(MaxNLocator(4))
 fig.savefig(HERE/'figures'/f'{name.lower()}_fit.png',dpi=160);plt.close(fig)
