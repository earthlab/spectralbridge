"""All-band native/common-support diagnostics and clearly experimental maps."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from prepare_rerun import HERE,WORK,sha,write
from correct_sites import SCALE
FIG=HERE/'figures';FIG.mkdir(exist_ok=True)
STAGES=['raw','topographic_only','brdf_only','combined']
LABELS=['Uncorrected','Topographic only','BRDF only','Combined']
WAVES=[444,475,531,560,650,668,705,717,740,862]


def samples(src,bands):
    factor=min(1,750/max(src.shape));h,w=max(1,round(src.height*factor)),max(1,round(src.width*factor))
    a=src.read(bands,out_shape=(len(bands),h,w),masked=True,resampling=Resampling.nearest).filled(np.nan)
    return a.astype('float32')*SCALE


def summary(a):
    v=np.asarray(a);v=v[np.isfinite(v)]
    if not v.size:return dict(n=0)
    q=np.quantile(v,[.01,.25,.5,.75,.99])
    return dict(n=len(v),minimum=float(v.min()),p01=float(q[0]),q25=float(q[1]),median=float(q[2]),q75=float(q[3]),p99=float(q[4]),maximum=float(v.max()),above1=int((v>1).sum()),above2=int((v>2).sum()),negative=int((v<0).sum()))


def render_support(config):
    name=config['site'];folder=WORK/name.lower()
    geometry=np.load(folder/'geometry.npy',mmap_mode='r')
    with rasterio.open(config['prepared']) as src:
        factor=max(1,int(np.ceil(max(src.shape)/750)));mask=src.dataset_mask()[::factor,::factor]>0
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    count=geometry[::factor,::factor,0].copy();zenith=geometry[::factor,::factor,1].copy();count[~mask]=np.nan;zenith[~mask]=np.nan
    image=axes[0].imshow(count,vmin=0,vmax=240,cmap='viridis');fig.colorbar(image,ax=axes[0],shrink=.7);axes[0].set_title('Potential cameras per ground pixel\n(nadir footprint scenario)')
    image=axes[1].imshow(zenith,vmin=0,vmax=30,cmap='magma');fig.colorbar(image,ax=axes[1],shrink=.7,label='Degrees from vertical');axes[1].set_title('Most-central candidate ray\n(diagnostic, not mean view angle)')
    with rasterio.open(folder/'topographic_status.tif') as src:status=src.read(5)[::factor,::factor]
    cmap=ListedColormap(['#dddddd','#ed9a3a','#238b45']);image=axes[2].imshow(status,cmap=cmap,norm=BoundaryNorm([-.5,.5,1.5,2.5],3));fig.colorbar(image,ax=axes[2],shrink=.7,ticks=[0,1,2]);axes[2].set_title('650 nm topographic support\n0 missing | 1 unsupported | 2 corrected')
    for ax in axes:ax.set_axis_off()
    fig.suptitle(name+': source-based geometry and explicit correction support')
    fig.savefig(FIG/(name.lower()+'_support.png'),dpi=160);plt.close(fig)

def main():
    statistics=[];common_rows=[];polygons=[];sites=[];validation=[]
    for config in json.loads((HERE/'site_inputs.json').read_text()):
        name=config['site'];folder=WORK/name.lower();result=json.loads((folder/'corrections_complete.json').read_text())
        paths={'raw':config['prepared']}
        bybranch={r['branch']:r for r in result['branches']}
        paths.update({r['branch']:r['geotiff'] for r in result['branches'] if r['status']=='EXECUTED_EXPERIMENTAL'})
        arrays={};profiles={};site_rows=[]
        # One band per stage at a time; no ordinary row-level population cache.
        common_all=None
        for band,nm in enumerate(WAVES,1):
            data={}
            for stage,path in paths.items():
                with rasterio.open(path) as src:
                    a=src.read(band,masked=True).filled(np.nan).astype('float32')*SCALE
                    profiles[stage]=(src.shape,src.crs,src.transform)
                data[stage]=a
                row=dict(site=name,stage=stage,band=band,wavelength_nm=nm,units='conditional DN/32768 interpretation',**summary(a))
                for axis,label in [(0,'vertical'),(1,'horizontal')]:
                    d=np.abs(np.diff(a,axis=axis));d=d[np.isfinite(d)];row[label+'_adjacent_jump_p99']=float(np.quantile(d,.99)) if len(d) else None
                if stage!='raw':
                    valid=np.isfinite(a)&np.isfinite(data['raw'])
                    ratio=np.divide(a,data['raw'],out=np.full_like(a,np.nan),where=valid&(data['raw']!=0))
                    factor=summary(ratio)
                    row.update(factor_median=factor.get('median'),factor_p99=factor.get('p99'),factor_maximum=factor.get('maximum'),paired_raw_pixels=int(valid.sum()))
                statistics.append(row);site_rows.append(row)
            common=np.logical_and.reduce([np.isfinite(a) for a in data.values()])
            common_all=common.copy() if common_all is None else common_all&common
            for stage,a in data.items():
                native=summary(a[common]);delta=summary((a-data['raw'])[common])
                common_rows.append(dict(site=name,stage=stage,wavelength_nm=nm,common_support_stages=';'.join(data),**native,delta_median=delta.get('median'),delta_p99=delta.get('p99')))
        for stage,profile in profiles.items():assert profile[0]==profiles['raw'][0] and profile[1]==profiles['raw'][1] and profile[2].almost_equals(profiles['raw'][2],precision=1e-8)
        common_path=folder/'common_available_stages_all_bands_mask.tif'
        with rasterio.open(config['prepared']) as src:
            p=src.profile.copy();p.update(count=1,dtype='uint8',nodata=None,predictor=1)
        with rasterio.open(common_path,'w',**p) as dst:
            dst.write(common_all.astype('uint8'),1);dst.update_tags(SUPPORT='All ten bands, all available accepted experimental stages; missing stages are NOT included',SCIENTIFIC_STATUS='EXPERIMENTAL')
        fig,axes=plt.subplots(3,4,figsize=(16,10),layout='constrained')
        red_im=edge_im=None
        for col,(stage,label) in enumerate(zip(STAGES,LABELS)):
            if stage not in paths:
                for row,ax in enumerate(axes[:,col]):
                    ax.text(.5,.5,'NOT PRODUCED\nBRDF prediction checks failed',ha='center',va='center',transform=ax.transAxes,color='#9a3e22',fontsize=11);ax.set_axis_off()
                axes[0,col].set_title(label);continue
            with rasterio.open(paths[stage]) as src:
                rgb=np.moveaxis(np.sqrt(np.clip(samples(src,[5,4,2])/.5,0,1)),0,-1)
                axes[0,col].imshow(rgb);axes[0,col].set_title(label)
                red_im=axes[1,col].imshow(samples(src,[5])[0],vmin=0,vmax=.4,cmap='magma')
                edge_im=axes[2,col].imshow(samples(src,[8])[0],vmin=0,vmax=1.2,cmap='viridis')
            for ax in axes[:,col]:ax.set_axis_off()
        axes[1,0].set_title('650 nm red');axes[2,0].set_title('717 nm red edge')
        fig.colorbar(red_im,ax=axes[1,:],shrink=.55,label='Conditional fractional units; display0-.4')
        fig.colorbar(edge_im,ax=axes[2,:],shrink=.55,label='Conditional fractional units; display0-1.2')
        fig.suptitle(name+': experimental rerun with supplied camera locations\nCalibration, contributors and vertical/clock conventions remain unverified',fontsize=15)
        fig.savefig(FIG/(name.lower()+'_stages.png'),dpi=160);plt.close(fig)
        render_support(config)
        index=pd.read_parquet(config['polygon_index'])
        attrs=[c for c in index.columns if c not in {'pixel_id','row','col','x','y','lon','lat','polygon_geometry_wkb'}]
        for stage,path in paths.items():
            with rasterio.open(path) as src:
                for pid,frame in index.groupby('polygon_id'):
                    rr,cc=frame.row.to_numpy(),frame.col.to_numpy();r0,c0=int(rr.min()),int(cc.min())
                    a=src.read(window=rasterio.windows.Window(c0,r0,int(cc.max())-c0+1,int(rr.max())-r0+1),masked=True).filled(np.nan)
                    a=a[:,rr-r0,cc-c0]*SCALE
                    identity={c:frame.iloc[0][c] for c in attrs}
                    for b,nm in enumerate(WAVES):polygons.append(dict(**identity,site=name,stage=stage,wavelength_nm=nm,scientific_status='EXPERIMENTAL_NOT_APPROVED_LIBRARY',**summary(a[b])))
        record=dict(site=name,branches=[dict(branch=r['branch'],status=r['status'],reason=r.get('reason')) for r in result['branches']],source_pixels=next(r['n'] for r in site_rows if r['stage']=='raw' and r['band']==5),common_all_bands_available_stage_pixels=int(common_all.sum()),common_available_stages=list(paths),researcher_polygon_count=int(index.polygon_id.nunique()),polygon_memberships=len(index),source_manifest=str(folder/'source_manifest.json'),grid_validated=True,figures=[str(FIG/(name.lower()+'_stages.png')),str(FIG/(name.lower()+'_support.png'))])
        sites.append(record)
        for branch in ['brdf_only','combined']:
            model_path=HERE/(name.lower()+'_'+branch+'_brdf_model.json')
            if model_path.exists():
                model=json.loads(model_path.read_text())
                for fit in model['validation']['fits']:
                    validation.append(dict(site=name,branch=branch,wavelength_nm=WAVES[fit['band']],status=fit['status'],reason=fit.get('reason'),eligible=fit.get('eligible'),condition_number=fit.get('condition_number'),reference_prediction=fit.get('reference_prediction'),reference_standard_error=fit.get('reference_standard_error'),uncertainty_groups=fit.get('uncertainty_groups'),unsupported_application_predictions=fit.get('unsupported_application_predictions')))
        print(name,'QA maps and all-band/polygon diagnostics complete',flush=True)
    pd.DataFrame(statistics).to_csv(HERE/'native_all_band_metrics.csv',index=False)
    pd.DataFrame(common_rows).to_csv(HERE/'common_support_all_band_metrics.csv',index=False)
    pd.DataFrame(polygons).to_csv(HERE/'experimental_polygon_summaries.csv',index=False)
    pd.DataFrame(validation).to_csv(HERE/'brdf_acceptance_by_band.csv',index=False)
    write(HERE/'qa_summary.json',sites)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    p=pd.DataFrame(polygons)
    for ax,name in zip(axes,['Gordon','Goldhill','Ruby']):
        for stage,color in [('raw','#555555'),('topographic_only','#238b45'),('brdf_only','#377eb8'),('combined','#bd5e14')]:
            sub=p[(p.site==name)&(p.stage==stage)]
            if len(sub):
                group=sub.groupby('wavelength_nm')['median'].median();ax.plot(group.index,group.values,marker='o',ms=3,label=stage,color=color)
        ax.set(title=name,xlabel='Wavelength (nm)',ylabel='Conditional fraction');ax.grid(alpha=.2)
    axes[2].legend(fontsize=7);fig.suptitle('Median of half-diameter polygon medians; per-stage support differs; no ecological gain claim')
    fig.savefig(FIG/'polygon_stage_comparison.png',dpi=170);plt.close(fig)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--support-only',action='store_true');args=parser.parse_args()
    if args.support_only:
        for config in json.loads((HERE/'site_inputs.json').read_text()):render_support(config)
    else:main()
