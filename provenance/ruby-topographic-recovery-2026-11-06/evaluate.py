"""Predeclared common-population topographic candidates and buffered spatial CV."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from scipy.ndimage import binary_dilation
from spectralbridge.drone_topography import fit_topographic_model,topographic_factors,spatial_training_mask
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';g=np.load(OUT/'common_grid.npz');base=json.loads((P/'baseline.json').read_text());sz=base['solar_zenith_deg'];raw=g['raw'];waves=[444,475,531,560,650,668,705,717,740,842];valid=g['valid'];groups=g['groups'];fold=g['fold'];stratum=g['stratum'];dark=g['spectral_dark'];hom=g['texture_cv']<=.25
records=[];holdouts=[];applications={};plan=[]
def mask_population(name,geometry):
 sun=g['viewing_absolute_covered']&~g['viewing_absolute_shadow']&(g[geometry+'_incidence']>0)
 masks={'existing':np.ones(valid.shape,bool),'geometric_sunlit':sun,'spectral_screened':~dark,'combined_screened':sun&~dark,'homogeneous_sunlit':sun&~dark&hom,'canopy_proxy':stratum==1,'herbaceous_proxy':stratum==2,'exposed_proxy':stratum==3,'mixed_proxy':stratum==4}
 return masks[name]
def fit_eval(ci,y,sl,selection,method,strategy,fitgroups):
 use=selection&np.isfinite(ci)&np.isfinite(sl)&np.isfinite(y)&(sl>=5)&(ci>0)&(y>=0)&(y<=2)
 return fit_topographic_model(ci[use],y[use],fitgroups[use],method=method,balanced=strategy=='balanced',robust=strategy=='huber'),use
# Full red sensitivity; all ten bands for native/3m DTM and the six requested screening fits.
for surface in ['viewing_absolute','ground_dtm_chunk']:
 for sigma in [0,1,3,10]:
  key=surface+'_sigma'+str(sigma);ci=g[key+'_incidence'];sl=g[key+'_slope_deg']
  for population in ['existing','geometric_sunlit','spectral_screened','combined_screened','homogeneous_sunlit','canopy_proxy','herbaceous_proxy','exposed_proxy','mixed_proxy']:
   for method,strategy in [('scsc','ols'),('scsc','balanced'),('scsc','huber'),('c_correction','ols'),('minnaert','ols')]:
    bands=range(10) if surface=='ground_dtm_chunk' and sigma in [0,3] and population in ['existing','geometric_sunlit','spectral_screened','combined_screened','homogeneous_sunlit'] and strategy=='ols' else [4]
    for band in bands:
     nm=waves[band];identifier=f'{key}__{population}__{method}__{strategy}__{nm}';plan.append(dict(id=identifier,surface=surface,sigma=sigma,population=population,method=method,strategy=strategy,wavelength_nm=nm));populationmask=mask_population(population,key);selection=valid&populationmask&~g['field_buffer'];y=raw[band];model,use=fit_eval(ci,y,sl,selection,method,strategy,groups);model.update(id=identifier,surface=surface,sigma=sigma,population=population,strategy=strategy,wavelength_nm=nm,fitting_locations=int(use.sum()),spatial_coverage_groups=int(len(np.unique(groups[use]))));sun=(g['viewing_absolute_covered']&~g['viewing_absolute_shadow']) if population in ['geometric_sunlit','combined_screened','homogeneous_sunlit'] else None
     app=topographic_factors(ci,sl,sz,model,geometric_sunlit=sun);support=valid&populationmask&app['supported'];model.update(application_supported=int(support.sum()),application_valid=int(valid.sum()),application_fraction=float(support.sum()/valid.sum()),unsupported_geometric_shadow=int((valid&g['viewing_absolute_shadow']).sum()),unsupported_dark=int((valid&dark&~support).sum()))
     if support.any():model.update(factor_quantiles=np.quantile(app['factor'][support],[0,.01,.5,.99,1]).tolist(),factor_interval_relative_width_median=float(np.median((app['high'][support]-app['low'][support])/app['factor'][support])))
     records.append(model)
     if nm==650 and surface=='ground_dtm_chunk' and sigma in [0,3] and population in ['existing','homogeneous_sunlit','combined_screened'] and strategy=='ols':
      applications[identifier+'_factor']=np.where(support,app['factor'],np.nan);applications[identifier+'_supported']=support;applications[identifier+'_width']=app['high']-app['low']
     # Same quadrants, 2m boundary exclusion, held-out target populations.
     for f in range(4):
      testregion=fold==f;train=selection&spatial_training_mask(fold,f,buffer_cells=2);fit,trainuse=fit_eval(ci,y,sl,train,method,strategy,groups)
      appcv=topographic_factors(ci,sl,sz,fit,geometric_sunlit=sun);test=testregion&valid&populationmask;ok=test&appcv['supported'];rec=dict(id=identifier,fold=f,method=method,population=population,surface=surface,sigma=sigma,strategy=strategy,wavelength_nm=nm,train_n=int(trainuse.sum()),test_n=int(test.sum()),supported_n=int(ok.sum()),status=fit['status'],reason=fit.get('reason'),C=fit.get('C'),k=fit.get('k'),application_fraction=float(ok.sum()/max(1,test.sum())))
      if ok.sum()>4:
       original=y[ok];corrected=original*appcv['factor'][ok];x=ci[ok];corr=lambda a:float(np.corrcoef(a,x)[0,1]) if np.std(a)>0 and np.std(x)>0 else None;cv=lambda a:float(np.std(a)/np.mean(a)) if np.mean(a)>0 else None;rec.update(raw_cv=cv(original),corrected_cv=cv(corrected),raw_incidence_correlation=corr(original),corrected_incidence_correlation=corr(corrected),raw_mean=float(original.mean()),corrected_mean=float(corrected.mean()),negative_corrected=int((corrected<0).sum()),above_one=int((corrected>1).sum()),factor_min=float(appcv['factor'][ok].min()),factor_max=float(appcv['factor'][ok].max()))
       # Held-out illumination prediction versus training-population constant, not proof of ecological truth.
       positive_train=trainuse&(y>0)
       if positive_train.any():
        a,b=fit['beta'];prediction=np.exp(a*np.log(x)+b) if method=='minnaert' else a*x+b;rec.update(prediction_rmse=float(np.sqrt(np.mean((original-prediction)**2))),constant_rmse=float(np.sqrt(np.mean((original-y[positive_train].mean())**2))))
      holdouts.append(rec)
     if len(records)%100==0:print('Candidates',len(records),'heldout fits',len(holdouts),flush=True)
(P/'candidate_plan.json').write_text(json.dumps(plan,indent=2)+'\n');(P/'models.json').write_text(json.dumps(records,indent=2)+'\n');pd.DataFrame(holdouts).to_csv(P/'spatial_holdouts.csv',index=False);np.savez_compressed(OUT/'candidate_maps.npz',**applications);print('Completed',len(records),len(holdouts),flush=True)
