"""Eight panels with a shared visual language; no statistical inference here."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from examples.publication_figures.figure_data import CATEGORIES, COLORS, STYLES, segments

SYNTHETIC = '#0072B2'
PFT_COLORS = {'DBS': '#CC79A7', 'DBT': '#D55E00', 'ECT': '#0072B2'}
COHORTS = ['NIWO-2020', 'NIWO-2023', 'WREF-2023', 'YELL-2023']


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5,
        'axes.labelsize': 7.5, 'axes.titlesize': 8.5, 'axes.titleweight': 'bold',
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 6.5,
        'axes.linewidth': .55, 'lines.linewidth': 1.1, 'xtick.major.width': .5,
        'ytick.major.width': .5, 'axes.spines.top': False, 'axes.spines.right': False,
        'pdf.fonttype': 42, 'svg.fonttype': 'none',
        'svg.hashsalt': 'spectralbridge-publication-2026-10-14', 'savefig.facecolor': 'white'})


def heading(ax, letter, title):
    ax.set_title(title, loc='left', pad=10)
    ax.text(-.14, 1.065, letter, transform=ax.transAxes, fontweight='bold', fontsize=11)


def spectral_axis(ax):
    for lo, hi in [(1340, 1450), (1790, 2000)]:
        ax.axvspan(lo, hi, color='#f0f0f0', zorder=-5)
    ax.set(xlim=(380, 2510), xlabel='Wavelength (nm)')
    ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.tick_params(length=3)


def category_legend(ax, **kwargs):
    return ax.legend(handles=[Line2D([], [], color=COLORS[c], ls=STYLES[c], label=c) for c in CATEGORIES],
                     frameon=False, handlelength=2.4, **kwargs)


def plot_spectral_atlas(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'A', 'Corrected spectral atlas')
    w = d['waves']['NEON']
    y = d['spectra']['NEON']
    for cat in CATEGORIES:
        q = np.quantile(y[d['table'].cover_category.eq(cat)], [.25, .5, .75], axis=0)
        for ix in segments(w):
            ax.fill_between(w[ix], q[0, ix], q[2, ix], color=COLORS[cat], alpha=.12, lw=0)
            ax.plot(w[ix], q[1, ix], color=COLORS[cat], ls=STYLES[cat], lw=1.25)
    spectral_axis(ax)
    ax.set_ylabel('Corrected reflectance (stored units)')
    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
    category_legend(ax, loc='upper right', ncol=1, labelspacing=.35)
    ax.text(.02, .96, f"{len(y):,} polygon/year spectra\nMedian + empirical 25–75% interval", transform=ax.transAxes,
            va='top', fontsize=6.5)
    return [ax]


def plot_library_structure(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'B', 'Sampling hierarchy')
    ax.set_axis_off()
    c = d['counts']
    lines = [(f"{c['identities']:,}", 'polygon / plant identities'),
             (f"{c['pixel_rows']:,}", 'extracted pixel records'),
             (f"{c['polygon_years']:,}", 'polygon/year spectra')]
    for i, (value, label) in enumerate(lines):
        y = .94 - i * .18
        ax.text(.02, y, value, fontsize=13, weight='bold', transform=ax.transAxes)
        ax.text(.02, y - .065, label, fontsize=7, transform=ax.transAxes)
        if i < 2:
            ax.annotate('', xy=(.5, y - .155), xytext=(.5, y - .085), xycoords='axes fraction',
                        arrowprops=dict(arrowstyle='->', color='#777777', lw=.6))
    ax.text(.02, .43, f"{c['species_identified']:,} with species recorded\n{c['species_missing']:,} without species\n{c['cover_categories']} researcher cover categories",
            transform=ax.transAxes, fontsize=6.5, linespacing=1.35, va='top')
    counts = d['table'].groupby(['site', 'year']).size()
    ax.text(.02, .21, f"{c['sites']} sites · {c['years']} years", transform=ax.transAxes, weight='bold')
    ax.text(.02, .16, '\n'.join(f'{s} {y}: {n:,}' for (s, y), n in counts.items()),
            transform=ax.transAxes, fontsize=6.5, linespacing=1.35, va='top')
    return [ax]


def plot_morphospace(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'C', 'Spectral morphospace')
    markers = {'NIWO': 'o', 'WREF': '^', 'YELL': 's'}
    table, scores = d['table'], d['scores']
    # Every observation retained; shared draw order avoids category-order priority.
    rng = np.random.default_rng(20261014)
    order = rng.permutation(len(table))
    for site, marker in markers.items():
        ix = order[table.site.to_numpy()[order] == site]
        ax.scatter(scores[ix, 0], scores[ix, 1], c=[COLORS[x] for x in table.cover_category.iloc[ix]],
                   s=5, alpha=.22, marker=marker, edgecolors='none', rasterized=True)
    ax.set(xlabel=f"PC1 ({100*d['variance'][0]:.1f}% variance)", ylabel=f"PC2 ({100*d['variance'][1]:.1f}% variance)")
    ax.legend(handles=[Line2D([], [], marker=m, color='#555555', ls='', ms=3, label=s) for s, m in markers.items()],
              frameon=False, loc='upper right', handletextpad=.35)
    ax.text(.02, .025, 'All polygon/years · no clipping', transform=ax.transAxes, fontsize=6.5)
    return [ax]


def plot_sensor_representation(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'D', 'From NEON to seven OLI bands')
    w, centers = d['waves']['NEON'], d['oli_centers']
    for cat in CATEGORIES:
        i = d['representatives'][cat]
        for ix in segments(w):
            ax.plot(w[ix], d['spectra']['NEON'][i, ix], color=COLORS[cat], ls=STYLES[cat], lw=.9)
        ax.scatter(centers, d['spectra']['OLI'][i], s=13, color=COLORS[cat], marker='D',
                   edgecolors='white', linewidths=.35, zorder=5)
    spectral_axis(ax)
    ax.set_ylabel('Corrected reflectance (stored units)')
    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
    for j, x in enumerate(centers):
        ax.plot([x, x], [.015, .045], transform=ax.get_xaxis_transform(), color=SYNTHETIC, lw=.6)
    ax.legend(handles=[Line2D([], [], color='#555555', label='NEON spectrum'),
                       Line2D([], [], color=SYNTHETIC, ls='', marker='D', ms=3, label='Synthetic OLI')], frameon=False, loc='upper right')
    return [ax]


def plot_effect_matrix(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'A', 'Whole-spectrum PFT contrasts')
    data = d['effects']
    pairs = sorted(data.contrast.unique())
    m = data.pivot(index='contrast', columns='cohort', values='NEON_effect').reindex(index=pairs, columns=COHORTS)
    vmax = np.ceil(data.NEON_effect.max() * 10) / 10
    cmap = plt.get_cmap('cividis').copy()
    cmap.set_bad('#eeeeee')
    im = ax.imshow(m, aspect='auto', cmap=cmap, vmin=0, vmax=vmax)
    for row in data.itertuples():
        if row.NEON_supported:
            i, j = pairs.index(row.contrast), COHORTS.index(row.cohort)
            ax.text(j, i, '●', ha='center', va='center', color='white' if row.NEON_effect < .9 else 'black', fontsize=7)
    ax.set_xticks(range(4), ['NIWO\n2020', 'NIWO\n2023', 'WREF\n2023', 'YELL\n2023'], fontsize=6.5)
    ax.set_yticks(range(len(pairs)), [x.replace(' / ', '–') for x in pairs])
    ax.tick_params(length=0)
    for label, pair in zip(ax.get_yticklabels(), pairs):
        if pair in ['DBS / ECT', 'DBT / ECT']:
            label.set_color(PFT_COLORS[pair[:3]])
    cb = fig.colorbar(im, ax=ax, fraction=.05, pad=.03)
    cb.set_label('Standardized RMS contrast', fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    ax.text(0, -.20, '● Adjusted NPC p < 0.05\nGray: insufficient matched support', transform=ax.transAxes, fontsize=6.5, va='top')
    return [ax, cb.ax]


def plot_spectral_localization(fig, spec, d):
    gs = spec.subgridspec(2, 1, hspace=.35, height_ratios=[1, 1])
    axes = []
    for i, a in enumerate(['DBS', 'DBT']):
        ax = fig.add_subplot(gs[i])
        if i == 0:
            heading(ax, 'B', 'Where the contrasts occur')
        t = d['localization'][d['localization'].contrast.eq(a + ' / ECT')]
        w, y = t.wavelength_nm.to_numpy(), t.standardized_delta.to_numpy()
        for ix in segments(w):
            ax.plot(w[ix], y[ix], color=PFT_COLORS[a], ls='-' if i == 0 else '--')
            ax.plot(w[ix], np.where(t.excursion_family.to_numpy()[ix], y[ix], np.nan), color=PFT_COLORS[a], lw=2.0)
        ax.axhline(0, color='#888888', lw=.5)
        spectral_axis(ax)
        ax.set_ylabel('Signed β / s')
        ax.text(.98, .92, f'{a} – ECT', ha='right', va='top', transform=ax.transAxes, fontsize=7)
        if i == 0:
            ax.set_xlabel('')
            ax.tick_params(labelbottom=False)
            ax.text(.02, .91, 'NIWO 2023', transform=ax.transAxes, va='top', fontsize=6.5)
        for x in d['oli_centers']:
            ax.plot(x, .04, 'D', color=SYNTHETIC, ms=2.4, transform=ax.get_xaxis_transform())
        axes.append(ax)
    axes[-1].text(0, -.55, 'Thick: family-controlled null excursion\n◆ OLI centers; atmospheric gaps shaded', transform=axes[-1].transAxes, fontsize=6.5, va='top')
    return axes


def plot_sensor_retention(fig, spec, d):
    ax = fig.add_subplot(spec)
    heading(ax, 'C', 'Contrast structure survives OLI')
    data = d['effects']
    groups = [(data.NEON_supported & data.OLI_supported, 'o', SYNTHETIC, 'Supported in both'),
              (data.NEON_supported & ~data.OLI_supported, '^', '#D55E00', 'NEON support only'),
              (~data.NEON_supported & ~data.OLI_supported, 's', '#777777', 'Unsupported in both')]
    for mask, marker, color, label in groups:
        ax.scatter(data.loc[mask, 'NEON_effect'], data.loc[mask, 'OLI_effect'], color=color, marker=marker, s=23,
                   edgecolor='white', linewidth=.4, label=label)
    upper = max(data.NEON_effect.max(), data.OLI_effect.max()) * 1.08
    ax.plot([0, upper], [0, upper], ':', color='#777777', lw=.8, zorder=-1)
    ax.set(xlim=(0, upper), ylim=(0, upper), xlabel='NEON standardized RMS contrast', ylabel='Synthetic OLI standardized RMS contrast')
    ax.set_aspect('equal', adjustable='box')
    pear = d['correlations'].query("method == 'Pearson'").correlation.iloc[0]
    spear = d['correlations'].query("method == 'Spearman'").correlation.iloc[0]
    r = d['retention']
    ax.text(.035, .96, f"Pearson r = {pear:.3f}\nSpearman ρ = {spear:.3f}\n{int(r.retained)}/{int(r.NEON_supported)} NEON-supported retained", transform=ax.transAxes, va='top', fontsize=6.8)
    ax.legend(frameon=False, loc='lower right', handletextpad=.3, labelspacing=.4)
    exception = data[data.NEON_supported & ~data.OLI_supported].iloc[0]
    ax.annotate('NIWO 2023\nDBS–DBT', xy=(exception.NEON_effect, exception.OLI_effect), xytext=(1.35, .70),
                fontsize=6.5, arrowprops={'arrowstyle': '-', 'lw': .5, 'color': '#555555'})
    return [ax]


def plot_real_landsat_validation(fig, spec, d):
    # Native-aspect maps share one extent/mask/stretch. A container owns heading.
    container = fig.add_subplot(spec)
    container.set_axis_off()
    heading(container, 'D', 'One independent Landsat pilot')
    grid = spec.subgridspec(5, 1, height_ratios=[.2, 1, 1, 1, .95], hspace=.32)
    common, images = d['images']['common'], d['images']
    transform = d['grid']['transform']
    x0, y0 = transform[2], transform[5]
    extent = [x0 / 1000, (x0 + transform[0] * common.shape[1]) / 1000,
              (y0 + transform[4] * common.shape[0]) / 1000, y0 / 1000]
    axes = [container]
    for i, (key, title) in enumerate([('undarkened', 'Synthetic OLI · NEON 15 Sep 2021'),
                                    ('actual', 'Real Landsat 8 · 16 Sep 2021'), ('residual', 'NIR residual: synthetic − real')]):
        ax = fig.add_subplot(grid[i+1])
        ax.set_facecolor('#e4e4e4')
        if key != 'residual':
            rgb = np.moveaxis(images[key][[3, 2, 1]], 0, -1) / .4
            rgba = np.dstack([np.nan_to_num(np.clip(rgb, 0, 1)), common.astype(float)])
            ax.imshow(rgba, extent=extent, interpolation='nearest', aspect='equal')
        else:
            residual = np.where(common, images['undarkened'][4] - images['actual'][4], np.nan)
            ax.imshow(residual, cmap='RdBu_r', vmin=-.15, vmax=.15, extent=extent, interpolation='nearest', aspect='equal')
        ax.set_title(title, loc='left', fontsize=6.5, fontweight='normal', pad=2)
        ax.set_xticks([])
        ax.set_yticks([])
        if i == 1:
            ax.plot([extent[0]+.15, extent[0]+1.15], [extent[2]+.1]*2, color='white', lw=1.7)
            ax.text(extent[0]+.65, extent[2]+.15, '1 km', color='white', ha='center', fontsize=6.5)
        axes.append(ax)
    last = grid[4].subgridspec(2, 1, height_ratios=[.3, 1], hspace=1.7)
    cbax = fig.add_subplot(last[0])
    cb = fig.colorbar(ScalarMappable(norm=Normalize(-.15, .15), cmap='RdBu_r'), cax=cbax, orientation='horizontal')
    cb.set_ticks([-.15, 0, .15])
    cb.ax.tick_params(labelsize=6.5, length=2, pad=1)
    cb.set_label('NIR reflectance difference (unitless)', fontsize=6.5, labelpad=0)
    ax = fig.add_subplot(last[1])
    ax.axis('off')
    f, m = d['flight'], d['metrics']
    ax.text(0, 1, f"RMSE {f.pooled_seven_band_RMSE:.4f} · median angle {f.median_spectral_angle_deg:.2f}°\n"
            f"Bandwise r {m.Pearson_r.min():.2f}–{m.Pearson_r.max():.2f} · {int(f.N):,} footprints\n"
            'Same 0–0.4 RGB stretch · common 30 m grid/mask', transform=ax.transAxes, fontsize=6.5, va='top', linespacing=1.35)
    axes += [cbax, ax]
    return axes
