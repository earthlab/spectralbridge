"""Rebuild audit interpretation/diagnostics from verified inference and simulation."""
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.plant_spectral_pfts import tag_pfts,load_pft_crosswalk
from spectralbridge.plant_spectral_years import _year_plant_spectra
from spectralbridge.plant_pft_statistics import _history_keys,_center,_write_json,holm

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=REPO/'artifacts/plant_spectral_atlas/pft_method_audit'
EMP=BASE/'empirical'
SIM=BASE/'simulations'
OUT=BASE/'interpretation'


def md_table(frame):
    lines=['| '+' | '.join(frame.columns)+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(str(x) for x in row)+' |')
    return '\n'.join(lines)


def verify(root,name):
    manifest=json.loads((root/name).read_text())
    if not all(_file_hash(root/n)==h for n,h in manifest['outputs'].items()):
        raise ValueError(f'Invalid input ledger: {name}')
    return manifest


def diagnostics(summary):
    source=REPO/'artifacts/plant_spectral_atlas/comparisons/products/corr/plant_flight_spectra.parquet'
    table,cols,obs=_year_plant_spectra(pd.read_parquet(source),'corr')
    table=tag_pfts(table,load_pft_crosswalk()).join(_history_keys(obs),on=['GlobalID','year'])
    records=[]
    block_records=[]
    for row in summary.query('status=="tested" and blocking=="flight_history"').itertuples():
        part=table[(table.site==row.site)&(table.year==row.year)&table.pft_code.isin([row.a,row.b])].sort_values('GlobalID')
        z=part.pft_code.eq(row.a).astype(float).to_numpy()
        b=pd.factorize(part.flight_history)[0]
        mixed=[v for v in np.unique(b) if len(np.unique(z[b==v]))==2]
        use=np.isin(b,mixed)
        part=part[use]
        z,b=z[use],b[use]
        with np.load(EMP/'checkpoints'/(row.test_id+'.npz')) as cp:
            columns,beta,se,scale=cp['columns'],cp['curves'][0],cp['se'],cp['scale']
        y=part[cols].to_numpy(float)[:,columns]
        peak=int(np.argmax(np.abs(beta/se)))
        median_beta=np.zeros(len(columns))
        auc=np.zeros(len(columns))
        denominator=0
        variance_a=variance_b=df_a=df_b=0
        ranks=np.empty_like(y)
        for block in np.unique(b):
            ix=np.flatnonzero(b==block)
            aa=y[(b==block)&(z==1)]
            bb=y[(b==block)&(z==0)]
            weight=len(aa)*len(bb)/(len(aa)+len(bb))
            denominator+=weight
            variance_a+=float(np.sum(((aa-aa.mean(axis=0))/scale)**2))
            variance_b+=float(np.sum(((bb-bb.mean(axis=0))/scale)**2))
            df_a+=len(aa)-1
            df_b+=len(bb)-1
            median_beta+=weight*(np.median(aa,axis=0)-np.median(bb,axis=0))
            auc+=weight*np.mean(np.sign(aa[:,None,:]-bb[None,:,:]),axis=(0,1))
            ranks[ix]=rankdata(y[ix],axis=0,method='average')
            block_records.append({'test_id':row.test_id,'block':int(block),'n_a':len(aa),'n_b':len(bb),'mean_weight':weight,
                                  'peak_mean_difference':float(aa[:,peak].mean()-bb[:,peak].mean()),
                                  'peak_median_difference':float(np.median(aa[:,peak])-np.median(bb[:,peak])),
                                  'rank_variance_mass':float(np.sum((ranks[ix,peak]-ranks[ix,peak].mean())**2))})
        median_beta/=denominator
        auc/=denominator
        x=_center(z[:,None],b).ravel()
        contributions=x[:,None]*_center(y,b)/(x@x)/scale
        influence=np.linalg.norm(contributions,axis=1)/np.linalg.norm(beta/scale)
        records.append({'test_id':row.test_id,'cohort':row.cohort,'pair':row.pair,
                        'peak_wavelength_nm':float(cols[columns[peak]].split('_wl')[1][:-2]),
                        'peak_mean_difference':beta[peak],'peak_weighted_median_difference':median_beta[peak],
                        'peak_weighted_cliffs_delta':auc[peak],
                        'dispersion_trace_ratio_a_over_b':(variance_a/df_a)/(variance_b/df_b) if df_a and df_b and variance_b else float('nan'),
                        'mean_median_curve_cosine':float(beta@median_beta/(np.linalg.norm(beta)*np.linalg.norm(median_beta))),
                        'max_single_plant_term_over_contrast_norm':float(influence.max()),
                        'most_influential_GlobalID':part.GlobalID.iloc[int(np.argmax(influence))]})
    frame=pd.DataFrame(records)
    frame.to_csv(OUT/'disagreement_diagnostics.csv',index=False)
    pd.DataFrame(block_records).to_csv(OUT/'block_rank_diagnostics.csv',index=False)
    return frame


def figures(summary, simulations, extended):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    bands=pd.read_csv(EMP/'envelopes.csv')
    cases=[('NIWO-2023','DBS − ECT','Deciduous broadleaf shrubs − evergreen conifer trees'),
           ('WREF-2023','DBT − ECT','Deciduous broadleaf trees − evergreen conifer trees'),
           ('NIWO-2023','DBT − ECS','Deciduous broadleaf trees − evergreen conifer shrubs'),
           ('NIWO-2023','DBS − DBT','Deciduous broadleaf shrubs − deciduous broadleaf trees')]
    fig,axes=plt.subplots(2,2,figsize=(14,9),squeeze=False)
    for ax,(cohort,pair,title) in zip(axes.ravel(),cases):
        rec=summary[(summary.cohort==cohort)&(summary.pair==pair)&(summary.blocking=='flight_history')].iloc[0]
        b=bands[bands.test_id==rec.test_id].sort_values('wavelength_nm')
        w=b.wavelength_nm.to_numpy()
        for lo,hi in [(1340,1450),(1790,2000)]:
            ax.axvspan(lo,hi,color='#f1f1f1',zorder=0)
        for ix in np.split(np.arange(len(w)),np.flatnonzero(np.diff(w)>8)+1):
            ax.fill_between(w[ix],b.lower_family.to_numpy()[ix],b.upper_family.to_numpy()[ix],color='#cdd1d6',label='Family-controlled null envelope' if ix[0]==0 else None)
            ax.fill_between(w[ix],b.lower_simultaneous_95.to_numpy()[ix],b.upper_simultaneous_95.to_numpy()[ix],color='#abcde5',label='95% whole-curve null envelope' if ix[0]==0 else None)
            ax.plot(w[ix],b.observed_beta.to_numpy()[ix],color='#153e62',lw=1.3,label='Observed A−B' if ix[0]==0 else None)
        use=b.excursion_family
        ax.scatter(b.loc[use,'wavelength_nm'],b.loc[use,'observed_beta'],s=5,color='#bb2844',zorder=5)
        ax.axhline(0,color='grey',lw=.5)
        ax.set_title(cohort+'\n'+title,fontsize=10)
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('A−B contrast (stored spectral units)')
        ax.text(.02,.97,f'NPC adjusted p={rec.p_npc_holm:.4g}; max adjusted p={rec.p_max_holm:.4g}',transform=ax.transAxes,va='top',fontsize=9,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'})
    axes[0,0].legend(loc='lower right',fontsize=8)
    fig.suptitle('Illustrative audit cases: observed PFT contrast versus simultaneous null envelopes\nGrey/red: Bonferroni over 21 matched contrasts; scalar p-values use Holm. Not biological-effect confidence bands.',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94))
    for ext in ('png','pdf'):
        fig.savefig(OUT/f'illustrative_simultaneous_envelopes.{ext}',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    x=np.arange(len(extended))
    axes[0].errorbar(x,extended.rate,yerr=[extended.rate-extended.wilson_low,extended.wilson_high-extended.rate],fmt='o',capsize=4)
    axes[0].axhline(.05,color='#b32d3e',ls='--',label='Nominal 5%')
    axes[0].set(xticks=x,xticklabels=extended.method,title='Exchangeable null: 5,000 datasets',ylabel='Rejection rate',ylim=(0,.09))
    axes[0].tick_params(axis='x',rotation=25)
    axes[0].legend()
    methods=['max','integrated','npc','energy','fpca']
    scenarios=['localized','broad_weak','extreme_imbalance_broad','shape']
    x=np.arange(len(scenarios))
    for j,method in enumerate(methods):
        vals=simulations[(simulations.method==method)].set_index('scenario').loc[scenarios]
        axes[1].bar(x+(j-2)*.15,vals.rate,yerr=[vals.rate-vals.wilson_low,vals.wilson_high-vals.rate],capsize=2,width=.14,label=method)
    axes[1].set(xticks=x,xticklabels=['Localized','Broad weak','Broad, 10:390','Shape'],ylim=(0,1.05),ylabel='Power',title='Alternatives: 1,000 datasets each')
    axes[1].legend(ncol=2,fontsize=8)
    fig.suptitle('Simulation diagnostics for the recorded designs; intervals show Monte Carlo uncertainty')
    fig.tight_layout()
    for ext in ('png','pdf'):
        fig.savefig(OUT/f'simulation_comparison.{ext}',dpi=170)
    plt.close(fig)


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    emp=verify(EMP,'audit_manifest.json')
    design=json.loads((HERE/'DESIGN_METRICS.json').read_text())
    if emp['identity']['legacy'] != design['source_manifest_sha256']:
        raise ValueError('Interpretive prose is specific to the audited supplied library')
    sim=verify(SIM,'simulation_manifest.json')
    ext_meta=json.loads((SIM/'exchangeable_null_extended.json').read_text())
    if _file_hash(SIM/'exchangeable_null_extended.csv')!=ext_meta['sha256']:
        raise ValueError('Invalid extended null ledger')
    summary=pd.read_csv(EMP/'method_comparison.csv')
    oldroot=REPO/'artifacts/plant_spectral_atlas/pft_statistics'
    oldmanifest=json.loads((oldroot/'statistics_manifest.json').read_text())
    if _file_hash(oldroot/'pairwise_tests.csv') != oldmanifest['outputs']['pairwise_tests.csv']:
        raise ValueError('Changed legacy test table')
    oldtable=pd.read_csv(oldroot/'pairwise_tests.csv').set_index('test_id')
    summary['p_rank']=summary.test_id.map(oldtable.p_rank)
    for blocking in ('site_year','flight_history'):
        use=summary.status.eq('tested') & summary.blocking.eq(blocking)
        summary.loc[use,'p_rank_holm']=holm(summary.loc[use,'p_rank'])
    simulations=pd.read_csv(SIM/'simulation_summary.csv')
    extended=pd.read_csv(SIM/'extended_null_summary.csv')
    figures(summary,simulations,extended)
    diag=diagnostics(summary)
    valid=summary.query('status=="tested" and blocking=="flight_history"').copy()
    # Fixed multiplicity-budget comparison is conservative and distinct from
    # the old 324-member Holm family, which cannot be recreated for new methods.
    for method in ('max','integrated','npc','energy','fpca'):
        summary['p_'+method+'_bonferroni324']=np.minimum(1,summary['p_'+method]*324)
    summary.to_csv(OUT/'comparison_with_multiplicity_budget.csv',index=False)
    common=valid[['cohort','pair','legacy_max_holm_324',*[f'p_{m}_holm' for m in ('max','integrated','npc','energy','fpca','rank')]]].copy()
    common=common.rename(columns={'legacy_max_holm_324':'legacy max (324)',**{f'p_{m}_holm':m+' (21)' for m in ('max','integrated','npc','energy','fpca','rank')}})
    display=common.copy()
    for col in display.columns[2:]:
        display[col]=display[col].map(lambda x:f'{x:.4g}')
    common.to_csv(HERE/'METHOD_COMPARISON.csv',index=False)
    simulations.to_csv(HERE/'SIMULATION_SUMMARY.csv',index=False)
    extended.to_csv(HERE/'EXTENDED_NULL_SUMMARY.csv',index=False)
    consistency=pd.read_csv(EMP/'cross_site_curve_consistency.csv')
    consistency.to_csv(HERE/'CROSS_SITE_CONSISTENCY.csv',index=False)
    sim_display=simulations.pivot(index='scenario',columns='method',values='rate').reset_index().fillna('—')
    for col in sim_display.columns[1:]:
        sim_display[col]=sim_display[col].map(lambda x:f'{100*x:.1f}%' if isinstance(x,(float,int)) else x)
    null_display=extended.copy()
    null_display['rate (95% MC interval)']=null_display.apply(lambda r:f'{100*r.rate:.2f}% ({100*r.wilson_low:.2f}–{100*r.wilson_high:.2f}%)',axis=1)
    lines=['# Results, calibrated recommendation and paper claim','',
           'Audit date: 2026-10-14. Existing outputs remain unchanged. See the four audit/review/design/recommendation documents in this directory. This is an exploratory analysis following inspection of the plots and earlier results, not a prospectively registered confirmatory study.','',
           '## What was run','',
           '54 eligible corrected-NEON contrasts, exactly the same units, supported bands and blocks across methods, with 9,999 permutations each. Every maximum-test raw p-value reproduces its legacy value exactly. All methods use the same plants: agreement is sensitivity evidence, not independent biological replication. Maximum envelopes are the same test visualized, not an independent confirmation. Integrated and FPCA contrasts are functional-response fixed-block adaptations; energy is a predeclared block-weighted distance adaptation. GET ERL and full functional mixed models were reviewed but not executed (R unavailable; unrestricted species+PFT effects aliased).', '',
           'The primary family is the 21 acquisition-matched corrected contrasts. Methods are compared with Holm across that same 21-member family each; site/year-only sensitivity uses 33. This is different from the old combined 324-test family. The complete legacy values and a fixed Bonferroni×324 sensitivity for each new method are retained. Smaller adjusted values caused by changing the family are not new biological evidence. No union-of-methods rejection rule is used. Repeated adjusted p=0.0021 values reflect the 0.0001 Monte Carlo floor in a 21-test family, not identical biological effect strengths.','',
           'The graph scales A−B by s(lambda)/sqrt(q), a fixed, label-invariant variance proxy. It is not a Welch SE or necessarily the exact permutation SD when block variances differ. Envelope validity uses fixed scaling plus whole-curve exchangeability, not that proxy being a perfect variance estimator. The CSV field null_se names this proxy; it must be interpreted accordingly.','',
           '## Empirical method comparison','',md_table(display),'',
           '## Biological conclusions and disagreements','',
           '- **DBS–ECT and DBT–ECT:** supported by every compared method in all four cohorts, including acquisition matching. The central broadleaf-versus-conifer-tree sampled-mixture conclusion does not depend on using only a maximum statistic. This remains association among the sampled taxa, not a species-independent mechanism.',
           '- **DBT–ECS:** max/integrated/NPC remain nonsignificant in both NIWO years. FPCA rejects in NIWO 2020 but not 2023. The projection test weights a limited whitened covariance subspace and has a different sensitivity; this isolated sensitivity result is not adopted as the primary conclusion.',
           '- **DBS–DBT:** WREF remains supported. NIWO 2020 remains unresolved by the primary test, while FPCA alone rejects. NIWO 2023 becomes borderline (NPC adjusted p=0.045) only in the narrower 21-test family; even the unchanged max p becomes significant under that family. The fixed ×324 comparison does not support it. This is family/Monte-Carlo-sensitive, not a robust new discovery. YELL lacks minimum matched support.',
           '- **ECS–ECT:** NIWO mean/integrated/NPC/energy/FPCA tests agree on a conditional association, whereas the legacy rank sensitivity does not. The weighted mean and weighted median contrast curves have cosines about 0.996 in both NIWO years. At their mean-statistic peak, weighted median contrasts have the same sign and similar amplitude as means. Thus the rank disagreement cannot simply be called an outlier artifact. The old rank test uses unnormalized within-block ranks: rank ranges and variance mass depend on block size (roughly cubic variance mass for untied ranks). It is not a pure neutral outlier-removal transformation. These diagnostics and unequal overlap help explain changed sensitivity; they do not prove either statistic uniformly better. ECS remains one species globally, and YELL shows no corresponding supported contrast.',
           '- **NIWO 2023 DBS–ECS:** energy and FPCA reject while max/integrated/NPC do not. Distribution/covariance geometry and projection sensitivity differ from mean-functional evidence. Do not choose the sensitivity result with the lowest p-value.',
           '- **Acquisition conditioning:** support shrinks and target mixtures change. A pooled significance loss can be reduced power, changed species composition or acquisition association; it is not by itself proof of a flight artifact.','',
           '## Distributional disagreement diagnostics','',
           'The table below reports descriptive pooled within-PFT/history residual trace-variance ratios (A/B), weighted-median versus mean curve cosine, and within-block Cliff delta at the mean-statistic peak. These are not new significance tests. A ratio different from one can help explain energy/projection sensitivity, but does not by itself prove why a particular p-value changed. Largest individual linear-term ratios and block rank-variance masses remain in the ignored interpretation tables for source-traceable review.','',
           md_table(diag[diag.pair.isin(['DBS − ECS','ECS − ECT','DBT − ECS'])][['cohort','pair','dispersion_trace_ratio_a_over_b','mean_median_curve_cosine','peak_weighted_cliffs_delta']].round(4)),'',
           '## Cross-site direction/shape (H3)','',
           'Use the three 2023 sites only for the independent-site comparison. For DBS–ECT and DBT–ECT, contrast-curve cosine similarities are positive and high; the full matrix below is descriptive rather than a random-site population test. DBS–DBT and ECS–ECT do not show a universal direction/shape. NIWO 2020 is a repeated-site view, not a fourth independent site.','',
           md_table(consistency.round(4)), '',
           '## Simulation calibration and power','',
           'Nine initial scenarios plus two extreme-imbalance checks added after inspecting real support, 1,000 independently generated datasets each, 499 permutations per dataset. Curves use smooth correlated noise, unequal group sizes (including 10 versus 390 plants in the extreme check), three acquisition histories, four repeated observations reduced to one plant curve, atmospheric gaps and an isolated unsupported sample. No gap imputation occurs. Rejection rates below concern one test per simulated study, not the empirical 21-contrast multiplicity family. The generator is stylized rather than fitted to the exact crowns. These results demonstrate comparative behavior in this design, not universal optimality or validity in real spatially dependent crowns.','',
           md_table(sim_display),'',
           'The exchangeable null was expanded to 5,000 datasets after an initial noisy calibration estimate, retaining the original 1,000 and adding 4,000 independent replicates. The 95% Wilson intervals quantify Monte Carlo uncertainty in rejection rates, not uncertainty in biological effects.','',
           md_table(null_display[['method','replicates','rate (95% MC interval)']]),'',
           'The combined test materially improves broad-weak sensitivity relative to max alone while retaining localized sensitivity in these simulations. The integrated statistic alone sacrifices localized power; NPC is not uniformly most powerful (for example, max is slightly better in the shape scenario). The NPC null rate is compatible with 5%; no gain is credited to an inflated equal-means rejection under heteroscedasticity.','',
           'The unequal-covariance scenario has equal means but different distributions: energy rejection is a true distributional alternative, and increased mean-focused rejection demonstrates why the strong exchangeability guarantee must not be recast as an arbitrary equal-means guarantee. The species-cluster scenario has no PFT coefficient but shared species functions; high rejection shows these plant-level tests cannot establish H4. Naively permuting repeated rows or ignoring strongly imbalanced acquisition blocks gives grossly misleading rejection rates.','',
           '## Exact paper recommendation','',
           '**Primary:** blocked, synchronized max-plus-integrated nonparametric combination of the whole plant contrast function, corrected NEON, exact flight/source-history conditioning, and a declared cohort/pair multiplicity family. Keep the maximum component and its simultaneous envelope as the principal graphical explanation.','',
           '**Sensitivity:** original maximum test, integrated norm, carefully interpreted rank sensitivity, energy distance and a label-blind reduced-rank functional model; show acquisition support and species composition. No method is a substitute for valid units or independent taxa.','',
           '**Claim:** “Among the sampled species mixtures, corrected whole-spectrum structure is associated with assigned PFT within matched acquisition contexts. Contrasts between sampled evergreen conifer trees and sampled deciduous broadleaf tree/shrub groups recur across NIWO, WREF and YELL. These observations do not isolate PFT from species composition, demonstrate a causal trait mechanism, or establish classification/detection accuracy.”','',
           'A colleague-facing description: We compared whole plant/year curves. Within shared acquisition histories we permuted each whole plant PFT label, preserving its entire spectrum and wavelength covariance. A synchronized combination of maximum and integrated contrast asks whether localized or distributed differences exceed those expected under that conditional exchangeability null. It gives one whole-spectrum probability; the simultaneous maximum envelope locates excursions of the maximum component, not every possible reason for combined rejection.','',
           '## Limitations and next validation','',
           'No test here establishes H4–H6. The primary guarantee is conditional on the exchangeability assumptions audited in CURRENT_METHOD_AUDIT.md. Spatial/plant identity uncertainty, inferred traits and species dominance remain. Add independent ECS/EBS taxa and spatial/field-trait covariates. A future species/site-held-out prediction study is needed for transfer/classification, with plant leakage prevented and unavailable classes explicitly excluded or abstained.','',
           'References and method-specific nulls are in METHODS_REVIEW.md. Code, seeds, supported domains, primary/sensitivity families and all output checksums are retained. The scalar and graphical thresholds differ when Holm is less conservative than the fixed Bonferroni envelope; do not reinterpret an envelope as a biological-effect confidence interval.','']
    (HERE/'RESULTS.md').write_text('\n'.join(lines))
    # Compact publication-facing summaries retained; individual IDs stay ignored.
    for n in ['METHOD_COMPARISON.csv','SIMULATION_SUMMARY.csv','EXTENDED_NULL_SUMMARY.csv','CROSS_SITE_CONSISTENCY.csv','RESULTS.md']:
        shutil.copyfile(HERE/n,OUT/n)
    _write_json(OUT/'interpretation_manifest.json',{'code':_file_hash(Path(__file__)),
                  'empirical_manifest':_file_hash(EMP/'audit_manifest.json'),
                  'simulation_manifest':_file_hash(SIM/'simulation_manifest.json'),
                  'extended_null_ledger':_file_hash(SIM/'exchangeable_null_extended.json'),
                  'empirical_code':emp['identity']['code'],'simulation_code':sim['identity']['simulation_code'],
                  'outputs':{p.name:_file_hash(p) for p in OUT.iterdir() if p.is_file() and p.name!='interpretation_manifest.json'}})


if __name__=='__main__':
    run()
