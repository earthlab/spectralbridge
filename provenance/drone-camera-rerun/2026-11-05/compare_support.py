"""Keep extreme corrected values traceable across native and shared support."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_rerun import HERE,WORK
from correct_sites import SCALE
from build_qa import summary,WAVES,FIG
records=[];extremes=[]
for config in json.loads((HERE/'site_inputs.json').read_text()):
    folder=WORK/config['site'].lower();out=json.loads((folder/'corrections_complete.json').read_text())
    paths={'raw':config['prepared'],**{r['branch']:r['geotiff'] for r in out['branches'] if r['status']=='EXECUTED_EXPERIMENTAL'}}
    with rasterio.open(folder/'common_available_stages_all_bands_mask.tif') as src:common=src.read(1)>0
    for stage,path in paths.items():
        with rasterio.open(path) as src,rasterio.open(config['prepared']) as raw:
            for band,nm in enumerate(WAVES,1):
                data=src.read(band,masked=True).filled(np.nan)*SCALE
                records.append(dict(site=config['site'],stage=stage,wavelength_nm=nm,common_stages=';'.join(paths),**summary(data[common])))
                if stage=='raw':continue
                original=raw.read(band,masked=True).filled(np.nan)*SCALE
                factor=np.divide(data,original,out=np.full_like(data,np.nan),where=np.isfinite(original)&(original!=0))
                for kind,values in [('signal_maximum',data),('factor_maximum',factor)]:
                    flat=int(np.nanargmax(values));row,col=np.unravel_index(flat,src.shape);x,y=src.transform*(col+.5,row+.5)
                    extremes.append(dict(site=config['site'],stage=stage,wavelength_nm=nm,kind=kind,row=row,col=col,pixel_id=flat,x=x,y=y,raw_conditional_fraction=float(original[row,col]),corrected_conditional_fraction=float(data[row,col]),factor=float(factor[row,col]),in_shared_all_band_support=bool(common[row,col]),source_raster=config['prepared'],product=path,scientific_status='EXPERIMENTAL'))
pd.DataFrame(records).to_csv(HERE/'shared_all_ten_band_metrics.csv',index=False)
pd.DataFrame(extremes).to_csv(HERE/'bounded_extreme_source_records.csv',index=False)
native=pd.read_csv(HERE/'native_all_band_metrics.csv');common=pd.DataFrame(records)
fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
colors=['#666666','#238b45','#377eb8','#bd5e14'];stages=['raw','topographic_only','brdf_only','combined'];labels=['Raw','Topo','BRDF','Both']
for col,name in enumerate(['Gordon','Goldhill','Ruby']):
    for row,nm in enumerate([650,717]):
        ax=axes[row,col]
        for i,stage in enumerate(stages):
            a=native[(native.site==name)&(native.stage==stage)&(native.wavelength_nm==nm)]
            b=common[(common.site==name)&(common.stage==stage)&(common.wavelength_nm==nm)]
            if len(a):
                ax.bar(i-.15,float(a.iloc[0]['maximum']),width=.3,color=colors[i],label='Native support' if i==0 else None)
                ax.bar(i+.15,float(b.iloc[0]['maximum']),width=.3,color=colors[i],hatch='///',edgecolor='white',label='Shared all ten bands' if i==0 else None)
        ax.set_xticks(range(4),labels);ax.set_title(name+' | '+str(nm)+' nm');ax.set_ylabel('Maximum in conditional units');ax.grid(axis='y',alpha=.2)
axes[0,0].legend(fontsize=8)
fig.suptitle('Native and shared-support maxima answer different questions\nNo analytical clipping; every native extreme remains traceable')
fig.savefig(FIG/'native_vs_shared_extremes.png',dpi=170);plt.close(fig)
print('Shared support and',len(extremes),'bounded extreme-source records saved',flush=True)
