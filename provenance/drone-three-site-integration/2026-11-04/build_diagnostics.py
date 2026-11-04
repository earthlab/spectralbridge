"""Descriptive source/preparation diagnostics, never calibrated library products."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT/'archive/local/drone-three-site-integration/2026-11-04'
FIG = HERE/'figures'
FIG.mkdir(exist_ok=True)
WAVES = [444,475,531,560,650,668,705,717,740,862]


def sample(src, bands):
    scale = min(1, 750/max(src.shape))
    h,w = max(1,round(src.height*scale)),max(1,round(src.width*scale))
    a=src.read(bands,out_shape=(len(bands),h,w),resampling=Resampling.nearest).astype(float)
    mask=src.dataset_mask(out_shape=(h,w),resampling=Resampling.nearest)>0
    alpha=[i for i,c in enumerate(src.colorinterp,1) if c.name=='alpha']
    if alpha: mask &= src.read(alpha[0],out_shape=(h,w),resampling=Resampling.nearest)>0
    a[:,~mask]=np.nan
    return a


def stats(a):
    good=np.isfinite(a)
    v=a[good]
    spatial={}
    if a.ndim==2:
        for axis,label in [(0,'vertical'),(1,'horizontal')]:
            delta=np.abs(np.diff(a,axis=axis));delta=delta[np.isfinite(delta)]
            spatial[label+'_adjacent_jump_p99']=float(np.quantile(delta,.99)) if delta.size else None
    return dict(**spatial,valid=int(v.size),missing=int(a.size-v.size),minimum=float(v.min()),
                p01=float(np.quantile(v,.01)),q25=float(np.quantile(v,.25)),
                median=float(np.median(v)),q75=float(np.quantile(v,.75)),
                p99=float(np.quantile(v,.99)),maximum=float(v.max())) if v.size else dict(valid=0,missing=int(a.size))


def main():
    allrows=[];sites=[];polys=[]
    for site in ['Gordon','Goldhill','Ruby']:
        m=json.loads((HERE/f'{site.lower()}_source_manifest.json').read_text())
        original=Path(m['original_local']['path']);prepared=Path(m['prepared']['output'])
        output=WORK/'outputs'/m['flight_stem']
        with rasterio.open(original) as src, rasterio.open(prepared) as dst:
            for label,raster,mult in [('Native original',src,1.),('Prepared 10 cm',dst,65535/10000)]:
                for band,nm in enumerate(WAVES,1):
                    a=raster.read(band).astype(float)*mult
                    a[raster.read_masks(band)==0]=np.nan
                    if raster.count==11:a[raster.read(11)==0]=np.nan
                    row=dict(site=site,stage=label,band=band,wavelength_nm=nm,units='original_DN_equivalent',**stats(a))
                    allrows.append(row)
            fig,axes=plt.subplots(2,3,figsize=(11,7),layout='constrained')
            for row,(label,raster,mult) in enumerate([('Original',src,1.),('10 cm prepared',dst,65535/10000)]):
                rgb=sample(raster,[5,4,2])*mult
                rgb=np.moveaxis(np.sqrt(np.clip(rgb/16384,0,1)),0,-1)
                axes[row,0].imshow(rgb,extent=(raster.bounds.left,raster.bounds.right,raster.bounds.bottom,raster.bounds.top));axes[row,0].set_title(label+' | RGB 650/560/475 nm')
                for col,band in [(1,5),(2,8)]:
                    a=sample(raster,[band])[0]*mult
                    im=axes[row,col].imshow(a,vmin=0,vmax=16384,cmap='magma',extent=(raster.bounds.left,raster.bounds.right,raster.bounds.bottom,raster.bounds.top))
                    axes[row,col].set_title(f'{label} | {WAVES[band-1]} nm')
                for ax in axes[row]:
                    ax.set_xlim(src.bounds.left,src.bounds.right);ax.set_ylim(src.bounds.bottom,src.bounds.top);ax.set_axis_off()
            fig.colorbar(im,ax=axes[:,1:],shrink=.65,label='Original DN equivalent (not reflectance)')
            fig.suptitle(f'{site}: source and resampling only; no correction applied',fontsize=14)
            fig.savefig(FIG/f'{site.lower()}_maps.png',dpi=180);plt.close(fig)
            index=next((output/'preparation_pipeline').rglob('*__polygon_index.parquet'),None)
            if index:
                frame=pd.read_parquet(index)
                attr=[c for c in frame if c not in {'row','col','x','y','pixel_id','polygon_geometry_wkb'}]
                for pid,group in frame.groupby('polygon_id'):
                    rr,cc=group.row.to_numpy(),group.col.to_numpy()
                    r0,c0,r1,c1=int(rr.min()),int(cc.min()),int(rr.max())+1,int(cc.max())+1
                    cube=dst.read(window=Window(c0,r0,c1-c0,r1-r0))
                    values=cube[:,rr-r0,cc-c0]*np.float32(65535/10000)
                    identity={c:str(group.iloc[0][c]) for c in attr}
                    for b,nm in enumerate(WAVES):
                        polys.append({**identity,'site':site,'wavelength_nm':nm,'status':'DESCRIPTIVE_DN_NOT_APPROVED_LIBRARY',**stats(values[b])})
                m['diagnostic_polygon_pixels']=len(frame)
                m['diagnostic_polygon_count']=int(frame.polygon_id.nunique())
        sites.append(dict(site=site,flight_stem=m['flight_stem'],native_shape=m['original_local']['shape'],
                          prepared_shape=m['prepared']['shape'],polygon_pixels=m.get('diagnostic_polygon_pixels',0),
                          polygon_count=m.get('diagnostic_polygon_count',0),clipped_export=m['clipped_export']))
        print(site,'diagnostics complete',flush=True)
    df=pd.DataFrame(allrows);df.to_csv(HERE/'all_band_numeric_diagnostics.csv',index=False)
    pdf=pd.DataFrame(polys);pdf.to_csv(HERE/'polygon_dn_summaries.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(11,3.8),layout='constrained')
    for ax,site in zip(axes,['Gordon','Goldhill','Ruby']):
        for label,style in [('Native original','--'),('Prepared 10 cm','-')]:
            sub=df[(df.site==site)&(df.stage==label)]
            ax.plot(sub.wavelength_nm,sub['median'],style,label=label)
            if label=='Prepared 10 cm':ax.fill_between(sub.wavelength_nm,sub.q25,sub.q75,alpha=.2)
        ax.set(title=site,xlabel='Wavelength (nm)',ylabel='Original DN equivalent');ax.grid(alpha=.2)
    axes[-1].legend(fontsize=8)
    fig.suptitle('All ten bands: spatial distributions, not physical reflectance')
    fig.savefig(FIG/'all_band_distributions.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(11,3.8),layout='constrained')
    for ax,site in zip(axes,['Gordon','Goldhill','Ruby']):
        for _,group in pdf[pdf.site==site].groupby('polygon_id'):
            ax.plot(group.wavelength_nm,group['median'],alpha=.35,linewidth=.8)
        ax.set(title=site,xlabel='Wavelength (nm)',ylabel='Original DN equivalent');ax.grid(alpha=.2)
    fig.suptitle('Half-diameter polygons: descriptive median signals; uncalibrated')
    fig.savefig(FIG/'polygon_signals.png',dpi=180);plt.close(fig)
    (HERE/'diagnostic_summary.json').write_text(json.dumps(dict(sites=sites,physical_calibration='UNVERIFIED',
        correction_artifact_assessment='NOT_EVALUABLE: no eligible corrected products',
        display='Fixed DN 0-16384; RGB square-root stretch shared within/across sites; maps downsampled nearest for display only',
        statistics='All native/prepared pixels per band; polygon medians use indexed pixel centers; no analytical display clipping'),indent=2)+'\n')

if __name__=='__main__':main()
