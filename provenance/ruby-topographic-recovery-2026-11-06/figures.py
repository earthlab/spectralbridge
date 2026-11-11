"""Reproduce twelve publication-resolution scientific diagnostic figures."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path(__file__).resolve().parent;R=P.parents[1];F=P/'figures';F.mkdir(exist_ok=True);OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';g=np.load(OUT/'common_grid.npz');models=json.loads((P/'models.json').read_text());cv=pd.read_csv(P/'spatial_holdouts.csv');matched=pd.read_csv(P/'matched_comparisons.csv');mask=g['valid'];plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):fig.savefig(F/(name+'.png'),dpi=220,bbox_inches='tight');plt.close(fig)
def image(ax,array,title,cmap='viridis',vmin=None,vmax=None):
 im=ax.imshow(np.where(mask,array,np.nan),cmap=cmap,vmin=vmin,vmax=vmax);ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([]);plt.colorbar(im,ax=ax,shrink=.7)
def get(surface='ground_dtm_chunk',sigma=0,pop='existing',method='scsc',nm=650):return next(v for v in models if v['surface']==surface and v['sigma']==sigma and v['population']==pop and v['method']==method and v['strategy']=='ols' and v['wavelength_nm']==nm)
# 1: physical roles, same extent and elevation scales.
fig,axs=plt.subplots(2,3,figsize=(13,7))
for ax,key,title in zip(axs[0],['viewing_absolute_sigma0_elevation','ground_dtm_chunk_sigma0_elevation','height_above_dtm'],['Absolute viewing surface (m)','Ground DTM candidate (m)','Viewing minus ground height (m)']):image(ax,g[key],title,vmin=2710 if 'elevation' in key else -5,vmax=2810 if 'elevation' in key else 30)
image(axs[1,0],g['viewing_absolute_sigma0_slope_deg'],'Viewing-surface local slope (degrees)',vmin=0,vmax=85);image(axs[1,1],g['ground_dtm_chunk_sigma0_slope_deg'],'Ground-DTM local slope (degrees)',vmin=0,vmax=85);image(axs[1,2],g['ground_dtm_chunk_sigma3_slope_deg'],'Ground slope after declared 3m sigma',vmin=0,vmax=85);fig.suptitle('1 | Recovered surfaces have different roles; neither has independently verified accuracy');fig.tight_layout();save(fig,'01_terrain')
# 2: illumination and finite-radius visibility.
fig,axs=plt.subplots(2,3,figsize=(13,7));image(axs[0,0],g['viewing_absolute_sigma0_incidence'],'Viewing-surface cos(i)',vmin=-.2,vmax=1);image(axs[0,1],g['ground_dtm_chunk_sigma0_incidence'],'Ground-DTM cos(i)',vmin=-.2,vmax=1);image(axs[0,2],g['ground_dtm_chunk_sigma0_aspect_deg'],'Ground aspect, clockwise from north','twilight',0,360);image(axs[1,0],g['viewing_absolute_shadow'],'Canopy-surface obstruction, 100m radius','Reds',0,1);image(axs[1,1],g['ground_dtm_chunk_shadow'],'Ground-terrain obstruction, 100m radius','Reds',0,1);axs[1,2].hist(g['ground_dtm_chunk_sigma0_incidence'][mask],bins=30,alpha=.6,label='Ground DTM');axs[1,2].hist(g['viewing_absolute_sigma0_incidence'][mask],bins=30,alpha=.5,label='Viewing surface');axs[1,2].set(xlabel='cos(i)',ylabel='Sampled locations');axs[1,2].legend();fig.suptitle('2 | Terrain and canopy obstruction are distinct from spectral darkness');fig.tight_layout();save(fig,'02_illumination')
# 3: fitting regression and poles.
m=get();ci=g['ground_dtm_chunk_sigma0_incidence'];y=g['raw'][4];choose=mask&(ci>0)&(g['ground_dtm_chunk_sigma0_slope_deg']>=5)&~g['field_buffer'];fig,axs=plt.subplots(1,3,figsize=(14,4));sc=axs[0].scatter(ci[choose],y[choose],c=g['stratum'][choose],s=2,alpha=.25,rasterized=True,cmap='tab10');xx=np.linspace(ci[choose].min(),ci[choose].max(),200);a,b=m['beta'];axs[0].plot(xx,a*xx+b,'k',lw=2);axs[0].set(xlabel='Ground cos(i)',ylabel='Red fraction',title=f'Field-excluded refit: C={m["C"]:.3f}');axs[1].hist(ci[mask],bins=50);axs[1].axvline(-m['C'],c='red',label='Point-estimate pole');lo,hi=m['C_interval'];axs[1].axvspan(-hi,-lo,color='red',alpha=.2,label='Uncertain pole interval');axs[1].set(xlabel='cos(i)',ylabel='Locations');axs[1].legend(fontsize=8);image(axs[2],ci+lo,'Lowest denominator across C interval','coolwarm',-.2,1);fig.suptitle('3 | Negative intercept/slope ratio and the application denominator are separate questions');fig.tight_layout();save(fig,'03_negative_C')
# 4: heterogeneity/proxies and withheld field footprints.
fig,axs=plt.subplots(2,3,figsize=(13,7));image(axs[0,0],g['ndvi'],'Raw NDVI proxy',vmin=0,vmax=1);image(axs[0,1],g['texture_cv'],'0.5m patch variability (CV)',vmin=0,vmax=1);image(axs[0,2],g['stratum'],'Descriptive strata (not ground truth)\n1 canopy | 2 herb | 3 exposed | 4 mixed','tab10',0,4);image(axs[1,0],g['field_polygon']>0,'Withheld field polygons (86 overlap)','Greens',0,1);image(axs[1,1],g['brightness'],'Visible brightness',vmin=0,vmax=.15);field=pd.read_csv(P/'field_stratum_validation.csv');axs[1,2].scatter(field.median_ndvi,field.median_height_proxy,c=field.canopy_proxy_fraction,cmap='viridis');axs[1,2].set(xlabel='Field polygon median NDVI',ylabel='Height proxy (m)',title='Cover context, not reflectance truth');fig.suptitle('4 | Proxy classes and field context retain ecological and registration uncertainty');fig.tight_layout();save(fig,'04_heterogeneity')
# 5: geometry/darkness cross-tab plus screening effects.
fig,axs=plt.subplots(1,3,figsize=(13,4));image(axs[0],g['spectral_dark'],'Spectral darkness (visible mean <0.01)','Greys',0,1);table=np.array([[int((mask&(g['viewing_absolute_shadow']==s)&(g['spectral_dark']==d)).sum()) for d in [0,1]] for s in [0,1]]);axs[1].imshow(table,cmap='Blues');axs[1].set(xticks=[0,1],xticklabels=['Bright','Dark'],yticks=[0,1],yticklabels=['Not obstructed','Obstructed'],title='Independent diagnostics, not synonyms')
for i in range(2):
 for j in range(2):axs[1].text(j,i,str(table[i,j]),ha='center',va='center')
pops=['existing','geometric_sunlit','spectral_screened','combined_screened','homogeneous_sunlit'];vals=[get(pop=p)['C'] for p in pops];axs[2].barh(pops,vals,color='teal');axs[2].axvline(0,c='black',lw=.5);axs[2].set(xlabel='Red C (native ground DTM)',title='Screening changes fitting population');fig.suptitle('5 | Shadow screening changes C without forcing its sign');fig.tight_layout();save(fig,'05_shadows')
# 6: complete scale sensitivity.
fig,axs=plt.subplots(1,2,figsize=(13,4.5))
for ax,surface in zip(axs,['ground_dtm_chunk','viewing_absolute']):
 for pop in ['existing','combined_screened','homogeneous_sunlit','canopy_proxy','exposed_proxy']:
  records=[get(surface=surface,sigma=s,pop=pop) for s in [0,1,3,10]];values=[r.get('C',np.nan) for r in records];ax.plot([0,1,3,10],values,'o-',label=pop)
  for scale,r in zip([0,1,3,10],records):
   if r.get('C_interval'):lo,hi=r['C_interval'];ax.vlines(scale,lo,hi,alpha=.25,lw=1)
 ax.set_yscale('symlog',linthresh=.1)
 ax.axhline(0,c='black',lw=.5);ax.set(title=surface,xlabel='Gaussian sigma (m), predeclared',ylabel='Red C');ax.legend(fontsize=7)
fig.suptitle('6 | Scale and population sensitivity; no scale selected just to make C positive');fig.tight_layout();save(fig,'06_sensitivity')
# 7: known truth synthetic recovery.
syn=pd.read_csv(P/'synthetic_recovery.csv');fig,ax=plt.subplots(figsize=(13,6));names=list(syn.scenario.unique());ax.boxplot([syn[syn.scenario==s].C.dropna() for s in names],tick_labels=names,vert=False,showfliers=False);ax.axvline(.2,c='teal',label='Known C=+0.2 (except negative control)');ax.axvline(-.1,c='gray',ls='--',label='Known negative-C control');ax.set(xlabel='Recovered C',title='7 | Correct estimator + confounded brightness can produce negative C');ax.legend(fontsize=8);fig.tight_layout();save(fig,'07_identifiability')
# 8: alternatives on common original-target support.
paired=pd.read_csv(P/'matched_common_support.csv');sel=paired[(paired.sigma==0)&(paired.population=='existing')];fig,axs=plt.subplots(1,2,figsize=(12,4.5));methods=['scsc','c_correction','minnaert'];axs[0].boxplot([sel[m].dropna() for m in methods],tick_labels=methods,showfliers=False);axs[0].axhline(1,c='red',ls='--');axs[0].set(ylabel='Combined/raw CV-squared ratio',title='Identical paired target-band-fold cases');full=pd.read_csv(P/'full_frame_support.csv');red=full[full.wavelength_nm==650];axs[1].barh(range(len(red)),red.numerical_support_fraction);axs[1].set(yticks=range(len(red)),yticklabels=['Native SCS+C','3m SCS+C','3m C correction','3m Minnaert'],xlabel='10cm numerical support fraction',xlim=(0,1));fig.suptitle('8 | Alternatives change assumptions; bounded gains alone do not establish validity');fig.tight_layout();save(fig,'08_alternatives')
# 9: spatial holdout terrain comparison, identical strata per row with own-domain n reported.
sel=cv[(cv.surface=='ground_dtm_chunk')&(cv.sigma==3)&(cv.wavelength_nm==650)&(cv.strategy=='ols')&(cv.population.isin(pops))];fig,ax=plt.subplots(figsize=(10,6))
for method in methods:
 means=sel[sel.method==method].groupby('population').apply(lambda a:np.nanmean((a.corrected_cv/a.raw_cv)**2),include_groups=False).reindex(pops);ax.plot(means,pops,'o-',label=method)
ax.axvline(1,c='red',ls='--');ax.set(xlabel='Mean held-out CV-squared ratio (method-specific supported domain)',title='9 | Red terrain-only held-out dispersion: descriptive, not ecological ground truth');ax.legend();fig.tight_layout();save(fig,'09_holdouts')
# 10: matched stages on own common supported targets.
sel=matched[(matched.sigma==0)&(matched.population=='existing')];fig,axs=plt.subplots(1,2,figsize=(12,4.5))
for ax,metric,label in zip(axs,['combined_variance_ratio','combined_to_brdf_variance'],['Combined/raw CV-squared','Combined/BRDF-only CV-squared']):
 ax.boxplot([sel[sel.method==m][metric].dropna() for m in methods],tick_labels=methods,showfliers=False);ax.axhline(1,c='red',ls='--');ax.set(ylabel=label)
fig.suptitle('10 | Matched original-photo fits: topography and BRDF are refitted inside each spatial fold');fig.tight_layout();save(fig,'10_combined')
# 11: real full-frame factor/mask diagnostics.
products=json.loads((P/'full_frame_products.json').read_text())['products'];fig,axs=plt.subplots(2,4,figsize=(15,6))
for col,path in enumerate(products):
 with rasterio.open(path) as src:a=src.read(out_shape=(4,104,196))
 im=axs[0,col].imshow(a[0],vmin=0,vmax=3,cmap='magma');axs[1,col].imshow(a[3]==2,cmap='Greens',vmin=0,vmax=1);axs[0,col].set_title(['Native SCS+C','3m SCS+C','3m C correction','3m Minnaert'][col]);
 for ax in axs[:,col]:ax.set_xticks([]);ax.set_yticks([])
fig.colorbar(im,ax=list(axs[0]),shrink=.7,label='Red gain (display 0-3; analytical values uncapped)');fig.suptitle('11 | Full 10cm diagnostic factors and supported masks; unsupported pixels stay missing');save(fig,'11_full_support')
# 12: workflow/gates diagram.
fig,ax=plt.subplots(figsize=(13,7));ax.set(xlim=(0,13),ylim=(0,7));ax.axis('off');boxes=[(0.3,5,'Calibrated original photos\nSource scale + adjusted poses'),(4.7,5,'Typed absolute surfaces\nGround DTM / viewing DEM'),(9,5,'Field/proxy strata + shadow\nUnknown != sunlit'),(.3,2.8,'Buffered spatial training folds\nFit topo + uncertainty'),(4.7,2.8,'Positive denominator / supported domain\nUnsupported -> NaN + status'),(9,2.8,'Refit original-photo BRDF\nIn the same corrected space'),(2.5,.6,'Held-out spectral / terrain / angle checks\nReport improvement and degradation'),(7,.6,'Only accepted subset -> licensed mosaic\nCurrent workflow NOT production approved')]
for x,y,text in boxes:ax.add_patch(FancyBboxPatch((x,y),3.7,1.25,boxstyle='round,pad=.12',facecolor='#e1eff2',edgecolor='#265568'));ax.text(x+1.85,y+.625,text,ha='center',va='center',fontsize=9)
for a,b in [((4,5.6),(4.6,5.6)),((8.4,5.6),(8.9,5.6)),((10.8,5),(10.8,4.4)),((2.15,4.4),(2.15,4.12)),((4.05,3.4),(4.55,3.4)),((8.45,3.4),(8.95,3.4)),((10.8,2.8),(10.8,2.3)),((4.3,2.3),(4.3,1.98)),((6.3,1.2),(6.88,1.2))]:ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#265568'})
ax.plot([10.8,2.15],[4.4,4.4],color='#265568',lw=1);ax.plot([10.8,4.3],[2.3,2.3],color='#265568',lw=1)
ax.set_title('12 | Keep both corrections; retain unsupported domains and scientific validation gates');save(fig,'12_workflow')
print('Twelve figures complete',flush=True)
