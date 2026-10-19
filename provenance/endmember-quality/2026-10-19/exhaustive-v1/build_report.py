"""Human-readable paired comparison from compact exhaustive results."""
import base64
import json
import platform
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from run_exhaustive import OUT, PREVIOUS

CLASSES = ['Deciduous', 'Evergreen', 'Herbaceous', 'Non-vegetated & dead', 'Woody shrub']


def rmse(a, b):
    return float(np.sqrt(np.mean((a-b)**2)))


def main():
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none', 'savefig.facecolor': 'white'})
    figures = OUT/'figures'
    figures.mkdir(exist_ok=True)
    with np.load(OUT/'full_results.npz', allow_pickle=False) as z:
        result = {k: z[k] for k in z.files}
    truth, full = result['truth'], result['fractions']
    record = pd.read_csv(OUT/'exhaustive_predictions.csv', float_precision='round_trip')
    bundle = record.bundle.to_numpy()
    prior = PREVIOUS/'tables'
    methods = {'Screened selected (3/category)': 'selected', 'Screened selected (5/category)': 'screen5',
               'Screened matched random (one draw)': 'matched', 'Dense design prior': 'uniform',
               'Sparse design prior': 'sparse', 'Known-parent oracle': 'known-parent'}
    predictions = {'Exhaustive selected': full}
    for name, prefix in methods.items():
        frame = pd.read_csv(prior/(prefix+'_synthetic_predictions.csv'), float_precision='round_trip').sort_values('target')
        np.testing.assert_array_equal(frame.target.to_numpy(), record.target.to_numpy())
        np.testing.assert_allclose(frame[[f'truth_{j}' for j in range(1, 6)]], truth, atol=1e-15)
        predictions[name] = frame[[f'prediction_{j}' for j in range(1, 6)]].to_numpy()
    screened = predictions['Screened selected (3/category)']
    detail = pd.read_csv(prior/'screened_mesma_details.csv', float_precision='round_trip')
    d3 = detail[detail.method == 'Selected screened MESMA'].sort_values('target')
    d5 = detail[detail.method == 'Screen5 sensitivity'].sort_values('target')
    oldres = d3.reconstruction_RMSE.to_numpy()
    assert np.all(result['direct_RMSE'] <= oldres + 1e-9)
    assert np.all(result['direct_RMSE'] <= d5.reconstruction_RMSE.to_numpy() + 1e-9)
    metrics = []
    for name, prediction in predictions.items():
        metrics.append(dict(method=name, fraction_RMSE=rmse(prediction, truth),
                            fraction_MAE=float(np.mean(abs(prediction-truth))),
                            mean_target_fraction_RMSE=float(np.sqrt(np.mean((prediction-truth)**2, axis=1)).mean())))
    metric = pd.DataFrame(metrics)
    metric.to_csv(OUT/'method_comparison.csv', index=False)
    classrows = []
    for name in ('Exhaustive selected', 'Screened selected (3/category)'):
        p = predictions[name]
        for j, c in enumerate(CLASSES):
            absent, low = truth[:, j] == 0, (truth[:, j] > 0) & (truth[:, j] <= .2)
            classrows.append(dict(method=name, category=c, fraction_RMSE=rmse(p[:, j], truth[:, j]),
                                  bias=float((p[:, j]-truth[:, j]).mean()),
                                  false_positive_at_0_1=float((p[absent, j] >= .1).mean()),
                                  low_fraction_miss_at_0_1=float((p[low, j] < .1).mean())))
    pd.DataFrame(classrows).to_csv(OUT/'category_diagnostics.csv', index=False)
    domainrows = []
    for keys, domain in record.groupby(['site', 'year', 'components']):
        ix = domain.index.to_numpy()
        domainrows.append(dict(site=keys[0], year=int(keys[1]), components=int(keys[2]), targets=len(ix),
                               exhaustive_RMSE=rmse(full[ix], truth[ix]),
                               screened_RMSE=rmse(screened[ix], truth[ix])))
    pd.DataFrame(domainrows).to_csv(OUT/'domain_complexity_diagnostics.csv', index=False)
    # Paired whole-parent-bundle bootstrap; identical target weights for all methods.
    rng = np.random.default_rng(20261019)
    draws = rng.integers(0, 8, size=(1999, 8))
    bundle_mse = {name: np.array([np.mean((p[bundle == b]-truth[bundle == b])**2) for b in range(8)])
                  for name, p in predictions.items()}
    comparisons = []
    for name in predictions:
        if name == 'Exhaustive selected':
            continue
        difference = np.sqrt(bundle_mse['Exhaustive selected'][draws].mean(1))-np.sqrt(bundle_mse[name][draws].mean(1))
        comparisons.append(dict(comparator=name,
                                exhaustive_minus_comparator_RMSE=rmse(full, truth)-rmse(predictions[name], truth),
                                conditional_bundle_bootstrap_2_5=float(np.quantile(difference, .025)),
                                conditional_bundle_bootstrap_97_5=float(np.quantile(difference, .975))))
    pd.DataFrame(comparisons).to_csv(OUT/'paired_bundle_comparisons.csv', index=False)
    error_full = np.sqrt(np.mean((full-truth)**2, axis=1))
    error_old = np.sqrt(np.mean((screened-truth)**2, axis=1))
    delta = error_full-error_old
    spectral_drop = oldres-result['direct_RMSE']
    summary = json.loads((OUT/'full_summary.json').read_text())
    summary.update(method_metrics=metrics, paired_comparisons=comparisons,
                   winning_components={str(k): int((result['complexity'] == k).sum()) for k in (1, 2, 3)},
                   mean_screened_spectral_RMSE=float(oldres.mean()),
                   mean_exhaustive_spectral_RMSE=float(result['direct_RMSE'].mean()),
                   lower_fraction_error_targets=int((delta < -1e-8).sum()),
                   higher_fraction_error_targets=int((delta > 1e-8).sum()),
                   unchanged_fraction_error_targets=int((abs(delta) <= 1e-8).sum()),
                   improved_residual_targets=int((spectral_drop > 1e-9).sum()),
                   mean_near_class_sets={str(t): float((result['composition_errors'] <= result['RMSE'][:, None]+t).sum(1).mean())
                                         for t in (.001, .005, .01)})
    (OUT/'comparison_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    captions = []

    def save(fig, name, caption):
        fig.savefig(figures/(name+'.png'), dpi=160, bbox_inches='tight')
        fig.savefig(figures/(name+'.svg'), bbox_inches='tight')
        plt.close(fig)
        captions.append((name, caption))

    fig, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
    ax.barh(metric.method, metric.fraction_RMSE, color=['#007f88', '#b16d26', '#b16d26', '#969696', '#606060', '#969696', '#606060'])
    for i, value in enumerate(metric.fraction_RMSE):
        ax.text(value+.004, i, f'{value:.3f}', va='center')
    ax.invert_yaxis()
    ax.set(xlabel='PFT fraction RMSE (lower is better; fraction scale 0–1)', xlim=(0, .41),
           title='Does a complete spectral search recover better PFT fractions?')
    save(fig, '01_fraction_accuracy', 'Figure 1. All methods predict the same 360 synthetic targets. RMSE pools all target × category fraction errors before taking the square root. The dense prior predicts 0.2 for every category; the sparse prior predicts 1/3 for each of three fixed categories. They are design controls, not spectrum-based estimators. The oracle knows the generating parents. The random comparator remains screened and is only one matched draw.')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    colors = np.array(['#007f88', '#c27820', '#8553a2'])[record.components.to_numpy()-1]
    axes[0].scatter(oldres, result['direct_RMSE'], s=22, c=colors, alpha=.65)
    limit = max(oldres.max(), result['direct_RMSE'].max())*1.04
    axes[0].plot([0, limit], [0, limit], '--', color='gray')
    axes[0].set(xlabel='Screened spectral RMSE', ylabel='Exhaustive spectral RMSE', title='Below diagonal = better spectral fit')
    axes[1].scatter(spectral_drop, delta, c=colors, s=22, alpha=.65)
    axes[1].axhline(0, color='gray', linestyle='--')
    axes[1].set(xlabel='Spectral RMSE reduction from exhaustive search',
                ylabel='Change in per-target fraction RMSE', title='Above zero = worse PFT fractions')
    from matplotlib.lines import Line2D
    axes[1].legend(handles=[Line2D([], [], marker='o', linestyle='', color=c, label=f'{j} generating PFT'+('s' if j > 1 else '')) for j, c in enumerate(['#007f88', '#c27820', '#8553a2'], 1)], fontsize=9, loc='upper right')
    save(fig, '02_fit_vs_fractions', 'Figure 2. Each point is one target, not an independent plant replicate. Colors denote one (teal), two (orange), or three (purple) generating categories. Searching more models can lower the spectral residual without moving fractions toward the known truth. Spectral RMSE is in supplied-array units; fraction RMSE is dimensionless.')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout='constrained')
    cr = pd.DataFrame(classrows)
    positions = np.arange(5)
    for shift, name, color in [(-.18, 'Screened selected (3/category)', '#b16d26'), (.18, 'Exhaustive selected', '#007f88')]:
        rows = cr[cr.method == name]
        axes[0].barh(positions+shift, rows.fraction_RMSE, height=.34, label=name, color=color)
        axes[1].barh(positions+shift, rows.false_positive_at_0_1*100, height=.34, color=color)
    axes[0].set_yticks(positions, CLASSES)
    axes[1].set_yticks(positions, [])
    axes[0].invert_yaxis()
    axes[1].invert_yaxis()
    axes[0].set(xlabel='PFT fraction RMSE', title='Which PFT fractions are recovered?')
    axes[1].set(xlabel='False detections among true zeros (%)', title='Absent PFT predicted at ≥10%', xlim=(0, 100))
    axes[0].legend(loc='upper center', bbox_to_anchor=(.5, -.17), fontsize=9, ncol=2)
    save(fig, '03_category_errors', 'Figure 3. Each PFT has equal target weight within its row. Left: fraction errors across all targets. Right: false detections restricted to targets where that PFT is absent; prediction ≥0.10 counts as a detection. The 10% threshold is descriptive and unchanged across methods, not a validated field decision threshold.')

    # Trace and fraction examples chosen transparently by maximum improvement/worsening.
    examples = [int(delta.argmin()), int(delta.argmax())]
    library = np.load('/Users/tuff/Downloads/library_oli_undarkened_10_12_26.npy', allow_pickle=False).T
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout='constrained')
    for row, i in enumerate(examples):
        det = d3.iloc[i]
        indices = np.array(list(map(int, det.selected_array_indices.split('|'))))
        weights = np.array(list(map(float, det.selected_component_fractions.split('|'))))
        prior_recon = weights @ library[indices]
        axes[row, 0].plot(range(7), result['targets'][i], '-o', color='black', label='Known target')
        axes[row, 0].plot(range(7), prior_recon, '--', color='#b16d26', label='Screened fit')
        axes[row, 0].plot(range(7), result['reconstruction'][i], ':', color='#007f88', linewidth=2, label='Exhaustive fit')
        axes[row, 0].set_xticks(range(7), ['443', '482', '561', '655', '865', '1609', '2201'])
        axes[row, 0].set(xlabel='Band center label (nm; equal band spacing)', ylabel='Supplied-array reflectance',
                         title=f'Target {i}: '+('largest fraction improvement' if row == 0 else 'largest fraction worsening'))
        for shift, p, name, color in [(-.25, truth, 'Known fractions', 'black'), (0, screened, 'Screened', '#b16d26'), (.25, full, 'Exhaustive', '#007f88')]:
            axes[row, 1].bar(positions+shift, p[i], width=.24, label=name, color=color)
        axes[row, 1].set_xticks(positions, ['Decid.', 'Evergr.', 'Herb.', 'Nonveg.\n& dead', 'Shrub'])
        axes[row, 1].set(ylabel='Category fraction', ylim=(0, 1.05),
                         title=f'Fraction RMSE: {error_old[i]:.3f} → {error_full[i]:.3f}')
        if row == 0:
            axes[row, 0].legend(fontsize=9)
            axes[row, 1].legend(fontsize=9)
    save(fig, '04_target_examples', 'Figure 4. Deliberately selected extremes illustrate improvement and failure; they are not typical targets. The left column compares seven-band spectral reconstructions. The right column compares their PFT fractions with the exact generating weights. Closely overlapping spectral traces can correspond to different category mixtures. Nonveg. & dead is one recorded category.')

    metric_lines = '\n'.join(f'| {r.method} | {r.fraction_RMSE:.4f} | {r.fraction_MAE:.4f} |' for r in metric.itertuples())
    paired = comparisons[0]
    percent = 100*(1-summary['mean_exhaustive_spectral_RMSE']/summary['mean_screened_spectral_RMSE'])
    md = f'''# What changes when MESMA searches the entire selected library?

**Completed exhaustive internal benchmark — 19 October 2026.**

The search evaluated **16,918,447 candidate combinations for each of the same 360 synthetic targets: 6,090,640,920 target–model evaluations**. No nearest-endmember shortlist was used. The fixed library contains 603 references in five researcher-assigned categories.

The exhaustive search gave PFT fraction RMSE **{rmse(full, truth):.4f}**, compared with **{rmse(screened, truth):.4f}** for the earlier three-reference-per-category screening. Mean spectral reconstruction RMSE changed from **{oldres.mean():.6f} to {result['direct_RMSE'].mean():.6f}** ({percent:.1f}% reduction). These measure different things: matching a spectrum and recovering its known generating fractions.

## What was tested?

Each target is a known algebraic mixture of one, two or three observed seven-band polygon spectra. There are eight disjoint parent bundles, each containing five different polygon IDs, one per category. Every bundle contributes 45 targets. Its generating parent IDs are excluded from the fixed candidate library. Targets cover four observed site–acquisition-year cells and use the exact preceding target recipes. This is synthetic linear mixing of observed spectra, not independently measured ground cover.

The library contains 115 Deciduous, 166 Evergreen, 90 Herbaceous, 141 Non-vegetated & dead and 91 Woody shrub references. MESMA chooses up to three different categories, at most one reference per category, and nonnegative fractions that sum to one. It minimizes **mean squared spectral reconstruction error**, not known fraction error. All single-reference and two-reference faces are evaluated, as well as triples. No shade or additional endmembers were introduced.

## How much does exhaustive searching help?

| Method | PFT fraction RMSE | PFT fraction MAE |
| --- | ---: | ---: |
{metric_lines}

Fraction RMSE is sqrt(mean squared error over all 360 × 5 fractions); it is not the mean of 360 per-target RMSE values. Lower is better. The dense prior has five nonzero fractions and therefore a different output constraint from three-component MESMA. The sparse prior is constraint matched. The oracle supplies the actual generating spectra and is an implementation control, not an available deployment method. Comparing against a single screened random draw does not establish selector superiority.

Across targets, exhaustive searching reduced fraction error for **{summary['lower_fraction_error_targets']}**, increased it for **{summary['higher_fraction_error_targets']}**, and left it effectively unchanged for **{summary['unchanged_fraction_error_targets']}** (absolute fraction-RMSE tolerance 1e-8). Spectral error improved for {summary['improved_residual_targets']} targets by more than 1e-9 supplied-array units.

The winning exhaustive fits use one category for **{summary['winning_components']['1']}** targets, two for **{summary['winning_components']['2']}**, and three for **{summary['winning_components']['3']}**. The search chooses the smallest spectral error without a complexity penalty; the stated numerical tie rule retains earlier, lower-dimensional solutions when improvement is negligible. Generating component counts are known only for evaluation and are not supplied to the solver.

The paired exhaustive-minus-screened fraction RMSE difference is **{paired['exhaustive_minus_comparator_RMSE']:+.4f}**. Its conditional 95% whole-bundle bootstrap range is **[{paired['conditional_bundle_bootstrap_2_5']:+.4f}, {paired['conditional_bundle_bootstrap_97_5']:+.4f}]**, using 1,999 paired resamples of eight parent bundles. Negative differences favor exhaustive search. Only eight bundles are available: this describes sensitivity to those parents, not validated population coverage or a site-general significance test.

FIGURES

## What about alternative explanations for the same spectrum?

The average numbers of near-optimal distinct category sets are **{summary['mean_near_class_sets']['0.001']:.2f}**, **{summary['mean_near_class_sets']['0.005']:.2f}** and **{summary['mean_near_class_sets']['0.01']:.2f}**, at additive spectral RMSE tolerances 0.001, 0.005 and 0.01. Up to 25 sets are possible under the one-to-three-category model family. These are descriptive tolerances, not measured sensor noise. We retain one best interior solution per category set; this is a restricted ambiguity diagnostic and **does not bound every feasible fraction or prove uniqueness**.

## What does this establish, and what remains open?

This experiment separates candidate screening from full search over the declared fixed-library model family. Better spectral optimization is evidence about that model family; biological fraction accuracy must be judged from fraction errors and external observations. A globally best spectral fit need not identify the generating materials uniquely.

Selection used the whole archive. Excluding candidate parent IDs from target generation prevents direct parent reuse, but does not undo selection exposure. Results therefore remain **internal fixed-library diagnostics**, not selection-blind validation, universal sensor calibration or field PFT-cover accuracy. The targets are noiseless algebraic mixtures with constrained fractions; real scenes can include nonlinear mixing, shade, acquisition differences and materials absent from the dictionary.

The next validation step is to freeze this library and test independent targets with independently measured complete fractions, or reselect endmembers inside training-only identity/domain splits. Exhaustive random-library searches and independent site/year transfer experiments are separate work.

## Numerical audit and reproducibility

The analysis-only solver streams 1,024 models at a time, checkpoints each of 25 category sets, fingerprints inputs/code and reuses valid checkpoints on restart. Search time was {float(result['seconds']):.1f} seconds, excluding data preparation and reporting. Candidate-model storage does not grow with the 16.9-million-model count. Rank, positive-interior and improvement thresholds match the existing kernel; “exhaustive” is relative to those floating-point thresholds and the declared model family.

Regression tests compare against the existing solver and independently enumerate small libraries, including pure/boundary/degenerate cases and restart/input-mismatch behavior. The numerical audit independently reconstructs every reported winner, checks its constrained optimum using SLSQP, compares the 12-target pilot, and directly evaluates all 16.9 million models for one prespecified triple target using separate seven-band difference geometry. Original P136 packet hashes are preserved. See `numerical_validation.json`, `full_summary.json`, `full_run.log`, input/code hashes and the compact tables for exact records.
'''
    blocks = []
    for name, caption in captions:
        blocks.append(f'![{caption}](figures/{name}.png)\n\n{caption}')
    md = md.replace('FIGURES', '\n\n'.join(blocks))
    (OUT/'EXHAUSTIVE_MESMA_REPORT.md').write_text(md)
    html = markdown.markdown(md, extensions=['tables'])
    for name, _ in captions:
        encoded = base64.b64encode((figures/(name+'.png')).read_bytes()).decode()
        html = html.replace(f'figures/{name}.png', 'data:image/png;base64,'+encoded)
    css = 'body{font:17px/1.6 system-ui,sans-serif;color:#182b34;max-width:1100px;margin:36px auto;padding:0 22px}h1,h2{line-height:1.2;color:#075b63}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:.9em}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccd7da}code{overflow-wrap:anywhere}p{max-width:95ch}@media(max-width:600px){body{font-size:15px;padding:0 12px}td,th{padding:4px}}'
    (OUT/'EXHAUSTIVE_MESMA_REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Exhaustive MESMA benchmark</title><style>'+css+'</style><body>'+html+'</body></html>')
    (OUT/'environment.json').write_text(json.dumps(dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__, platform=platform.platform()), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
