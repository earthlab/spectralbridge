"""Reproduce ten Ruby evidence figures; unsupported stages are labelled, never fabricated."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from spectralbridge.drone_original import reference_design
P=Path(__file__).resolve().parent;R=P.parents[1];F=P/'figures';F.mkdir(exist_ok=True);O=R/'archive/local/ruby-correction-recovery-2026-11-06';OLD=R/'provenance/metashape-recovery/2026-11-05';d=pd.read_csv(P/'observations_enriched.csv');red=d[d.wavelength_nm==650];targets=red.groupby('target_id').first();ref=reference_design();baseline=json.loads((P/'baseline.json').read_text())
plt.rcParams.update({'font.size':10})
def save(fig,n):fig.savefig(F/(n+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)
# 1: geometry from recovered camera tables, no guessed orientation.
cam=pd.read_csv(next((OLD/'extracted').glob('*RUBY*chunk_0/cameras.csv')));cam=cam[cam.aligned];centers=np.array([json.loads(v) for v in cam.center_project]);fig,ax=plt.subplots(figsize=(9,6));ax.scatter(centers[:,0],centers[:,1],s=3,alpha=.15,label='Aligned camera planes');ax.scatter(targets.x,targets.y,s=20,label='Grid-selected tracked targets');
with rasterio.open(O/'ruby_vendor_fraction_x10000_10cm_v1.tif') as src:b=src.bounds;ax.plot([b.left,b.right,b.right,b.left,b.left],[b.bottom,b.bottom,b.top,b.top,b.bottom],label='Export extent')
from pyproj import Transformer
transform=Transformer.from_crs(4326,26913,always_xy=True)
features=json.loads((OLD/'footprints.geojson').read_text())['features']
for feature in [f for f in features if f['properties']['site']=='Ruby'][::30]:
 a=np.array(feature['geometry']['coordinates'][0]);x,y=transform.transform(a[:,0],a[:,1]);ax.plot(x,y,color='teal',lw=.5,alpha=.35)
ax.set(aspect='equal',xlabel='UTM easting (m)',ylabel='UTM northing (m)',title='1 | Ruby reconstruction and experimental target coverage');ax.legend();save(fig,'01_reconstruction')
# 2: counts and representativeness.
fig,axs=plt.subplots(1,2,figsize=(11,4.5));counts=red.groupby('target_id').master_key.nunique();sc=axs[0].scatter(targets.x,targets.y,c=counts.reindex(targets.index),cmap='viridis',s=45);fig.colorbar(sc,ax=axs[0],label='Selected red exposures');axs[0].set(aspect='equal',xlabel='Easting',ylabel='Northing');axs[1].hist(targets.lattice_displacement_m,bins=12);axs[1].set(xlabel='Grid center to tracked feature (m)',ylabel='Targets');fig.suptitle('2 | Spatial grid coverage; tracked features are not an unbiased surface census');save(fig,'02_overlap')
# 3: actual angles.
fig,axs=plt.subplots(1,3,figsize=(12,4));
for ax,key,label in zip(axs,['view_zenith_deg','view_azimuth_deg','relative_azimuth_deg'],['View zenith (degrees)','View azimuth (degrees)','Solar-view azimuth (degrees)']):ax.hist(red[key],bins=24);ax.set(xlabel=label,ylabel='Red observations')
fig.suptitle('3 | Reconstructed original-photo geometry, not camera-axis tilt');save(fig,'03_angles')
# 4: genuine repeated all-band spectra for four fixed target IDs.
fig,axs=plt.subplots(2,2,figsize=(11,7));
for ax,t in zip(axs.flat,sorted(d.target_id.unique())[::max(1,len(targets)//4)][:4]):
 for _,g in d[d.target_id==t].groupby('master_key'):
  g=g.sort_values('wavelength_nm');ax.plot(g.wavelength_nm,g.observed_fraction,alpha=.5,lw=.8)
 ax.set(title=t,xlabel='Source wavelength (nm)',ylabel='Vendor-calibrated fraction')
fig.suptitle('4 | Same tracked targets across original photos; 842 nm source NIR');fig.tight_layout();save(fig,'04_spectra')
# 5: joint support and bootstrap.
fig,axs=plt.subplots(1,2,figsize=(12,4.5));sc=axs[0].scatter(red.ross,red.li,c=red.view_zenith_deg,s=5,alpha=.5);axs[0].scatter(ref[1],ref[2],marker='*',s=180,c='red',label='45 degree sun / nadir');axs[0].set(xlabel='RossThick',ylabel='LiDenseR');axs[0].legend();fig.colorbar(sc,ax=axs[0],label='View zenith');boot=json.loads((P/'bootstrap_uncertainty.json').read_text())+json.loads((P/'temporal_wild_uncertainty.json').read_text());
for cluster,color in [('spatial_group','teal'),('time_minute_wild','orange')]:
 b=[v for v in boot if v['clustering']==cluster];x=np.array([v['wavelength_nm'] for v in b]);interval=np.array([v['reference_interval'] for v in b]);axs[1].errorbar(x,interval.mean(1),yerr=(interval[:,1]-interval[:,0])/2,fmt='o',color=color,label=cluster)
axs[1].axhline(0,c='black',lw=.5);axs[1].set(xlabel='Wavelength (nm)',ylabel='Shared-shape reference prediction');axs[1].legend();fig.suptitle('5 | Joint reference support and conditional single-flight bootstrap');save(fig,'05_support')
# 6: terrain and fitted C support.
fig,axs=plt.subplots(1,3,figsize=(13,4));
for surface,color in [('viewing_absolute','purple'),('ground_dtm_chunk','teal')]:axs[0].hist(targets[surface+'_slope_deg'],bins=15,alpha=.5,label=surface,color=color)
axs[0].set(xlabel='Local slope (degrees)',ylabel='Tracked targets');axs[0].legend(fontsize=7);models=json.loads((P/'topographic_models.json').read_text());
for ax,surface in zip(axs[1:],['viewing_absolute','ground_dtm_chunk']):
 rows=[v for v in models if v['surface']==surface and v['stratum']=='all'];
 for v in rows:
  if v.get('C_interval'):lo,hi=v['C_interval'];ax.plot([v['wavelength_nm']]*2,[lo,hi],color='teal');ax.scatter(v['wavelength_nm'],v['C'],color='teal')
 ax.axhline(0,c='black',lw=.6);ax.set(title=surface,xlabel='Wavelength (nm)',ylabel='C with spatial Fieller interval')
fig.suptitle('6 | Surface choice changes SCS+C inputs; bounded C is not full validation');fig.tight_layout();save(fig,'06_topography')
# 7: raw map and explicit unsupported stages.
fig,axs=plt.subplots(2,2,figsize=(11,7));
with rasterio.open(O/'ruby_vendor_fraction_x10000_10cm_v1.tif') as src:raw=src.read(5)[::5,::5]*.0001
im=axs[0,0].imshow(raw,vmin=0,vmax=np.nanpercentile(raw,99),cmap='magma');fig.colorbar(im,ax=axs[0,0],label='Red fraction');axs[0,0].set_title('Immutable calibrated input')
for ax,title in zip([axs[0,1],axs[1,0],axs[1,1]],['Topographic-only full image','BRDF-only full image','Combined full image']):ax.text(.5,.5,'NOT PRODUCED\nFull-frame scientific support unresolved',ha='center',va='center',transform=ax.transAxes);ax.set_title(title)
for ax in axs.flat:ax.set_xticks([]);ax.set_yticks([])
fig.suptitle('7 | Correction stages: no unsupported raster substituted');save(fig,'07_stages')
# 8: spectral stratum diagnostics; avoid pretending proxies are ground truth.
fig,ax=plt.subplots(figsize=(9,5));
for label,g in d.groupby('spectral_stratum'):series=g.groupby('wavelength_nm').observed_fraction.median();ax.plot(series.index,series,'o-',label=label)
ax.set(xlabel='Source wavelength (nm)',ylabel='Median vendor-calibrated fraction',title='8 | Descriptive spectral strata; no independent vegetation/soil labels');ax.legend();save(fig,'08_spectral_strata')
# 9: held-out spatial target agreement.
v=pd.read_csv(P/'heldout_validation.csv');fig,axs=plt.subplots(1,2,figsize=(12,4.5));
for ax,model in zip(axs,['additive_target_effects','multiplicative_target_amplitudes']):
 a=v[v.model==model];before=a.before_sd.to_numpy();after=a.after_sd.to_numpy();ax.scatter(before,after,s=10,alpha=.4);maximum=float(max(before.max(),after.max()));ax.plot([0,maximum],[0,maximum],'k--');ax.set(title=model,xlabel='Before within-target SD',ylabel='After candidate SD')
fig.suptitle('9 | Held-out spatial targets; shared photos/calibration limit independence');save(fig,'09_validation')
# 10: historical/current decision table.
fig,ax=plt.subplots(figsize=(12,5));ax.axis('off');rows=[['Radiometry','Old full-range storage was not fraction x10000','New explicit 1e-4 storage; source DN/32768'],['NIR','Previously labelled 862 nm','Source-specific 842 nm'],['Geometry','Assumed/primary-only mosaic geometry','Adjusted original-photo rays; explicit surfaces'],['BRDF','Ruby mosaic rejected','Target-aware candidates + spatial holdouts'],['Topography','Negative-C/denominator concerns','Recovered DTM tested; uncertainty retained'],['Final mosaic','No supported Ruby combined product','Not regenerated; scientific/license gates remain']];table=ax.table(cellText=rows,colLabels=['Component','Historical','P184 experiment'],loc='center',cellLoc='left',colWidths=[.15,.4,.45]);table.auto_set_font_size(False);table.set_fontsize(9);table.scale(1,2.7);ax.set_title('10 | Better inputs and tests do not automatically approve a corrected mosaic');save(fig,'10_comparison')
print('Ten figures reproduced',flush=True)

# Supplement: dense terrain incidence, red gain and explicit unsupported domain.
z=np.load(O/'dense_terrain_control.npz');fig,axs=plt.subplots(2,3,figsize=(12,6))
for row,surface in enumerate(['viewing_absolute','ground_dtm_chunk']):
 ci=z[surface+'_incidence'];gain=z[surface+'_red_gain'];bad=z[surface+'_unsupported'];im=axs[row,0].imshow(ci,vmin=-.2,vmax=1,cmap='viridis');fig.colorbar(im,ax=axs[row,0],label='cos(local solar incidence)');im=axs[row,1].imshow(np.where(~bad,gain,np.nan),vmin=0,vmax=5,cmap='magma');fig.colorbar(im,ax=axs[row,1],label='Red SCS+C gain (display 0-5)');axs[row,2].imshow(bad,cmap='Reds',vmin=0,vmax=1)
 for ax,title in zip(axs[row],[surface+' illumination','Numerically screened gain','Unsupported application domain']):ax.set_title(title,fontsize=9);ax.set_xticks([]);ax.set_yticks([])
fig.suptitle('6b | Dense mosaic terrain control only; no accepted corrected raster. Display bounds do not cap data.');fig.tight_layout();save(fig,'06b_terrain_maps')
