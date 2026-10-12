---
title: 'SpectralBridge: An Auditable Software Workflow for Reflectance Comparisons Across NEON, Drones, and Landsat'
tags:
  - Python
  - remote sensing
  - reflectance
  - reproducible workflows
authors:
  - name: Ty Tuff
    affiliation: "1"
    orcid: 0000-0001-5249-5197
    corresponding: true
  - name: Aashish Mukund
    affiliation: "1"
  - name: Nayani T. Ilangakoon
    affiliation: "2"
    orcid: 0000-0002-6607-0605
  - name: Erick Verleye
    affiliation: "2"
    orcid: 0009-0009-8854-0127
  - name: Megan E. Cattau
    affiliation: "4"
    orcid: 0000-0003-2164-3809
  - name: Janushi Shastri
    affiliation: "2, 3"
  - name: Pavan Appanna
    affiliation: "2, 3"
  - name: Tyler L. McIntosh
    affiliation: "2"
    orcid: 0000-0002-6383-1755
  - name: Matthew E. Bitters
    affiliation: "2"
  - name: Carol A. Wessman
    affiliation: "5"
    orcid: 0000-0002-7325-0153
  - name: Jennifer K. Balch
    affiliation: "1, 6"
    orcid: 0000-0002-3983-7970
  - name: Cibele Amaral
    affiliation: "1"
    orcid: 0000-0001-7597-2427
affiliations:
  - index: 1
    name: "Earth Lab and the Environmental Data Science Innovation & Impact Lab (ESIIL), Cooperative Institute for Research in Environmental Sciences (CIRES), University of Colorado Boulder, Boulder, Colorado, USA"
  - index: 2
    name: "Earth Lab, Cooperative Institute for Research in Environmental Sciences (CIRES), University of Colorado Boulder, Boulder, Colorado, USA"
  - index: 3
    name: "Department of Computer Science, University of Colorado Boulder, Boulder, Colorado, USA"
  - index: 4
    name: "Human-Environment Systems, School of the Environment, Boise State University, Boise, Idaho, USA"
  - index: 5
    name: "Department of Ecology and Evolutionary Biology, University of Colorado Boulder, Boulder, Colorado, USA"
  - index: 6
    name: "Department of Geography, University of Colorado Boulder, Boulder, Colorado, USA"
date: 12 October 2026
bibliography: paper.bib
---

# Summary

Reflectance describes how a surface reflects light at different wavelengths. SpectralBridge is Python research software that helps teams prepare and check reflectance products from NEON airborne sensors, drones, and Landsat. It retains named intermediate rasters, extracted values, quality checks, and provenance so users can inspect how each product was made. Separate routes preserve sensor-specific operations, while collection tools summarize selected flightlines and sites. The package organizes established corrections rather than proposing a new algorithm. Tests and team research examples demonstrate software contracts and limitations, not agreement among sensors.

# Statement of need

Band names invite direct comparison, but spectral response, footprint, viewing direction, and illumination help define the reflectance recorded by each instrument. A drone may isolate sunlit foliage; NEON records a dense spectrum; Landsat mixes canopy, gaps, soil, and shadow across broader pixels [@paper_kampe2010; @paper_nationalecologicalobservatorynetwork2026; @paper_woodcock1987]. Matching labels therefore do not make measurements equivalent, and these differences can change an ecological interpretation [@paper_nicodemus1977; @paper_schaepmanstrub2006; @paper_teillet1997; @paper_roy2016; @paper_huang2002]. The intended users are remote-sensing researchers and developers who need to construct sensor-oriented products, inspect intermediate states, verify outputs, or summarize flightlines. They remain responsible for temporal matching, co-registration, and common spatial support. Independent validation also requires characterized reference measurements and uncertainty analysis; process completion alone cannot establish it [@paper_origo2020]. SpectralBridge preserves the sequence from source through configured transformations to extracted values, helping users locate where an unexpected pattern first appears. It does not diagnose discrepancies or choose a valid spatial/temporal design. \autoref{fig:paper1} illustrates the separate roles of spatial support and spectral response.

![Two independent sources of measurement mismatch. (A) The same illustrated vegetation, soil, and shadow are integrated over different pixel footprints; grids are schematic and not to scale. (B) Read from top to bottom: the upper curve is the input reflectance spectrum; the lower curves show how strongly each target band weights each wavelength. They are response functions, not output spectra. Applying a response curve to the input produces one weighted reflectance value, shown schematically by the matching colored output label and defined in Equation 1. The Gaussian profiles use packaged Landsat 8 OLI and MicaSense centers and full widths at half maximum (FWHM), not official measured response curves [@paper_earthlab2026k]; the spectrum is illustrative.](figures/paper-figure-3.png){#fig:paper1}

# State of the field

HyTools is SpectralBridge’s closest methodological relative and part of its NEON lineage. HLS and Sen2Like harmonize satellite products; FORCE processes satellite archives; Snakemake and Nextflow orchestrate general pipelines [@paper_chlus2025; @paper_claverie2018; @paper_ju2025; @paper_saunier2022; @paper_frantz2019; @paper_koster2012; @paper_ditommaso2017]. In the systems compared here, none combines the separate NEON and drone routes with collection-level artifact and QA contracts [@paper_earthlab2026x; @paper_earthlab2026j]. SpectralBridge’s contribution is this sensor-aware integration, restart checks, and grouped summaries - not a new correction method or harmonization product.

# Software design

The workflow addresses geometry normalization and target-band weighting, while preserving geospatial products for downstream spatial reconciliation. It does not create a common spatial support; nominally matching bands may also require bandpass adjustment [@paper_chander2013; @paper_roy2016; @paper_earthlab2026z; @paper_earthlab2026m]. NEON provides the dense spectrum from which configured MicaSense- and Landsat-like products are constructed. Independently acquired drone data follow a separate preparation path [@paper_nationalecologicalobservatorynetwork2026; @paper_earthlab2026z; @paper_earthlab2026h]. Thus, Drone → NEON → Landsat describes a comparison design, not a physical conversion chain. A named target product reflects configured weighting and any recorded adjustment, while retaining NEON’s original spatial support.

## Geometry and terrain

For NEON, the workflow estimates bandwise SCS+C topographic terms, then applies RossThick and LiDenseR BRDF terms using available solar and view geometry [@paper_queally2022; @paper_earthlab2026r; @paper_earthlab2026ab]. These are established methods, with code lineage to HyTools acknowledged in the implementation [@paper_ross1981; @paper_roujean1992; @paper_li1992; @paper_soenen2005; @paper_wanner1995; @paper_schaaf2002; @paper_chlus2025]. Invalid geometry ratios receive neutral factors, which QA should report. Both corrections share one output cube, so their separate effects cannot be isolated from that artifact.

## Spectral response

Different instruments weight different parts of the spectrum, so matching band names do not guarantee matching measurements [@paper_chander2013; @paper_roy2016]. Given source reflectance samples $\rho_i$ and target-band weights $s_{b,i}$ sampled on the same source-band grid, SpectralBridge computes

$$
\hat{\rho}_b = \frac{\sum_i \rho_i s_{b,i}}{\sum_i s_{b,i}}. \tag{1}
$$

The implementation normalizes supplied response weights by their discrete sum; it does not perform wavelength-interval quadrature. Weights must therefore match the source grid and intended spectral support. Actual Landsat weighting requires measured relative spectral responses, not band centers and widths alone [@paper_barsi2014]. A deterministic fixture checks this arithmetic to an absolute tolerance of $2 \times 10^{-7}$ [@paper_earthlab2026s; @paper_earthlab2026ae]. Source atmospheric correction is inherited from NEON; some configured Landsat-like products also receive a separate empirical brightness adjustment [@paper_nationalecologicalobservatorynetwork2026; @paper_earthlab2026l]. These configured representations are not proof of physical agreement with another sensor [@paper_claverie2023; @paper_ju2025].

## Spatial support

Matching band spaces does not make a crown-scale spectrum and a Landsat pixel the same spatial mixture [@paper_teillet1997; @paper_woodcock1987; @paper_huang2002]. SpectralBridge preserves georeferenced rasters and polygon extractions but leaves grid alignment, overlap, and aggregation to the user, because these choices determine which observations contribute [@paper_dungan2002; @paper_earthlab2026m; @paper_earthlab2026h].

## Architecture and data flow

\autoref{fig:paper2} aligns the two observation routes and the shared collection-analysis path. NEON and drone processing share most stages; their main differences are at the edges: drone processing adds local-image staging and may use an affine mapping, while NEON’s dense spectrum supports target-band convolution. Each route writes named artifacts for distinct measurement states, linking the source to corrected and target-band products [@paper_earthlab2026e; @paper_earthlab2026m].

![The NEON and drone routes share most stages and retain similar rasters, tables, and QA/provenance. Drone processing adds local input staging and may apply a configured affine mapping; NEON processing convolves its dense spectrum with target-band responses. The shared collection path streams selected, aligned products into grouped fits and diagnostics. The diagram shows intended workflow structure, not one campaign’s results [@paper_earthlab2026j; @paper_earthlab2026m; @paper_earthlab2026h; @paper_earthlab2026x; @paper_earthlab2026a].](figures/paper-figure-6.png){#fig:paper2}

The architecture evolved from a HyTools-based workflow; HyTools is no longer a runtime dependency, but lineage remains in NEON access, ENVI writing, and correction components [@paper_chlus2025; @paper_earthlab2025a; @paper_earthlab2025b; @paper_earthlab2026i; @paper_earthlab2026t; @paper_earthlab2026r]. The NEON route applies configured geometry corrections and spectral weighting to its source cube. The drone route retains native bands and may apply reviewed affine coefficients, without runtime coefficient fitting or spectral convolution [@paper_earthlab2026e; @paper_earthlab2026m; @paper_earthlab2026h; @paper_earthlab2026c]. Collection analysis streams aligned ENVI windows into pooled, flightline-, and site-level fits. It accumulates compact statistics but still reads source rasters; no performance advantage is claimed without a matched benchmark [@paper_earthlab2026a; @paper_earthlab2026aa; @paper_earthlab2026b]. Named files serve as stage interfaces, not disposable cache. This design lets users inspect intermediate states, check stage-specific QA, and reuse valid products after interruption; it costs storage and I/O, and does not serialize every realized parameter. Restart therefore supports recovery, not guaranteed exact replay. Completion is request-specific: every configured output must exist and be readable [@paper_earthlab2026j; @paper_earthlab2026d; @paper_earthlab2026ad; @paper_earthlab2026u].

![Four questions govern a multi-stage scientific workflow. Normal process termination does not establish production of the requested scientific state; artifact existence does not establish QA; and QA does not establish agreement with independent observations. Remote-sensing validation frameworks likewise treat validation as staged evidence rather than a binary declaration [@paper_morisette2006; @paper_origo2020]. The examples in the Research impact statement illustrate these separate checks [@paper_spectralbridgeprojectteam2026; @paper_earthlab2026p].](figures/paper-figure-7.png){#fig:paper3}

The package is OS-independent, requires Python 3.10 or newer, and is distributed under the GNU General Public License version 3 (GPLv3); installation and usage are documented in its README [@paper_earthlab2026v; @paper_earthlab2026x]. The evidence spans version 2.2.0 at f7e7ddd for the historical NEON route and c86da6a for later bulk work and 2.3.0rc1 preparation, but supplied run records do not link every result to an exact revision [@paper_earthlab2026y; @paper_earthlab2026g]. The public release page listed v1.0.0 at commit 9d1de28 as latest on 12 October 2026; the cited Zenodo DOI is a pre-rename archive, not a record for these results [@paper_earthlab2026w; @paper_earthlab2026f]. The supplementary material distinguishes these historical source and execution records.

## Reuse potential

Reuse is most direct for NEON products and drone observations that match the supported input schemas. Users can configure target-band responses or reviewed affine registries, while preserving exact wavelength definitions and coefficient provenance; adding spatial aggregation or a new sensor remains a study-specific extension. The ENVI, Parquet, and JSON products can then be inspected or consumed by downstream analysis tools [@paper_earthlab2026m; @paper_earthlab2026h; @paper_earthlab2026x].

# Research impact statement

The examples below come from the authors’ ongoing research workflow for comparing NEON, drone, and Landsat reflectance; they are developer-team applications, not evidence of external adoption. Deterministic fixtures cover convolution, correction, extraction, QA, restart, and collection-analysis contracts [@paper_kanewala2014; @paper_earthlab2026ac; @paper_earthlab2026n]. In the R10C NEON example, the declared route produced 18 readable Parquet outputs, while QA retained warnings, including 68 poor-quality wavelength bands that were reported but not masked. This demonstrates artifact completion and warning preservation, not correction efficacy or agreement with Landsat [@paper_earthlab2026p; @paper_earthlab2026q]. A separate 43-flight drone attempt exposes the value of explicit completion checks: orchestration labeled all flights processed, but required ENVI and Parquet outputs were absent [@paper_spectralbridgeprojectteam2026]. A supplied bulk analysis summarizes 122 flightlines, but its executed software revision and run manifest were not provided [@paper_spectralbridgebulkevidencebundle2026; @paper_earthlab2026o]. Together, these cases show how the workflow can expose incomplete production, preserve warnings, and summarize collections while making the limits of the evidence visible. They do not establish independent cross-sensor accuracy, a performance advantage, improved ecological inference, or adoption beyond the developer team.

# AI usage disclosure

The authors report beginning with GPT-3.5 for early consultation and subsequently using all later models available in their workflow. This early history predates the repository's partial prompt log, which records OpenAI Codex and Cursor Agent. Recorded model labels for Codex include GPT-5, GPT-5 family (exact deployment identifier not exposed), and GPT-6. Cursor entries and most historical Codex entries do not identify a model; unrecorded model versions are not inferred [@paper_earthlab_ai_transparency2026].

Logged requests cover software implementation and refactoring, regression and contract tests, pipeline debugging, source and licensing audits, documentation and release preparation, QA visualization, analysis-table checks, and manuscript conversion and citation checks. Requested verification includes automated tests, linting, documentation checks, installed-artifact smoke tests, and inspection of numerical and rendered outputs. The log begins on 21 March 2026, after development was underway, and records user requests rather than accepted outputs or proof that every requested check was completed.

Human team members reviewed proposed software changes, citations, and calculations. AI output was not treated as scientific evidence; the authors retain responsibility for the software, scientific interpretation, and manuscript. [AUTHOR INPUT REQUIRED: confirm that human authors reviewed, edited and validated all AI-assisted outputs and made the core design decisions.]

# Acknowledgements

[AUTHOR INPUT REQUIRED: list financial support and award numbers, describe sponsor involvement, or confirm no financial support.]

Conflicts of interest: [AUTHOR INPUT REQUIRED: provide the authors’ disclosure or confirm that there are no relevant conflicts.]

# References
