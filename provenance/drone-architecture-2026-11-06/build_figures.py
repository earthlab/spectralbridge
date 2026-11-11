"""Rebuild report figures from compact, completed comparison outputs only."""
from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path(__file__).resolve().parent; F=P/'figures'; F.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#fbfcfd','axes.facecolor':'#fbfcfd','axes.titleweight':'bold','savefig.facecolor':'#fbfcfd'})
colors=['#216e8c','#e09432','#5c8b57','#a24b69'];manifest=[]
def save(fig,n,title):
 fig.suptitle(title,fontsize=17,fontweight='bold');fig.tight_layout(rect=[0,0,1,.94]);name=f'{n:02d}.png';fig.savefig(F/name,dpi=170,bbox_inches='tight');plt.close(fig);manifest.append({'number':n,'title':title,'file':'figures/'+name})
def boxes(n,title,items,footer):
 fig,ax=plt.subplots(figsize=(12,7));ax.axis('off')
 for i,(head,body) in enumerate(items):
  row,col=divmod(i,3);x=.025+col*.33;y=.57-row*.43
  ax.add_patch(FancyBboxPatch((x,y),.295,.34,boxstyle='round,pad=.012',fc='#e9f1f4',ec=colors[col%3],lw=1.5,transform=ax.transAxes))
  ax.text(x+.012,y+.28,head,weight='bold',fontsize=12,transform=ax.transAxes);ax.text(x+.012,y+.23,body,va='top',fontsize=10.5,linespacing=1.65,transform=ax.transAxes)
 ax.text(.025,.015,footer,transform=ax.transAxes,fontsize=10,color='#45545d');save(fig,n,title)
boxes(1,'Evolution: repair software before buying more information',[
 ('Mar–Jun 2026 · Core','H5 orchestration: 21 March\nTIFF bridge: 3 June\nFile-based, restart-safe stages'),('29–30 Oct · Software','Spatial reflection + CRS\nCalibration ambiguity exposed\nLegacy stretches ≠ fractions'),('3–5 Nov · Geometry','Red streak: unstable correction\nCamera CSV/source mismatch\nNadir ≠ blended viewing angle'),('P183 · Recovered context','Two Metashape projects\nAdjusted poses + terrain\nDN/32768 and 842 nm verified'),('P184–185 · Models','Repeated-target BRDF\nBuffered terrain holdouts\nNegative C remains unresolved'),('P186 · Simplify','Production encoding recognition\n271 KB calibration packet\nCapability-driven architecture')], 'Software repairs, new information, and model changes are distinct contributions; no full corrected mosaic is demonstrated.')
boxes(2,'Six levels: information grows faster than routine input needs',[
 ('L0 · Historical H5','Legacy metadata + old reader\nHistorical reference only\nNot a recommended workflow'),('L1 · Verified H5 / TIFF','Encoding, grid, wavelength\nMinimum calibrated extraction\nCorrections need support'),('L2 · Cheap metadata','Solar + suitable terrain\nRuby public DEM: 66.7 KB\nOne crop, not universal proof'),('L3 · Camera geometry','Adjusted centers + intrinsics\nPortable Ruby tables: 2.00 MB\nBlend weights still missing'),('L4 · Repeated observations','3341 records / 64 targets\n271 KB, all 10 bands\nNo photos needed for refitting'),('L5 · Original photographs','2267 sampled photos: 5.59 GB\nFull remosaic needs license\nNot executed / not approved')], 'Volumes are measured artifacts of different scope; the compact packet was derived from photographs, not independent new observations.')
cap=np.array([[0,0,0,0,0,0],[1,1,0,0,0,0],[1,1,1,0,0,0],[1,1,1,1,0,0],[1,1,1,1,1,0],[1,1,1,1,1,0]])
fig,ax=plt.subplots(figsize=(11,5));ax.imshow(cap,cmap=matplotlib.colors.ListedColormap(['#e6e9ed','#44869a']),vmin=0,vmax=1,aspect='auto');ax.set_yticks(range(6),['L0 historical','L1 verified core','L2 external metadata','L3 adjusted geometry','L4 compact calibration','L5 full photographs']);ax.set_xticks(range(6),['Known\nencoding/grid','Band\nidentity','Terrain +\nSun inputs','Actual\nview rays','Repeated\ntargets','Independent\nSun repeats']);
for i in range(6):
 for j in range(6):ax.text(j,i,'input*' if cap[i,j] else '—',ha='center',va='center',fontsize=9,color='white' if cap[i,j] else '#555')
ax.text(0,-.22,'*Designed input availability, not correction approval. A file alone does not establish physical identifiability.',transform=ax.transAxes,fontsize=10);save(fig,3,'Capabilities are gates, not a ladder of guaranteed accuracy')
pol=pd.read_csv(P/'polygon_common_support.csv');wl=np.array([444,475,531,560,650,668,705,717,740,842]);cols=['rho_'+str(x) for x in wl];ref=pol[pol.configuration=='verified_calibrated_input'][cols].median().to_numpy()
fig,axs=plt.subplots(1,2,figsize=(12,5));dn=np.linspace(0,65535,200);axs[0].plot(dn,dn/32768,label='Verified DN / 32768',color=colors[0]);axs[0].plot(dn,dn/65535,label='Historical fixed-range misread',color=colors[1]);axs[0].set(xlabel='Calibrated original integer DN',ylabel='Reflectance fraction');axs[0].legend();axs[1].plot(wl,ref,'o-',label='Verified polygon median',color=colors[0]);axs[1].plot(wl,ref*32768/65535,'o--',label='Same spectra, incorrect scale',color=colors[1]);axs[1].set(xlabel='Source wavelength (nm)',ylabel='Reflectance fraction');axs[1].legend();save(fig,4,'Encoding recovery changes magnitude, not physical validation')
geo=pd.read_csv(P/'viewing_geometry_comparison.csv');fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax,site in zip(axs,['Ruby','Goldhill']):
 for method,label,color in [('nadir','Nadir assumption',colors[1]),('actual_position_nominal_altitude','Actual XY + nominal AGL',colors[0]),('retained_primary_camera','Different primary exposure',colors[3])]:
  v=np.sort(geo[(geo.site==site)&(geo.method==method)].angular_error_degrees.dropna());ax.plot(v,np.arange(1,len(v)+1)/len(v),label=label,color=color)
 ax.set(title=site,xlabel='Angular separation from actual observation (°)',ylabel='Fraction of paired observations',ylim=(0,1));ax.legend(fontsize=9)
save(fig,5,'Nadir loses observed angle diversity; primary is not the blend')
pair=pd.read_csv(P/'compact_selected_outer_comparison.csv');outer=pd.read_csv(P/'compact_outer_results.csv');full=outer[(outer.targets==64)&(outer.views==99)&(outer.design=='spatial')];unc=pd.DataFrame(json.loads((P/'compact_uncertainty.json').read_text()))
fig,axs=plt.subplots(1,2,figsize=(12,5));axs[0].boxplot([np.clip(full.absolute_variance_ratio,.05,5),np.clip(pair.full,.05,5),np.clip(pair.compact,.05,5)],tick_labels=['Full packet\nabsolute variance','Full packet\nCV²','Selected small\nCV²'],showfliers=False);axs[0].axhline(1,color='#888',ls='--');axs[0].set(ylabel='Corrected / raw ratio (lower is better)',ylim=(0,3));counts=unc.groupby('design').normalization_supported.sum();axs[1].bar(['Full packet','Small subset'],[counts['full'],counts['nested_selected']],color=colors[:2]);axs[1].set(ylabel='Supported band × outer-fold models',ylim=(0,43));axs[1].axhline(40,color='#888',ls='--');save(fig,6,'Same held-out targets: median benefit, unresolved average harm')
ext=pd.read_csv(P/'external_dem_comparison.csv');held=pd.read_csv(P/'external_dem_spatial_holdouts.csv');fig,axs=plt.subplots(1,3,figsize=(13,5));names=['Metashape_DTM_native','Metashape_DTM_sigma3m','USGS_3DEP_requested_10m'];labels=['Native\nground DTM','3 m screened\nground DTM','Public\nrequested 10 m'];red=ext[ext.wavelength_nm==650].set_index('source').loc[names];axs[0].bar(labels,red.C,color=colors[:3]);axs[0].axhline(0,color='#888');axs[0].set(ylabel='Red SCS+C coefficient C');v=held.groupby('source').cv2_ratio.mean();axs[1].bar(labels,v.loc[names],color=colors[:3]);axs[1].axhline(1,color='#888',ls='--');axs[1].set(ylabel='Mean held-out CV² ratio',ylim=(0,1.15));support=held.groupby('source')[['supported_n','test_n']].sum();axs[2].bar(labels,(support.supported_n/support.test_n).loc[names],color=colors[:3]);axs[2].set(ylabel='Held-out numerical domain fraction',ylim=(0,1));save(fig,7,'Terrain changes numerical support; negative C remains')
fig,axs=plt.subplots(1,3,figsize=(13,5));pm=pd.DataFrame(json.loads((P/'polygon_metrics.json').read_text()));order=['verified_calibrated_input','fixed_range_misread_as_divide_10000','controlled_vertical_reflection'];labels=['Verified','Wrong scale','Reflected'];pm=pm.set_index('configuration').loc[order]
for name,label,color in zip(order,labels,colors):axs[0].plot(wl,pol[pol.configuration==name][cols].median(),'o-',label=label,color=color)
axs[0].set(xlabel='Wavelength (nm)',ylabel='Median polygon reflectance');axs[0].legend(fontsize=9);axs[1].bar(labels,pm.median_within_polygon_cv,color=colors[:3]);axs[1].set(ylabel='Median within-polygon CV');axs[2].bar(labels,pm.cover_between_within_scatter_ratio,color=colors[:3]);axs[2].set(ylabel='Field cover between / within scatter');save(fig,8,'86 common polygons: a smaller CV can still mean worse spectra')
cost=json.loads((P/'compact_cost.json').read_text());fig,axs=plt.subplots(1,2,figsize=(12,5));axs[0].barh(['Compact table','Sampled photographs','Remote two-site inventory'],[cost['compact_bytes'],cost['photo_subset_bytes'],96106111162],color=colors[:3]);axs[0].set(xscale='log',xlabel='Measured bytes (log scale; different scopes)');axs[1].scatter([cost['compact_bytes']/1e6],[pair.full.median()],s=140,color=colors[0]);axs[1].annotate('Full packet: 600 held-out cases\nmedian CV² = 0.838',(cost['compact_bytes']/1e6,pair.full.median()),xytext=(.08,.6),textcoords='axes fraction');axs[1].set(xlabel='Calibration packet size (MB)',ylabel='Held-out corrected / raw CV²',xlim=(0,.6),ylim=(0,1.3));axs[1].axhline(1,color='#888',ls='--');axs[1].text(.04,.07,'L5 corrected-mosaic accuracy: unmeasured\nNo invented accuracy-versus-cost curve',transform=axs[1].transAxes);save(fig,9,'Avoid photograph transfer for routine calibration refits')
fig,axs=plt.subplots(1,2,figsize=(12,5));summ=outer.groupby(['targets','views','design']).ratio.median().reset_index()
for views,label,color in [(3,'3 views / target',colors[1]),(5,'5 views / target',colors[2]),(99,'All available views',colors[0])]:
 z=summ[(summ.views==views)&(summ.design=='spatial')];axs[0].plot(z.targets,z.ratio,'o-',label=label,color=color)
axs[0].axhline(1,color='#888',ls='--');axs[0].set(xlabel='Requested training targets (capped by fold availability)',ylabel='Median outer held-out CV² ratio');axs[0].legend(fontsize=9)
for design,color in zip(['spatial','concentrated','angular'],colors):
 z=summ[(summ.views==99)&(summ.design==design)];axs[1].plot(z.targets,z.ratio,'o-',label=design,color=color)
axs[1].axhline(1,color='#888',ls='--');axs[1].set(xlabel='Requested training targets',ylabel='Median outer held-out CV² ratio');axs[1].legend();save(fig,10,'Nested spatial experiment: small numerical fits are not enough')
boxes(11,'Recommended architecture: immutable sources, explicit contracts',[
 ('1 · Ingestion boundary','Verified affine + wavelength\nGrid + source-validity checks\nUnknown encoding blocks science'),('2 · Scientific core','Terrain / Sun / view contracts\nSCS+C and Ross/Li unchanged\nPer-stage support + uncertainty'),('3 · Outputs','Native + translated products\nPhysical polygon Parquet + QA\nUnsupported ≠ identity success'),('Optional · Geometry','Portable adjusted camera table\nSource assignment + terrain\nExpose missing blend weights'),('Optional · Compact fitting','Repeated target observations\nSpatial holdouts + bootstrap\nReference-domain validation'),('Optional · Source rebuild','Calibrated photographs\nBoth supported corrections\nLicensed remosaic + validation')], 'Only ingestion hardening is implemented here; orchestrator and enhancement boundaries are an evidence-based roadmap.')
boxes(12,'Escalate for missing information, not file availability',[
 ('Encoding / grid unknown?','Request verified declaration\nor original export metadata\nDo not infer from value ranges'),('Terrain / Sun wrong?','Try suitable public terrain\nVerify datum + shadows\nRequest independent Sun repeats'),('View model unsupported?','Recover adjusted camera geometry\nTest kernel/reference support\nPrimary alone may not suffice'),('Need repeated targets?','Request compact calibrated packet\nSpatially distributed, all bands\nPreserve quality + provenance'),('Need mosaic reconstruction?','Only then recover source photos\nRequire supported corrections\nand executable licensed path'),('C still unidentifiable?','More same-flight views may fail\nSeek different illumination\nKeep corrected output blocked')], 'These are capability decisions. No fixed angle, pixel count, or high R² universally establishes scientific interchangeability.')
(P/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Saved',len(manifest),'figures')

# Directed architecture and decision diagrams replace the corresponding overview cards.
def directed(n,title,nodes,edges,footer):
 fig,ax=plt.subplots(figsize=(13,8));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
 for key,(x,y,w,h,label) in nodes.items():
  ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=.012',fc='#e9f1f4',ec='#216e8c',lw=1.5));ax.text(x,y,label,ha='center',va='center',fontsize=10.5,linespacing=1.55)
 for start,end,label in edges:
  a=nodes[start];b=nodes[end];dx=b[0]-a[0];dy=b[1]-a[1]
  if abs(dy)>=abs(dx):p=(a[0],a[1]+np.sign(dy)*a[3]/2);q=(b[0],b[1]-np.sign(dy)*b[3]/2)
  else:p=(a[0]+np.sign(dx)*a[2]/2,a[1]);q=(b[0]-np.sign(dx)*b[2]/2,b[1])
  ax.annotate('',xy=q,xytext=p,arrowprops=dict(arrowstyle='->',color='#53646d',lw=1.5));ax.text((p[0]+q[0])/2+.008,(p[1]+q[1])/2+.012,label,fontsize=9,ha='center',bbox=dict(fc='#fbfcfd',ec='none',pad=1))
 ax.text(.02,.015,footer,fontsize=9);save(fig,n,title)
directed(11,'A small scientific core with three optional information inputs',{
 'input':(.2,.88,.33,.10,'Immutable calibrated H5 / TIFF\nSource identity + polygons'),
 'ingest':(.2,.65,.33,.12,'Verified encoding, grid, wavelength\nShared physical affine boundary'),
 'core':(.2,.40,.33,.14,'Topography + BRDF stages\nReference / uncertainty / joint support'),
 'output':(.2,.15,.33,.11,'Physical polygon spectra + QA\nBlocked status when unsupported'),
 'geo':(.75,.78,.36,.12,'Optional adjusted geometry\nCenters, intrinsics, source assignments'),
 'packet':(.75,.53,.36,.12,'Optional compact calibration\nRepeated targets + actual rays'),
 'photos':(.75,.26,.36,.13,'Optional source reconstruction\nCalibrated photos + both corrections\nLicensed remosaic + validation')},[('input','ingest',''),('ingest','core',''),('core','output',''),('geo','core','geometry'),('packet','core','fit / validate'),('photos','output','only after support')], 'Implemented: radiometric ingestion contract. Broader dispatcher/enhancement integration is a roadmap, not a new API.')
directed(12,'Request the information that resolves the failed capability',{
 'start':(.26,.91,.40,.09,'Inspect source encoding, grid and bands'),
 'fix':(.77,.91,.34,.09,'Request verified export / declaration'),
 'terrain':(.26,.72,.40,.10,'Terrain / Sun / topographic support?'),
 'sun':(.77,.72,.34,.10,'Try suitable DTM + shadow checks\nIf confounded: independent Sun repeat'),
 'angular':(.26,.51,.40,.10,'View / reference / BRDF support?'),
 'cal':(.77,.51,.34,.10,'Actual geometry → compact targets\nDo not treat primary as blend'),
 'need':(.26,.31,.40,.10,'Need calibration change or source rebuild?'),
 'full':(.77,.31,.34,.10,'Recover photos + licensed reconstruction\nBoth corrections must be supported'),
 'end':(.26,.11,.40,.10,'Run supported core; retain support masks\nOtherwise block corrected-product claim')},[('start','fix','unknown'),('start','terrain','verified'),('terrain','sun','fails'),('terrain','angular','passes'),('angular','cal','fails'),('angular','need','passes'),('need','full','yes'),('need','end','no')], 'Failure branches request new evidence and re-evaluation; they never silently substitute identity corrections.')
(P/'figure_manifest.json').write_text(json.dumps({x['number']:x for x in manifest},indent=2)+'\n')
