# Suggested figure caption

Plant functional types across three Landsat-mode products. **A**, Lines show category medians and shaded ribbons show the 25th–75th percentiles of footprint-level normalized spectra. Every spectrum, including its SWIR bands when available, is divided by its own B1–B5 sum before calculating medians and quantiles. Ribbons describe variation among sampled footprints; they are not confidence intervals or instrument error estimates. Counts follow the legend order: unique Landsat cells, NEON polygons and drone polygons. NEON repeat years are averaged within polygon before normalization; drone pixels are summarized by their polygon median. Real Landsat spectra are from the QA-screened Niwot scene acquired 20 August 2023; polygon association does not establish full-cell purity. NEON spectra are synthetic OLI products. Drone spectra use native MicaSense bands as conceptual B1–B5 proxies and have no B6/B7 observations. The three strips show absolute differences between category medians multiplied by 100 for each sensor pair and band; gray cells have no shared band. Differences are descriptive and confound sensor, sample, date and footprint effects.

**B**, S summarizes separability evidence and I summarizes held-out identification. NEON S values report supported contrasts against four other categories across four site-years, using Holm-adjusted p ≤ 0.05. NEON I values report mean class recall on unseen polygons / held-out sites. These tests use all seven synthetic OLI bands. Real Landsat S entries use the separate provisional photo-screened reference dataset at the frozen primary 95% cover threshold and zero positional shift. Four distinct footprints (three herbaceous and one non-vegetated) pass that photo screen, supplying seven annual observations. Only one herbaceous and one non-vegetated footprint share an eligible acquisition, Landsat 9 in Yellowstone on 18 August 2024. The two daggered table entries refer to this same single contrast, not two independent tests. Exact NPC and Holm-adjusted p are both 1.00 across two possible label assignments; this extremely small matched cohort cannot establish separability. Other classes lack matched photo-reference support. Photo labels are from one interpreter without independent or field verification. These provisional test references are distinct from the larger descriptive spectral cohort shown in A. Landsat identification and drone separability/identification remain untested.

# Reproduction and sources

Run from the repository root:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_pft_panel.py
```

- Figure builder: `examples/publication_figures/landsat_pft_panel.py`.
- Primary Landsat statistics: `provenance/landsat-pure-pixels/2026-11-18/photo-annotation/separability.csv`, threshold 0.95 and shift_m 0.
- Reference interpretation and limitations: `provenance/landsat-pure-pixels/2026-11-18/photo-annotation/RESULTS.md` and `annotation_policy.json`.
- NEON separability: `provenance/researcher-evidence/2026-10-16/v1/tables/whole_spectrum_separability.csv`.
- Held-out recall: `provenance/researcher-pft-information/2026-10-15/v1/tables/reused_researcher_class_rates_all_domains.csv`, representation OLI, experiment hierarchy.
- Spectral source paths, band mappings and aggregation are defined in the builder. Inputs and scientific test results were not modified for this revision.
