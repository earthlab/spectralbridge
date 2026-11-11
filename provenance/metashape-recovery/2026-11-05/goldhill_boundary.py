"""Direct retained-source comparisons at the preselected historical red boundary."""
import json
from pathlib import Path
import numpy as np,rasterio,Metashape
from scipy.ndimage import distance_transform_edt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources/AOP-GOLDHILL-08-14-23');selection=json.loads((ROOT/'provenance/brdf-artifact-anatomy/2026-11-03/selection.json').read_text());y0,y1,x0,x1=selection['roi_native_indices'];cfg=next(r for r in json.loads((ROOT/'provenance/drone-camera-rerun/2026-11-05/site_inputs.json').read_text()) if r['site']=='Goldhill')
old=np.load('/private/tmp/goldhill-clean-source-brdf-20261103/old_candidate.npy',mmap_mode='r');A=np.load('/private/tmp/goldhill-clean-source-brdf-20261103/A_historical_stored.npy',mmap_mode='r');raw=np.asarray(old[y0:y1,x0:x1,4]);factor=np.asarray(A[y0:y1,x0:x1,4])*65535/(10000*32768)/raw;state=factor>1.01;valid=np.isfinite(factor)&np.isfinite(raw)&(raw>0)
with rasterio.open(cfg['prepared']) as src:
 rr,cc=np.indices(state.shape);xx,yy=rasterio.transform.xy(src.transform,rr+y0,cc+x0);xx=np.asarray(xx).reshape(state.shape);yy=np.asarray(yy).reshape(state.shape);red=src.read(5,window=rasterio.windows.Window(x0,y0,x1-x0,y1-y0))*65535/(10000*32768)
results=[];masks=[]
for variant in ['WORKING','NOGCPS']:
 path=next(p for p in SRC.rglob('*.psx') if ('NOGCPS' in p.name)==(variant=='NOGCPS'));d=Metashape.Document();d.open(str(path),read_only=True,ignore_lock=True);chunk=d.chunks[0];keys=np.full(state.shape,-1,np.int32)
 for j in range(len(rr)):
  for i in range(state.shape[1]):
   cam=chunk.orthomosaic.camera(Metashape.Vector([xx[j,i],yy[j,i]]))
   if cam:keys[j,i]=cam.key
  if j%100==0:print('Goldhill',variant,'fixed ROI row',j,'/',len(rr),flush=True)
 good=valid&(keys>=0);historical_h=(state[:,:-1]!=state[:,1:])&good[:,:-1]&good[:,1:];historical_v=(state[:-1]!=state[1:])&good[:-1]&good[1:];source_h=(keys[:,:-1]!=keys[:,1:])&good[:,:-1]&good[:,1:];source_v=(keys[:-1]!=keys[1:])&good[:-1]&good[1:];boundary=np.zeros_like(state);boundary[:,:-1]|=source_h;boundary[:-1]|=source_v;distance=distance_transform_edt(~boundary)*.1;edge_dist=np.r_[distance[:,:-1][historical_h],distance[:-1][historical_v]];count=int(historical_h.sum()+historical_v.sum());coincident=int((historical_h&source_h).sum()+(historical_v&source_v).sum());same=1-coincident/count
 rec=dict(variant=variant,ROI=selection['roi_native_indices'],historical_edges=count,retained_source_change_coincident_edges=coincident,fraction_historical_edges_same_primary_camera=same,distance_to_source_boundary_m_quantiles=np.quantile(edge_dist,[0,.5,.9,.99,1]).tolist(),source_seam_edge_density=float((source_h.sum()+source_v.sum())/(good[:,:-1].sum()+good[:-1].sum())),method='Exact 0.1m edge locations selected in P165, before recovered project inspection; primary camera API, no blending weights');results.append(rec);masks.append((variant,keys,historical_h,historical_v));np.savez_compressed(HERE/(variant.lower()+'_fixed_boundary_sources.npz'),primary_key=keys,historical_h=historical_h,historical_v=historical_v)
fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained');im=axes[0].imshow(red,cmap='magma',vmin=0,vmax=.3);fig.colorbar(im,ax=axes[0],shrink=.7);axes[0].set_title('Uncorrected red: fixed historical ROI')
for ax,(variant,keys,h,v) in zip(axes[1:],masks):
 ax.imshow(np.where(keys>=0,keys,np.nan),cmap='tab20');ax.contour(state,levels=[.5],colors=['white'],linewidths=.7);ax.set_title(variant+' primary source\nwhite: historical gain-switch boundary')
for ax in axes:ax.set_axis_off()
fig.suptitle('A retained source-change map does not explain the historical millionfold BRDF jump');fig.savefig(HERE/'figures/goldhill_boundary_sources.png',dpi=170);plt.close(fig);(HERE/'goldhill_boundary_comparison.json').write_text(json.dumps(results,indent=2)+'\n');print(results,flush=True)
