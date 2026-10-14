"""Reproduce interpretation of the supplied researcher-category analysis."""
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from spectralbridge.plant_spectral_atlas import _file_hash

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=Path(__file__).resolve().parent
RUN=ROOT/'artifacts/plant_spectral_atlas/researcher_pft_statistics'
OUT=RUN/'interpretation'
OUT.mkdir(exist_ok=True)
manifest=json.loads((RUN/'manifest.json').read_text())
assert all(_file_hash(RUN/n)==h for n,h in manifest['outputs'].items())
s=pd.read_csv(RUN/'method_comparison.csv')
t=pd.read_parquet(RUN/'polygon_year_spectra.parquet')
m=pd.read_parquet(RUN/'membership.parquet')
labels=pd.read_csv(RUN/'researcher_labels_and_species.csv')
primary=s[(s.blocking=='flight_history')&(s.status=='tested')]
effects=[]
for row in s[s.status=='tested'].itertuples():
    with np.load(RUN/'checkpoints'/(row.test_id+'.npz')) as result:
        effect=np.sqrt(np.sum(result['weights']*(result['curves'][0]/result['scale'])**2))
        effects.append(dict(test_id=row.test_id,weighted_rms_standardized_contrast=effect,
                            maximum_standardized_contrast=np.max(np.abs(result['curves'][0]/result['scale']))))
effects=pd.DataFrame(effects)
effects.to_csv(OUT/'effect_sizes.csv',index=False)
s=s.merge(effects,on='test_id',how='left')
s.to_csv(OUT/'methods_and_effects.csv',index=False)
# Checkpoint membership must exactly reproduce unique polygon/year samples.
assert not m.duplicated(['test_id','GlobalID']).any()
for row in s[s.status=='tested'].itertuples():
    mm=m[m.test_id==row.test_id]
    assert mm.cover_category.eq(row.a).sum()==row.n_a
    assert mm.cover_category.eq(row.b).sum()==row.n_b
    with np.load(RUN/'checkpoints'/(row.test_id+'.npz')) as r:
        assert np.isfinite(r['curves']).all()
# Diagnostic means/spread use the full cohort and are explicitly not the matched
# contrast estimator. Show raw stored units, not assumed scaled reflectance.
cols=[c for c in t if c.startswith('corr_wl')]
w=np.array([float(c.split('_wl')[1][:-2]) for c in cols])
cohorts=list(t.groupby(['site','year'],sort=True))
categories=sorted(t.cover_category.unique())
fig,axes=plt.subplots(5,len(cohorts),figsize=(16,13),squeeze=False,sharex=True)
for i,category in enumerate(categories):
    for j,((site,year),cohort) in enumerate(cohorts):
        ax=axes[i,j]
        group=cohort[cohort.cover_category==category]
        values=group[cols].to_numpy(float)
        valid=np.isfinite(values).any(axis=0)
        ix=np.flatnonzero(valid)
        median=np.nanmedian(values[:,valid],axis=0)
        lo,hi=np.nanquantile(values[:,valid],[.1,.9],axis=0)
        for segment in np.split(np.arange(len(ix)),np.flatnonzero(np.diff(w[ix])>8)+1):
            ax.fill_between(w[ix[segment]],lo[segment],hi[segment],color='#9fc5d8',alpha=.6)
            ax.plot(w[ix[segment]],median[segment],color='#174f6e',lw=1)
        ax.set_title(f'{site} {year} · n={len(group)}',fontsize=9)
        if j==0:
            ax.set_ylabel(category+'\nStored spectral units',fontsize=9)
        if i==4:
            ax.set_xlabel('Wavelength (nm)')
fig.suptitle('Researcher classes: corrected NEON polygon/year spectra\nMedian and empirical 10–90% spread; full cohorts, descriptive only; local y scales')
fig.tight_layout(rect=(0,0,1,.95))
for ext in ['png','pdf']:
    fig.savefig(OUT/('category_spectra.'+ext),dpi=150)
plt.close(fig)
ranked=primary.merge(effects,on='test_id').sort_values('weighted_rms_standardized_contrast')
exceptions=primary[primary.p_energy_holm>=.05]
metrics={'source_sha256':manifest['identity']['source'],'unique_polygons':int(t.GlobalID.nunique()),
         'polygon_year_spectra':len(t),'species_null_polygons':int(labels[labels.species.isna()].GlobalID.nunique()),
         'primary_tested':len(primary),'primary_npc_supported':int(primary.p_npc_holm.lt(.05).sum()),
         'site_year_npc_supported':int(s[s.blocking=='site_year'].p_npc_holm.lt(.05).sum()),
         'primary_energy_supported':int(primary.p_energy_holm.lt(.05).sum()),
         'primary_max_supported':int(primary.p_max_holm.lt(.05).sum()),
         'primary_fpca_supported':int(primary.p_fpca_holm.lt(.05).sum()),
         'rms_standardized_range':[float(ranked.weighted_rms_standardized_contrast.min()),float(ranked.weighted_rms_standardized_contrast.max())]}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
lines=['# Researcher category results','',
       'The analysis now uses the source `cover_category` field, not a species-to-PFT lookup. The exact classes are Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, and Woody shrub. Non-vegetated & dead is a mixed cover/dead-material comparator; the five classes are researcher cover classes rather than five mutually exclusive physiological trait definitions.','',
       f"All {metrics['unique_polygons']:,} source polygon identities were included, yielding {len(t):,} polygon/year spectra; {metrics['species_null_polygons']:,} identities lack a species name. The source was read in place; original inferred-label outputs are preserved. NIWO contributes 2020 and 2023; WREF and YELL contribute 2023.",'',
       f"All {len(primary)} acquisition-matched class-pair comparisons are supported by the primary max+integrated NPC test after Holm correction across the 40-comparison family (adjusted p = 0.004 throughout). Maximum and FPCA sensitivities also support all 40; energy supports {metrics['primary_energy_supported']}/40. All 40 site/year-only comparisons are supported by NPC in their separate sensitivity family.",'',
       'The identical primary p-values are a Monte Carlo resolution floor: 9,999 permutations plus the observed statistic give minimum raw p = 0.0001; Holm yields 0.004 here. They do not mean the effects are equal or have precisely known probabilities. Corrected significance also does not imply nonoverlapping spectra or accurate assignment of an unknown polygon.','',
       '## Where methods disagree','']
for row in exceptions.itertuples():
    lines.append(f'- {row.cohort}, {row.pair}: energy adjusted p = {row.p_energy_holm:.4g}, despite primary/max/FPCA support. Distribution-wide evidence is less robust for this comparison; a mean/projection contrast does not require the energy statistic to agree.')
lines += ['', '## Magnitudes and interpretation','',
          f"The wavelength-weighted RMS block-adjusted contrast divided by the fixed pooled within-block spectral SD ranges from {metrics['rms_standardized_range'][0]:.3f} to {metrics['rms_standardized_range'][1]:.3f} across matched comparisons. This descriptive standardized curve magnitude is not a classifier score or an independent effect confidence interval. `methods_and_effects.csv` records every value.",'',
          'Smallest standardized contrasts in this dataset:','']
for row in ranked.head(5).itertuples():
    lines.append(f'- {row.cohort}, {row.pair}: RMS standardized contrast {row.weighted_rms_standardized_contrast:.3f}; matched n={row.n_a}/{row.n_b}.')
lines += ['', '## Limits on scientific claims','',
          'The defensible result is conditional spectral differentiation among the sampled researcher-labeled polygon mixtures. Exact histories account for shared acquisition exposure, not all spatial, canopy, substrate, illumination or compositional confounding. Polygon IDs are sampling units; herbaceous patches are not individual plants. Repeated years are analyzed separately and are correlated replications where IDs recur. Test exchangeability remains an observational assumption.','',
          'Researcher labels vary within some species names, so the earlier deterministic species/PFT aliasing result cannot simply be transferred. This does not establish a fully adjusted causal PFT effect; missing species, mixed cover and sparse taxon/class cells remain. Generic P117 simulations need not be rerun for a label adapter and do not establish actual-data exchangeability. Classification, equivalence and transfer to new regions require separate validation.','',
          'Use `category_spectra.pdf` to see typical curves and within-class spread, and `../simultaneous_envelopes.pdf` for matched contrast localization. The former uses full cohorts and does not reproduce the matched estimator. Both retain wavelength gaps. `../RESULTS.md` contains the full primary table.']
(OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
for name in ['RESULTS.md','metrics.json','methods_and_effects.csv']:
    shutil.copyfile(OUT/name,EVIDENCE/name)
shutil.copyfile(RUN/'support.csv',EVIDENCE/'support.csv')
outputs={p.name:_file_hash(p) for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'}
(OUT/'manifest.json').write_text(json.dumps({'source_manifest':_file_hash(RUN/'manifest.json'),'script':_file_hash(__file__),'outputs':outputs},indent=2)+'\n')
print(json.dumps(metrics,indent=2))
