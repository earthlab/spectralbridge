---
title: Technical supplement (publication evidence)
hide:
  - toc
search:
  exclude: true
---

# Technical supplement: publication evidence

This is the complete supplementary material supplied with the manuscript revised
12 October 2026, including all sections and appendices, 23 editable tables, two
figures, three equations and 101 references. It retains the source's historical
revision boundaries, incomplete-run records and unresolved scientific questions.
Those observations describe the cited runs and revisions, rather than a live
certification of the current software. Consult the current workflow guides for
operational instructions.

Download the [original 44-page SI PDF](supplement-assets/supplement-10.pdf),
[Markdown source bundle](supplement-assets/supplement-source.zip),
[bibliography](supplement-assets/supplement.bib), or
[Google Docs import copy](supplement-assets/SpectralBridge-SI.docx).
Wrapped PDF table lines remain separate rows where their semantic grouping is
uncertain; the source-page images remain alongside the tables for comparison.

<div class="sb-supplement-content">
<h2>Manuscript identity</h2><p>Supplementary Material for SpectralBridge: An Auditable Software Workflow for Reflectance Comparisons Across NEON, Drones, and Landsat</p><p>Revised 12 October 2026.</p><ul><li>Ty Tuff<sup>1</sup> (corresponding author) · <a href="https://orcid.org/0000-0001-5249-5197">ORCID 0000-0001-5249-5197</a></li><li>Aashish Mukund<sup>1</sup></li><li>Nayani T. Ilangakoon<sup>2</sup> · <a href="https://orcid.org/0000-0002-6607-0605">ORCID 0000-0002-6607-0605</a></li><li>Erick Verleye<sup>2</sup> · <a href="https://orcid.org/0009-0009-8854-0127">ORCID 0009-0009-8854-0127</a></li><li>Megan E. Cattau<sup>4</sup> · <a href="https://orcid.org/0000-0003-2164-3809">ORCID 0000-0003-2164-3809</a></li><li>Janushi Shastri<sup>2, 3</sup></li><li>Pavan Appanna<sup>2, 3</sup></li><li>Tyler L. McIntosh<sup>2</sup> · <a href="https://orcid.org/0000-0002-6383-1755">ORCID 0000-0002-6383-1755</a></li><li>Matthew E. Bitters<sup>2</sup></li><li>Carol A. Wessman<sup>5</sup> · <a href="https://orcid.org/0000-0002-7325-0153">ORCID 0000-0002-7325-0153</a></li><li>Jennifer K. Balch<sup>1, 6</sup> · <a href="https://orcid.org/0000-0002-3983-7970">ORCID 0000-0002-3983-7970</a></li><li>Cibele Amaral<sup>1</sup> · <a href="https://orcid.org/0000-0001-7597-2427">ORCID 0000-0001-7597-2427</a></li></ul><ol><li value="1">Earth Lab and the Environmental Data Science Innovation &amp; Impact Lab (ESIIL), Cooperative Institute for Research in Environmental Sciences (CIRES), University of Colorado Boulder, Boulder, Colorado, USA</li><li value="2">Earth Lab, Cooperative Institute for Research in Environmental Sciences (CIRES), University of Colorado Boulder, Boulder, Colorado, USA</li><li value="3">Department of Computer Science, University of Colorado Boulder, Boulder, Colorado, USA</li><li value="4">Human-Environment Systems, School of the Environment, Boise State University, Boise, Idaho, USA</li><li value="5">Department of Ecology and Evolutionary Biology, University of Colorado Boulder, Boulder, Colorado, USA</li><li value="6">Department of Geography, University of Colorado Boulder, Boulder, Colorado, USA</li></ol><p>Correspondence: <a href="mailto:ty.tuff@colorado.edu">ty.tuff@colorado.edu</a></p><!-- SI source SHA256: a1227e1b60838d2523b1cf040914e80cf9b155bd9d5074e70dfd8a4fa34e3e16 -->
<nav id="TOC" role="doc-toc">
<ul>
<li><a href="#purpose-and-relationship-to-the-main-text"
id="toc-purpose-and-relationship-to-the-main-text">Purpose and
relationship to the main text</a></li>
<li><a href="#software-scope-and-supported-paths"
id="toc-software-scope-and-supported-paths">Software scope and supported
paths</a></li>
<li><a href="#flightline-processing-contracts"
id="toc-flightline-processing-contracts">Flightline processing
contracts</a>
<ul>
<li><a href="#canonical-neon-stage-sequence"
id="toc-canonical-neon-stage-sequence">Canonical NEON stage
sequence</a></li>
<li><a href="#optional-across-track-half-flight-processing"
id="toc-optional-across-track-half-flight-processing">Optional
across-track half-flight processing</a></li>
</ul></li>
<li><a href="#scientific-transformations"
id="toc-scientific-transformations">Scientific transformations</a>
<ul>
<li><a href="#configured-target-band-weighting"
id="toc-configured-target-band-weighting">Configured target-band
weighting</a></li>
<li><a href="#topographic-and-brdf-normalization"
id="toc-topographic-and-brdf-normalization">Topographic and BRDF
normalization</a></li>
<li><a href="#spatial-support" id="toc-spatial-support">Spatial
support</a></li>
</ul></li>
<li><a href="#drone-processing-pipeline"
id="toc-drone-processing-pipeline">Drone processing pipeline</a></li>
<li><a href="#file-contracts-provenance-and-restart-behavior"
id="toc-file-contracts-provenance-and-restart-behavior">File contracts,
provenance, and restart behavior</a></li>
<li><a href="#multi-flightline-bulk-analysis"
id="toc-multi-flightline-bulk-analysis">Multi-flightline bulk
analysis</a>
<ul>
<li><a href="#additional-spectral-library-reporting-route"
id="toc-additional-spectral-library-reporting-route">Additional
spectral-library reporting route</a></li>
</ul></li>
<li><a href="#quality-assurance-model"
id="toc-quality-assurance-model">Quality-assurance model</a>
<ul>
<li><a href="#validation-tiers-and-installed-artifact-checks"
id="toc-validation-tiers-and-installed-artifact-checks">Validation tiers
and installed-artifact checks</a></li>
</ul></li>
<li><a href="#first-production-drone-campaign-attempt"
id="toc-first-production-drone-campaign-attempt">First production drone
campaign attempt</a></li>
<li><a href="#r10c-real-flightline-demonstration"
id="toc-r10c-real-flightline-demonstration">R10C real-flightline
demonstration</a></li>
<li><a href="#wref-visual-qa-example"
id="toc-wref-visual-qa-example">WREF visual QA example</a></li>
<li><a href="#bulk-analysis-collection-and-variable-definitions"
id="toc-bulk-analysis-collection-and-variable-definitions">Bulk
analysis: collection and variable definitions</a>
<ul>
<li><a href="#collection-accounting-and-acquisition-coverage"
id="toc-collection-accounting-and-acquisition-coverage">Collection
accounting and acquisition coverage</a></li>
<li><a href="#what-exactly-is-compared"
id="toc-what-exactly-is-compared">What exactly is compared?</a></li>
<li><a href="#numerical-summaries-and-their-estimands"
id="toc-numerical-summaries-and-their-estimands">Numerical summaries and
their estimands</a></li>
<li><a href="#reference-displacement-is-not-prediction-error"
id="toc-reference-displacement-is-not-prediction-error">Reference
displacement is not prediction error</a></li>
<li><a href="#executable-audit-and-file-provenance"
id="toc-executable-audit-and-file-provenance">Executable audit and file
provenance</a></li>
</ul></li>
<li><a href="#what-remains-to-be-established"
id="toc-what-remains-to-be-established">What remains to be
established</a></li>
<li><a href="#claims-and-their-boundaries"
id="toc-claims-and-their-boundaries">Claims and their
boundaries</a></li>
<li><a href="#reproducibility-checklist"
id="toc-reproducibility-checklist">Reproducibility checklist</a></li>
<li><a href="#figure-and-table-provenance"
id="toc-figure-and-table-provenance">Figure and table
provenance</a></li>
<li><a href="#a-software-lineage-and-implementation-provenance"
id="toc-a-software-lineage-and-implementation-provenance">A Software
lineage and implementation provenance</a>
<ul>
<li><a href="#a.1-evidence-and-revision-boundary"
id="toc-a.1-evidence-and-revision-boundary">A.1 Evidence and revision
boundary</a></li>
<li><a href="#a.2-component-level-provenance"
id="toc-a.2-component-level-provenance">A.2 Component-level
provenance</a></li>
<li><a href="#a.3-historical-source-packaging-and-licensing"
id="toc-a.3-historical-source-packaging-and-licensing">A.3 Historical
source, packaging, and licensing</a></li>
<li><a href="#a.4-spectralbridge-contribution-boundary"
id="toc-a.4-spectralbridge-contribution-boundary">A.4 SpectralBridge
contribution boundary</a></li>
</ul></li>
<li><a href="#b-relationship-to-neighboring-software"
id="toc-b-relationship-to-neighboring-software">B Relationship to
neighboring software</a></li>
<li><a href="#c-prospective-qa-and-resource-protocol"
id="toc-c-prospective-qa-and-resource-protocol">C Prospective QA and
resource protocol</a>
<ul>
<li><a href="#c.1-resource-use-analysis"
id="toc-c.1-resource-use-analysis">C.1 Resource-use analysis</a></li>
</ul></li>
<li><a href="#references" id="toc-references">References</a></li>
</ul>
</nav>
<h1 id="purpose-and-relationship-to-the-main-text">Purpose and
relationship to the main text</h1>
<p>The main paper argues that comparable reflectance has to be
constructed and that researchers should be able to examine how that
construction was made. This supplement provides the detail needed to
assess that claim: processing contracts and transformations, the
intended drone artifact sequence, the first 43-flight production
attempt, the streaming bulk workflow inspected in September 2026,
historical QA records, and the supplied 122-flightline analysis.
Development history, neighboring- software comparisons, and the
prospective QA and resource protocol are included here so that the main
paper can stay focused on the scientific problem. The organization
follows the questions a reader is likely to ask. What is the software
intended to produce? Which numerical transformations does it apply? How
are completion and QA judged? What happened in controlled tests and
real-data runs? Which conclusions can be drawn from the collection
analysis, and what remains to be tested? Detailed provenance and future
protocols follow the results they qualify. The historical NEON and
intended drone descriptions retain the 4 September audit at f7e7ddd; the
bulk and release-preparation update refers to c86da6a, inspected 9
September <span class="citation"
data-cites="si_earthlab2026ak si_earthlab2026l">(Earth Lab 2026ak,
2026l)</span>. R10C was generated at d88e8d0 and archived at f7e7ddd.
The supplied bulk results have a separate analysis run identifier, not
yet linked to an executed source revision by a matching manifest. The
exact revision and resolved configuration used for the 43-flight drone
production attempt were not included in its supplied inventory, and no
corrective revision is assigned here <span class="citation"
data-cites="si_spectralbridgeprojectteam2026">(SpectralBridge project
team 2026)</span>. Source inspection, historical execution, production
inventory, and this revision’s reanalysis of exported bulk tables are
kept distinct. The software-lineage section uses the same revision
boundaries. It draws on explicit notices in pinned source files, cited
repository history, and the later repository audit summarized for this
revision. No standalone HYTOOLS_PROVENANCE.md or provenance manifest was
supplied with the manuscript workspace. We therefore do not describe the
later attribution work as documentation that existed in historical
releases. Where file-level evidence is incomplete, the tables say so
rather than declaring independence. Four terms keep the claims
consistent. Implemented means that behavior is present in source code.
Tested means that a controlled fixture exercises a defined contract.
Demonstrated refers to artifacts and behavior recorded in a real-data
run. Scientifically validated requires independent observations or a
justified external reference. Thus, the drone campaign demonstrates
discovery, staging, and persistence of intermediate products, but not
completion of the full drone route.</p>
<h1 id="software-scope-and-supported-paths">Software scope and supported
paths</h1>
<p>SpectralBridge has two observation-level paths and one
collection-level path. NEON processing produces source-product and
geometry-normalized hyperspectral representations, configured target-
band products, analysis tables, and QA. Drone processing ingests
supported local observations while preserving their identity, correction
availability, and provenance <span class="citation"
data-cites="si_earthlab2026am si_earthlab2026m">(Earth Lab 2026am,
2026m)</span>. The bulk path then catalogs eligible target products and
reads aligned ENVI windows; merged Parquet remains available for
compatibility. Bulk analysis starts from completed products and does not
rerun geometry normalization or target-band weighting <span
class="citation" data-cites="si_earthlab2026a">(Earth Lab 2026a)</span>.
The project-level relationship Drone → NEON → Landsat is conceptual.
NEON supplies a dense reference spectrum from which configured
MicaSense- and Landsat-like band representations can be constructed. The
package does not implement a direct, universal drone-to-Landsat
conversion, and target-band weighting does not alter spatial support
<span class="citation"
data-cites="si_nationalecologicalobservatorynetwork2026 si_earthlab2026am si_earthlab2026s">(National
Ecological Observatory Network 2026; Earth Lab 2026am, 2026s)</span>.
Each observing system brings a different strength. Imaging spectroscopy
preserves contiguous spectral information <span class="citation"
data-cites="si_goetz1985">(Goetz et al. 1985)</span>; the NEON Airborne
Observation Platform applies it to repeatable ecological observation
<span class="citation" data-cites="si_kampe2010">(Kampe et al.
2010)</span>; Landsat provides a long calibrated record at moderate
resolution <span class="citation" data-cites="si_wulder2022">(Wulder et
al. 2022)</span>; and compact UAV instruments provide flexible,
very-high-resolution sampling while demanding careful measurement design
and calibration <span class="citation"
data-cites="si_aasen2018 si_mamaghani2019">(Aasen et al. 2018; Mamaghani
and Salvaggio 2019)</span>. SpectralBridge addresses the spectral and
workflow parts of relating these systems, not the entire comparison
problem.</p>
<h1 id="flightline-processing-contracts">Flightline processing
contracts</h1>
<h2 id="canonical-neon-stage-sequence">Canonical NEON stage
sequence</h2>
<p>Table 1: Canonical NEON processing stages and their scientific
interpretation <span class="citation"
data-cites="si_earthlab2026i si_earthlab2026e si_earthlab2026s">(Earth
Lab 2026i, 2026e, 2026s)</span>.</p>
<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr>
<th>Stage</th>
<th>Principal input</th>
<th>Principal output</th>
<th>Scientific purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td>Source acquisition</td>
<td>Flightline identifier and</td>
<td>Source HDF5</td>
<td>Preserve the acquired</td>
</tr>
<tr>
<td></td>
<td>NEON product request</td>
<td></td>
<td>observation and identity.</td>
</tr>
<tr>
<td>Source-product</td>
<td>NEON HDF5</td>
<td>ENVI image and header</td>
<td>Expose reflectance and map</td>
</tr>
<tr>
<td>export</td>
<td></td>
<td></td>
<td>information in a standard</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>raster representation without</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>implying unprocessed sensor</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>data.</td>
</tr>
<tr>
<td>Parameterization</td>
<td>Reflectance and</td>
<td>JSON model reference and</td>
<td>Record the retained BRDF</td>
</tr>
<tr>
<td></td>
<td>ancillary geometry</td>
<td>geometry summaries</td>
<td>and geometry information;</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>scene SCS+C terms are not</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>persisted.</td>
</tr>
<tr>
<td>Correction</td>
<td>Source-product ENVI</td>
<td>Combined topographic-</td>
<td>Normalize modeled terrain and</td>
</tr>
<tr>
<td></td>
<td>and geometry/model</td>
<td>and-BRDF-corrected</td>
<td>directional effects.</td>
</tr>
<tr>
<td></td>
<td>information</td>
<td>ENVI</td>
<td></td>
</tr>
<tr>
<td>Configured</td>
<td>Geometry-normalized</td>
<td>Target-band</td>
<td>Apply target-band weights and</td>
</tr>
<tr>
<td>target-band</td>
<td>hyperspectral cube and</td>
<td>representations of NEON</td>
<td>any separately recorded</td>
</tr>
<tr>
<td>weighting</td>
<td>configured weight</td>
<td>pixels</td>
<td>brightness adjustment without</td>
</tr>
<tr>
<td></td>
<td>arrays</td>
<td></td>
<td>changing spatial support.</td>
</tr>
<tr>
<td>Tabulation</td>
<td>ENVI products</td>
<td>Per-product Parquet files</td>
<td>Make pixel-level values and</td>
</tr>
<tr>
<td></td>
<td></td>
<td>and merged flightline table</td>
<td>metadata available to</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>statistical workflows.</td>
</tr>
<tr>
<td>Quality assurance</td>
<td>Stage artifacts and</td>
<td>JSON, metrics, HTML,</td>
<td>Record evaluated rules,</td>
</tr>
<tr>
<td></td>
<td>configured checks</td>
<td>visual panels, and optional</td>
<td>warnings, failures, and</td>
</tr>
<tr>
<td></td>
<td></td>
<td>combined PDF</td>
<td>unevaluated questions.</td>
</tr>
</tbody>
</table>
<p>Canonical paths and per-flightline directories isolate products
during parallel runs and provide stable locations for restart checks
<span class="citation"
data-cites="si_earthlab2026i si_earthlab2026e si_earthlab2026s">(Earth
Lab 2026i, 2026e, 2026s)</span>. The command- line interface and worked
invocation are maintained in the versioned project documentation; worker
count and storage configuration are execution choices rather than
scientific defaults.</p>
<h2 id="optional-across-track-half-flight-processing">Optional
across-track half-flight processing</h2>
<p>Full-flightline processing remains the default. When split across
track=True, SpectralBridge downloads or reuses one source HDF5 file,
divides the across-track columns into left and right windows, and writes
each window to a separately suffixed product tree. If the sample count
is odd, the right window receives the additional column. The two windows
share source identity but are independent pipeline units for output
paths, QA, and restart <span class="citation"
data-cites="si_earthlab2026o si_earthlab2026i">(Earth Lab 2026o,
2026i)</span>. This mode changes more than memory layout. Topographic
and BRDF estimation for each run sees only the pixels in that window, so
half-flight products are not assumed to be numerically identical to the
corresponding subset of a full-flightline result. Bulk-run records must
therefore distinguish</p>
<figure>
<img src="../supplement-assets/si-table-page-3.png"
alt="Source page 3 for table layout verification" />
<figcaption aria-hidden="true">Source page 3 for table layout
verification</figcaption>
</figure>
<p>full, left-half, and right-half processing. The mode provides an
operational option for large inputs, but its effect on peak memory, run
time, correction estimates, and seam behavior must be measured rather
than inferred <span class="citation"
data-cites="si_earthlab2026o si_earthlab2026ao">(Earth Lab 2026o,
2026ao)</span>.</p>
<h1 id="scientific-transformations">Scientific transformations</h1>
<h2 id="configured-target-band-weighting">Configured target-band
weighting</h2>
<p>Nominally similar bands can have different relative spectral
responses and therefore produce different reflectance values over the
same target <span class="citation"
data-cites="si_chander2013 si_roy2016 si_claverie2023">(Chander et al.
2013; Roy et al. 2016; Claverie 2023)</span>. SpectralBridge addresses
this spectral part of the comparison by applying sampled target-band
weights to the NEON spectrum. The result is a configured target-band
representation of the NEON observation, not an independently observed
target-sensor measurement. Some source code and historical QA records
call this stage spectral convolution; the manuscript uses target-band
weighting when discussing its scientific meaning. For reflectance
samples ρi and response weights sb,i already sampled on the same
source-band grid, the implemented target-band quantity is</p>
<p><math display="block" xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mover><mi>ρ</mi><mo accent="true">̂</mo></mover><mi>b</mi></msub><mo>=</mo><mfrac><mrow><munder><mo>∑</mo><mi>i</mi></munder><msub><mi>ρ</mi><mi>i</mi></msub><msub><mi>s</mi><mrow><mi>b</mi><mo>,</mo><mi>i</mi></mrow></msub></mrow><mrow><munder><mo>∑</mo><mi>i</mi></munder><msub><mi>s</mi><mrow><mi>b</mi><mo>,</mo><mi>i</mi></mrow></msub></mrow></mfrac><mi>.</mi></mrow><annotation encoding="application/x-tex">
\hat{\rho}_b = \frac{\sum_i \rho_i s_{b,i}}{\sum_i s_{b,i}}. \label{eq:weighting}
</annotation></semantics></math></p>
<p>The implementation normalizes each response by its discrete sum and
applies a floating-point matrix product <span class="citation"
data-cites="si_earthlab2026aa">(Earth Lab 2026aa)</span>. The wavelength
vector is checked for dimensional alignment but is not used for
wavelength-interval quadrature. The routine therefore assumes that the
supplied sampled weights already encode the intended wavelength sampling
and does not independently establish their units, ordering, spacing,
provenance, or spectral overlap. Configured outputs include
representations labeled for Landsat 5 TM, Landsat 7 ETM+, Landsat 8 OLI,
Landsat 9 OLI-2, and MicaSense, together with downstream affine
coefficient sets for selected MicaSense-like and Landsat-like variables.
Packaged center and full-width-at-half-maximum values are stored in the
repository’s sensor-parameter JSON <span class="citation"
data-cites="si_earthlab2026q">(Earth Lab 2026q)</span>. These parameters
can define Gaussian approximations but are not themselves measured
relative spectral response curves; the Landsat 8 Operational Land
Imager, for example, has measured bandwise relative spectral responses
that determine its actual wavelength weighting <span class="citation"
data-cites="si_barsi2014">(Barsi et al. 2014)</span>. More generally,
quantitative UAV multispectral use depends on documented geometric and
radiometric calibration, and camera-specific characterization can reveal
departures from factory assumptions <span class="citation"
data-cites="si_aasen2018 si_mamaghani2019 si_cao2019">(Aasen et al.
2018; Mamaghani and Salvaggio 2019; Cao et al. 2019)</span>. Some
configured Landsat-like products receive an empirical percentage
adjustment after Equation 1. The inspected coefficient files describe
adjustments derived from Table Mountain HLS median differences and warn
that their band indices are wavelength-aligned rather than
interchangeable with native sensor numbering <span class="citation"
data-cites="si_earthlab2026r">(Earth Lab 2026r)</span>. Product headers
and QA artifacts record whether the adjustment was applied, but the
purely weighted representation is not always retained as a separate
canonical raster. Target-band weighting and brightness adjustment are
therefore distinct measurement states even where the artifact chain
combines them, and transferability of the adjustment beyond its
derivation context has not been established. Evaluations of bandpass-
adjustment techniques show that simple linear, spectral-library,
adaptive, and nonlinear methods have different data requirements and
performance; no one fitted form is a complete definition of sensor
harmonization <span class="citation"
data-cites="si_claverie2023">(Claverie 2023)</span>. HLS version 2.0
further demonstrates that operational harmonization combines atmospheric
correction, cloud and shadow handling, directional normalization,
bandpass adjustment, and common gridding <span class="citation"
data-cites="si_ju2025">(Ju et al. 2025)</span>. Five controlled
source/target band-count variations agreed with an independently
implemented normalized-weight calculation to an absolute tolerance of 2
× 10−7 <span class="citation" data-cites="si_earthlab2026ar">(Earth Lab
2026ar)</span>. This tests the arithmetic contract. It does not validate
weight provenance, usable spectral support, or agreement with measured
satellite observations. Declared poor-quality source bands are retained
visibly in the R10C evidence, but the archived reports do not establish
whether they received nonzero weight in each target band <span
class="citation" data-cites="si_earthlab2026w si_earthlab2026y">(Earth
Lab 2026w, 2026y)</span>. Before scientific interpretation, the planned
study must report usable source-wavelength coverage for every
target-band representation, identify overlap with declared poor-quality
bands, and define the status assigned when usable support falls below
the recorded thresholds. Until then, an arithmetic pass for spectral
weighting should not be read as evidence that every target band has
adequate scientific support.</p>
<h2 id="topographic-and-brdf-normalization">Topographic and BRDF
normalization</h2>
<p>SpectralBridge applies sun-canopy-sensor plus C (SCS+C) topographic
normalization followed by kernel-driven bidirectional reflectance
distribution function (BRDF) normalization. SCS+C is attributed to its
forest topographic-correction source <span class="citation"
data-cites="si_soenen2005">(Soenen, Peddle, and Coburn 2005)</span>;
RossThick and LiDenseR belong to volume- and geometric-scattering model
lineages developed and operationalized across several studies <span
class="citation"
data-cites="si_ross1981 si_roujean1992 si_li1992 si_wanner1995 si_schaaf2002">(Ross
1981; Roujean, Leroy, and Deschamps 1992; Li and Strahler 1992; Wanner,
Li, and Strahler 1995; Schaaf et al. 2002)</span>. The source
implementation has a separate provenance: calc cosine i, calc volume
kernel, and calc geom kernel, together with portions of the surrounding
correction module, explicitly identify adaptation from the
GPLv3-licensed HyTools project <span class="citation"
data-cites="si_chlus2025 si_earthlab2026z">(Chlus et al. 2025; Earth Lab
2026z)</span>. In the default mode, one SCS+C term per band is estimated
from pixels passing the source no-data and finite-value masks, using
streamed sufficient statistics across the flightline. Correction is
applied in full-width row strips. Scene-level BRDF coefficients are then
applied using those kernels, scene-mean solar zenith, local view
geometry, and a conventional normalization target of 45-degree solar
zenith, nadir view, and zero relative azimuth; this is not the actual
acquisition geometry of Landsat or NEON <span class="citation"
data-cites="si_queally2022 si_earthlab2026ao">(Queally et al. 2022;
Earth Lab 2026ao)</span>. Non-finite or unsuitable correction ratios are
replaced by neutral factors rather than allowed to create extreme values
<span class="citation" data-cites="si_earthlab2026z">(Earth Lab
2026z)</span>. The fraction of pixels and bands receiving neutral
fallbacks should be retained as a QA diagnostic because numerical
stability does not imply that a correction was applied. An optional
tiled mode fits independent topographic terms in non-overlapping 100 ×
100-pixel tiles. This reduces fitting scope but creates a specific QA
question: whether grid-aligned seams appear in the normalized product.
The canonical normalized cube combines topographic and BRDF operations.
Separate topographic-only and BRDF-only cubes are not retained, so
attribution of their individual effects requires additional runs or
outputs <span class="citation"
data-cites="si_earthlab2026ao si_earthlab2026s">(Earth Lab 2026ao,
2026s)</span>. These empirical and semi-empirical models alter observed
relationships with terrain and acquisition geometry. Independent
reference observations are needed to determine whether the resulting
reflectance is more accurate for a particular scientific use, especially
when vegetation composition covaries with slope or aspect <span
class="citation" data-cites="si_soenen2005 si_queally2022">(Soenen,
Peddle, and Coburn 2005; Queally et al. 2022)</span>.</p>
<h2 id="spatial-support">Spatial support</h2>
<p>Spectral weighting changes band space, not pixel footprint. A
target-band representation of a NEON pixel and an actual Landsat
footprint remain different mixtures even when they use similar band
labels; a sensor’s point-spread function can also extend the
contributing area beyond a nominal pixel boundary <span class="citation"
data-cites="si_teillet1997 si_woodcock1987 si_huang2002">(Teillet 1997;
Woodcock and Strahler 1987; Huang et al. 2002)</span>. Spatial
comparison must distinguish grain, support, extent, and the scale of the
ecological process <span class="citation"
data-cites="si_dungan2002">(Dungan et al. 2002)</span>. SpectralBridge
retains geospatial rasters and polygon-extraction products so users can
define co-registration and aggregation explicitly <span class="citation"
data-cites="si_earthlab2026s si_earthlab2026m">(Earth Lab 2026s,
2026m)</span>. The aggregation rule determines which fine-resolution
observations contribute, how incomplete overlap is handled, and whether
the resulting quantity represents area, cover, or another ecological
target.</p>
<h1 id="drone-processing-pipeline">Drone processing pipeline</h1>
<p>The drone pipeline is intended to prepare the independently acquired
fine-resolution side of the comparison. It recursively discovers local
HDF5 inputs and supports configured local TIFF inputs, preserves
provenance from original filenames, and stages a working HDF5
representation. The intended downstream sequence is working HDF5,
native-drone ENVI representation, geometry normalization where
supported, geometry-normalized native-drone representation, optional
applica- tion of reviewed affine relationships to construct configured
Landsat-like variables, full-image or polygon extraction, Parquet, and
QA <span class="citation"
data-cites="si_earthlab2026m si_earthlab2026aj">(Earth Lab 2026m,
2026aj)</span>. This use case follows a broader ecological need to
connect reproducible UAS observations with NEON’s continental sampling
framework <span class="citation" data-cites="si_koontz2022">(Koontz et
al. 2022)</span>. Topographic and BRDF normalization require the
corresponding terrain, view, and solar geometry. Radiometric panel
methods, empirical-line calibration, camera characterization, and
downwelling- sensor geometry can each influence retrieved UAV
reflectance and must be recorded as part of the measurement definition
<span class="citation"
data-cites="si_wang2015 si_cao2019 si_schneiderzapp2019 si_origo2025">(Wang
and Myint 2015; Cao et al. 2019; Schneider-Zapp et al. 2019; Origo et
al. 2025)</span>. The intended QA record distinguishes a correction that
ran from one that was skipped because geometry was unavailable or that
used a fallback after a quality check. Users can request all available
pixels or restrict extraction to intersecting polygons. Each discovered
flight receives a separate output directory with drone-native identity.
Which artifacts are required depends on the resolved configuration;
completion must therefore be evaluated against that configuration rather
than against a universal list or process return code. The optional
affine relationships require especially careful language. The documented
post- normalization equation is</p>
<p><math display="block" xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>L</mi><mo>=</mo><mi>a</mi><mo>+</mo><mi>b</mi><mi>M</mi><mi>.</mi></mrow><annotation encoding="application/x-tex">
L = a + bM. \label{eq:si-affine}
</annotation></semantics></math></p>
<p>where M is a corrected native-drone variable and L is a configured
Landsat-like variable. The release-candidate documentation specifies
wavelength-aware source-to-target mapping, a versioned reviewed
coefficient registry, and a fixed production policy using the
site-balanced relationship. The drone route neither estimates these
coefficients at runtime nor performs spectral convolution; convolution
remains part of the NEON hyperspectral path. If an approved production
registry is unavailable, the documented default is to stop with an
actionable error rather than derive a registry from summary statistics
<span class="citation" data-cites="si_earthlab2026aj">(Earth Lab
2026aj)</span>. The registered relationships were derived from
same-source synthetic NEON representations. Ap-</p>
<p>plying Equation 2 is not empirical calibration against independent
Landsat observations and does not create Landsat spatial support. No
configured Landsat-like variables are inferred from the 43-flight
production attempt because the expected downstream raster and tabular
products were absent <span class="citation"
data-cites="si_earthlab2026d si_spectralbridgeprojectteam2026">(Earth
Lab 2026d; SpectralBridge project team 2026)</span>. Optional external
QA can search for an overlapping Landsat Collection 2 Level 2 scene, use
a supplied analysis-ready raster, or reuse a cached observation
manifest. The documented comparison places products on a common Landsat
grid and can include a pre-existing NEON-convolved product. Reproducible
use therefore requires the Landsat product identifier, acquisition time,
masks, scale and offset, grid and resampling rules, overlap definition,
and local cache or query record <span class="citation"
data-cites="si_usgeologicalsurvey2026">(U.S. Geological Survey
2026)</span>. This capability is not evidence that such a comparison ran
for the 43-flight campaign or that agreement was scientifically
validated. Surface-reflectance validation requires independent, fully
characterized reference measurements with uncertainty and traceability,
together with spatial and temporal matching rules <span class="citation"
data-cites="si_origo2020 si_origo2025">(Origo et al. 2020, 2025)</span>.
Table 2 states the configuration-dependent completion contract used to
interpret a future campaign replay. It is the manuscript’s scientific
acceptance protocol, not a claim that the production orchestrator
already enforces every gate. A stage marked as not requested or
unsupported must carry an explicit recorded disposition; silently
omitting it is not equivalent to satisfying it. The drone and NEON
pipelines therefore meet scientifically rather than through a hidden
conversion. The intended drone path preserves and prepares the observed
high-resolution measurement; the NEON path constructs MicaSense- and
Landsat-like band representations; and the researcher must still define
temporal matching, geometric overlap, spatial aggregation, and the
ecological sampling unit. The first real campaign does not yet provide
completed products for that comparison.</p>
<p>Table 2: Configuration-dependent artifact contract for the drone
route. A flight is complete only when every artifact required by its
resolved configuration satisfies the stated evidence check.</p>
<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr>
<th>State</th>
<th>Required when</th>
<th>Minimum completion evidence</th>
<th>Non-completing disposition</th>
</tr>
</thead>
<tbody>
<tr>
<td>Working HDF5</td>
<td>A discovered observation</td>
<td>File opens; required observation arrays</td>
<td>Missing, unreadable,</td>
</tr>
<tr>
<td></td>
<td>is staged</td>
<td>and source identity are readable;</td>
<td>or identity</td>
</tr>
<tr>
<td></td>
<td></td>
<td>provenance points to the original local</td>
<td>mismatch.</td>
</tr>
<tr>
<td></td>
<td></td>
<td>input.</td>
<td></td>
</tr>
<tr>
<td>Native ENVI</td>
<td>Raster representation is</td>
<td>Header/image pair opens together;</td>
<td>Missing member of</td>
</tr>
<tr>
<td>representation</td>
<td>requested or is a</td>
<td>dimensions, bands, coordinate reference</td>
<td>the pair, unreadable</td>
</tr>
<tr>
<td></td>
<td>prerequisite of a</td>
<td>information, and no-data metadata pass</td>
<td>data, or inconsistent</td>
</tr>
<tr>
<td></td>
<td>requested downstream</td>
<td>structural checks.</td>
<td>dimensions.</td>
</tr>
<tr>
<td></td>
<td>stage</td>
<td></td>
<td></td>
</tr>
<tr>
<td>Geometry-</td>
<td>Geometry normalization</td>
<td>Output raster opens; the correction</td>
<td>Unrecorded</td>
</tr>
<tr>
<td>normalized</td>
<td>is requested and</td>
<td>record identifies whether normalization</td>
<td>omission. An</td>
</tr>
<tr>
<td>native-drone</td>
<td>supported by available</td>
<td>ran, its inputs, and any fallback</td>
<td>explicit unsupported</td>
</tr>
<tr>
<td>representation</td>
<td>ancillary data</td>
<td>fractions.</td>
<td>or skipped status</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>may be valid for a</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>configuration that</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>does not require</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>normalized output,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>but is not evidence</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>of normalization.</td>
</tr>
<tr>
<td>Configured</td>
<td>Application of a reviewed</td>
<td>Output opens; registry version,</td>
<td>Missing output or</td>
</tr>
<tr>
<td>Landsat-like</td>
<td>affine relationship is</td>
<td>coefficient and estimator identifiers,</td>
<td>registry evidence; a</td>
</tr>
<tr>
<td>representation</td>
<td>requested</td>
<td>wavelength mapping, source and target</td>
<td>native-drone</td>
</tr>
<tr>
<td></td>
<td></td>
<td>variables, a and b, order of application,</td>
<td>product does not</td>
</tr>
<tr>
<td></td>
<td></td>
<td>and units or stored-value scale are</td>
<td>substitute for this</td>
</tr>
<tr>
<td></td>
<td></td>
<td>recorded.</td>
<td>state.</td>
</tr>
<tr>
<td>Extracted Parquet</td>
<td>Full-image or polygon</td>
<td>File and schema are readable; flight</td>
<td>Missing or</td>
</tr>
<tr>
<td></td>
<td>extraction is requested</td>
<td>identity, variables, row count, extraction</td>
<td>unreadable table, or</td>
</tr>
<tr>
<td></td>
<td></td>
<td>mode, and polygon identity where</td>
<td>an unexplained</td>
</tr>
<tr>
<td></td>
<td></td>
<td>applicable are recorded. A zero-row</td>
<td>zero-row result.</td>
</tr>
<tr>
<td></td>
<td></td>
<td>polygon result requires an explicit</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>overlap disposition.</td>
<td></td>
</tr>
<tr>
<td>QA evidence</td>
<td>A stage or complete flight</td>
<td>Stage JSON parses; evaluated rules</td>
<td>A QA rendering</td>
</tr>
<tr>
<td></td>
<td>is evaluated</td>
<td>identify their artifact; a combined report</td>
<td>alone cannot</td>
</tr>
<tr>
<td></td>
<td></td>
<td>preserves pass, warning, failure, and</td>
<td>substitute for a</td>
</tr>
<tr>
<td></td>
<td></td>
<td>not-evaluated states.</td>
<td>missing scientific</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>product.</td>
</tr>
</tbody>
</table>
<figure>
<img src="../supplement-assets/si-table-page-8.png"
alt="Source page 8 for table layout verification" />
<figcaption aria-hidden="true">Source page 8 for table layout
verification</figcaption>
</figure>
<h1 id="file-contracts-provenance-and-restart-behavior">File contracts,
provenance, and restart behavior</h1>
<p>The phrase “outputs are the API” means that stages communicate
through named files, not only through values held in memory <span
class="citation" data-cites="si_earthlab2026p">(Earth Lab 2026p)</span>.
Those files preserve the scientific sequence: source observation,
working or source-product representation, geometry/model summary,
geometry- normalized representation, configured target-band
representation, extracted table, and QA record. The resolved
configuration determines which of them are required. This design is
consistent with FAIR workflow and research-object practices that package
data, software, parameters, provenance, and results as one inspectable
record <span class="citation"
data-cites="si_goble2020 si_soilandreyes2022">(Goble et al. 2020;
Soiland-Reyes et al. 2022)</span>. This design helps localize a problem,
although it does not diagnose the cause automatically. A source-product
cube can show whether an unexpected pattern was already present; the
geometry- normalized cube can show whether it appeared during
normalization; the target-band product can reveal a change during band
construction; and the Parquet output can reveal a change during
extraction or merging. Some boundaries remain coarse: topographic and
BRDF effects share one cube, and weighting and brightness adjustment can
share one target-product stage. The files can therefore identify the
stage at which a pattern appeared without always isolating the operation
within that stage <span class="citation"
data-cites="si_earthlab2026p si_earthlab2026i si_earthlab2026s">(Earth
Lab 2026p, 2026i, 2026s)</span>. On rerun, a stage can reuse artifacts
that pass its format checks and reconstruct outputs that are absent or
rejected <span class="citation"
data-cites="si_earthlab2026f si_earthlab2026aq">(Earth Lab 2026f,
2026aq)</span>. JSON must parse, ENVI image/header pairs must pass
internal readability checks, and Parquet outputs receive schema-read
checks. QA reuse is stricter: the public contract requires matching
schema, parameters, thresholds, software version, and input/output
fingerprints <span class="citation"
data-cites="si_earthlab2026af">(Earth Lab 2026af)</span>. Format checks,
QA reuse, and completion are therefore separate decisions. Reproducible
reuse requires retaining or recording:</p>
<p>• the full software commit and installed package versions; • the
command and resolved configuration; • source identifiers and, where
possible, checksums; • packaged response-definition versions or exact
response arrays; • the expected artifacts implied by the resolved
configuration and their stage dependencies; • produced artifacts and
their checksums; and • the execution environment and resource
configuration.</p>
<p>Two important gaps remain: the scene-wide SCS+C coefficients applied
to the geometry-normalized cube and the exact per-output-band weights
are not fully serialized in the canonical record <span class="citation"
data-cites="si_earthlab2026ao si_earthlab2026aa si_earthlab2026s">(Earth
Lab 2026ao, 2026aa, 2026s)</span>. Both are needed to reconstruct every
numerical transformation exactly.</p>
<h1 id="multi-flightline-bulk-analysis">Multi-flightline bulk
analysis</h1>
<p>The bulk implementation inspected on 9 September 2026 replaces the
earlier Parquet-centered description with direct raster streaming.
Analysis eligibility requires the requested matched products, not a
complete upstream archive or an upstream QA pass. Catalogs retain
duplicate identities and ineligible inputs. Merged Parquet remains
supported, but the direct route does not populate a pixel-scale
observation cache <span class="citation"
data-cites="si_earthlab2026a si_earthlab2026c">(Earth Lab 2026a,
2026c)</span>. The pipeline provides four related evidence products:</p>
<p>Table 3: Updated bulk-analysis products and their interpretation
<span class="citation"
data-cites="si_earthlab2026a si_earthlab2026c">(Earth Lab 2026a,
2026c)</span>.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>Product</th>
<th>Function</th>
<th>Scientific interpretation</th>
</tr>
</thead>
<tbody>
<tr>
<td>Catalog and census</td>
<td>Inventory identities, schemas,</td>
<td>Defines the analyzed collection and exclusions</td>
</tr>
<tr>
<td></td>
<td>row counts, sites, dates, and</td>
<td>before summaries are interpreted.</td>
</tr>
<tr>
<td></td>
<td>duplicate or rejected inputs.</td>
<td></td>
</tr>
<tr>
<td>Compact statistics</td>
<td>Reduce aligned raster windows</td>
<td>Supports grouped fitting without storing</td>
</tr>
<tr>
<td></td>
<td>to mergeable per-flightline</td>
<td>another pixel-scale table.</td>
</tr>
<tr>
<td></td>
<td>moments.</td>
<td></td>
</tr>
<tr>
<td>Same-source</td>
<td>Fit pooled, per-flightline,</td>
<td>Describes relationships among products derived</td>
</tr>
<tr>
<td>relationship summaries</td>
<td>per-site, flightline-balanced,</td>
<td>from the same geometry-normalized NEON</td>
</tr>
<tr>
<td></td>
<td>and site-balanced relationships</td>
<td>observations; it is not empirical calibration</td>
</tr>
<tr>
<td></td>
<td>between wavelength-matched</td>
<td>between independently observed sensors.</td>
</tr>
<tr>
<td></td>
<td>target products.</td>
<td></td>
</tr>
<tr>
<td>Leave-one-site-out</td>
<td>Refit without one site and</td>
<td>Describes out-of-site stability of a same-source</td>
</tr>
<tr>
<td>evaluation</td>
<td>report held-out-site diagnostics.</td>
<td>synthetic relationship; it is not independent</td>
</tr>
<tr>
<td></td>
<td></td>
<td>cross-sensor validation.</td>
</tr>
</tbody>
</table>
<p>Pixels are nested within flightlines, and flightlines are nested
within sites. Pooled pixel regressions are therefore descriptive and
must not present pixel count as the number of independent land- scapes
<span class="citation" data-cites="si_hurlbert1984">(Hurlbert
1984)</span>. The three reported estimands differ only in group
contribution: pixel-pooled fitting gives each selected pixel equal
weight, flightline-balanced fitting gives each flightline equal total
weight, and site-balanced fitting gives each site equal total weight.
The exported weighting descriptions and replicate counts were checked
against these definitions. The balanced summaries are sensitivity
analyses, not independent replications or a hierarchical uncertainty
model. Validation of spatially and hierarchically structured data should
preserve that dependence in its training and test partitions <span
class="citation" data-cites="si_roberts2017">(Roberts et al.
2017)</span>. Leave-one-site-out evaluation fits on two observed sites
and evaluates the third; with only three sites, its three folds describe
those particular site/acquisition combinations rather than a population
of possible sites or a general model area of applicability <span
class="citation" data-cites="si_meyer2021">(Meyer and Pebesma
2021)</span>. All summaries inherit the limitations of the underlying
products: paired synthetic bands share one corrected NEON source and do
not constitute independently acquired drone or Landsat observations
<span class="citation"
data-cites="si_earthlab2026b si_earthlab2026d">(Earth Lab 2026b,
2026d)</span>. For each chunk, counts, means, centered sums of squares,
and cross-products are accumulated in numerically stable bivariate
moments. Merging produces flightline and collection records; inverse
merging removes a held-out site’s contribution to training. A second
bounded pass calculates errors that are not all recoverable from moments
alone <span class="citation"
data-cites="si_earthlab2026an si_earthlab2026c">(Earth Lab 2026an,
2026c)</span>. The bulk manifest and per-flightline checkpoint records
should accompany source hashes and the resolved configuration;
restartability is not a substitute for exact-run provenance. The direct
reader checks dimensions, transform, and coordinate reference system and
applies sensor- wide finite/no-data rules together with the configured
minimum-value threshold. It reads stored raster values without itself
establishing their physical scale <span class="citation"
data-cites="si_earthlab2026an">(Earth Lab 2026an)</span>. Concurrency,
window size, and storage throughput therefore matter both to
reproducibility and to the cost</p>
<figure>
<img src="../supplement-assets/si-table-page-10.png"
alt="Source page 10 for table layout verification" />
<figcaption aria-hidden="true">Source page 10 for table layout
verification</figcaption>
</figure>
<p>of repeated reads. Explicit dataset materialization and the
compatibility input path should be benchmarked separately, not described
as mandatory costs of streaming. The results interpretation layer
operates on the manifest and compact model/group tables without
reopening the source rasters <span class="citation"
data-cites="si_earthlab2026g">(Earth Lab 2026g)</span>. This
manuscript’s focused examination similarly uses the supplied CSV
exports. Neither workflow supplies a complete upstream QA census merely
by accepting inputs into a relationship analysis.</p>
<h2 id="additional-spectral-library-reporting-route">Additional
spectral-library reporting route</h2>
<p>The release-candidate interface also exposes spectral-library
preflight and reporting as first-class routes. A preflight inspects a
supplied Parquet library’s schema, group counts, and anticipated
rendering work before analysis. The reporting route reads that library
in place and can produce species summaries, quantiles, spectral
ensembles, hierarchical variability summaries, traceable
extreme-spectrum diagnostics, and optional multipage reports without
making a second row-level copy of the library <span class="citation"
data-cites="si_earthlab2026aj">(Earth Lab 2026aj)</span>. This route is
relevant to the package’s broader analysis design and is included in the
documented exact-artifact smoke. No executed spectral-library output was
supplied with the manuscript evidence bundle, however, so this
manuscript treats it as implemented and bounded-test functionality
rather than a demonstrated scientific result.</p>
<h1 id="quality-assurance-model">Quality-assurance model</h1>
<p>Every run raises four questions. Did the code execute? Were the
products required by the resolved configuration written and readable?
What did QA report about those products? Do independent observations
support their scientific interpretation? We call these process,
artifact, QA, and validation status. Remote-sensing frameworks likewise
treat validation as evidence assembled from representative comparisons
and characterized reference measurements, not as a single binary label
<span class="citation"
data-cites="si_morisette2006 si_origo2020">(Morisette et al. 2006; Origo
et al. 2020)</span>. The 43-flight campaign is a concrete example: it
reached intermediate and QA states but did not satisfy its downstream
artifact contract <span class="citation"
data-cites="si_spectralbridgeprojectteam2026">(SpectralBridge project
team 2026)</span>. SpectralBridge separately uses pass, warn, and fail
within evaluated QA records. Table 4 defines that narrower vocabulary
<span class="citation"
data-cites="si_earthlab2026s si_earthlab2026w">(Earth Lab 2026s,
2026w)</span>.</p>
<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr>
<th>Status</th>
<th>Meaning</th>
</tr>
</thead>
<tbody>
<tr>
<td>pass</td>
<td>The evaluated artifact or numerical quantity met its configured
rule.</td>
</tr>
<tr>
<td>warn</td>
<td>The evaluated quantity or known condition requires interpretation;
the</td>
</tr>
<tr>
<td></td>
<td>status does not independently establish full pipeline
completion.</td>
</tr>
<tr>
<td>fail</td>
<td>A required artifact or evaluated rule prevents the intended
interpretation.</td>
</tr>
<tr>
<td>Not evaluated</td>
<td>Available artifacts do not answer the stated question; absence of
evidence</td>
</tr>
<tr>
<td></td>
<td>is not converted into a pass.</td>
</tr>
</tbody>
</table>
<p>Table 4: QA status semantics. A status applies to its named
diagnostic, not to process execution, complete fulfillment of a resolved
artifact contract, or universal scientific validity <span
class="citation" data-cites="si_earthlab2026s si_earthlab2026w">(Earth
Lab 2026s, 2026w)</span>.</p>
<figure>
<img src="../supplement-assets/si-table-page-11.png"
alt="Source page 11 for table layout verification" />
<figcaption aria-hidden="true">Source page 11 for table layout
verification</figcaption>
</figure>
<p>QA artifacts include visual panels, machine-readable JSON and metric
records, stage-level HTML and JSON reports, and an optional combined PDF
<span class="citation" data-cites="si_earthlab2026s">(Earth Lab
2026s)</span>. These products record observed values, thresholds,
provenance fields, and reasons that a diagnostic could not be evaluated.
Several recorded thresholds are provisional workflow diagnostics rather
than externally validated scientific decision limits. For a collection
QA census, the emitted combined status is treated as authoritative
rather than reconstructed from selected metrics. pass, warn, and fail
counts are mutually exclusive. A missing or unreadable report remains a
separate category in the attempted-flightline denominator.
Stage-specific warning counts can overlap. Threshold sets and their
provisional flags must be archived so that changes in rules are not
mistaken for changes in data quality <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026x">(Earth Lab 2026w,
2026x)</span>. The supplied bulk fit status ok is not this combined QA
status.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>Recorded R10C diagnostic</th>
<th>Warn threshold</th>
<th>Fail threshold</th>
</tr>
</thead>
<tbody>
<tr>
<td>Within-footprint valid fraction</td>
<td>below 0.90</td>
<td>below 0.70</td>
</tr>
<tr>
<td>Negative-reflectance fraction</td>
<td>above 0.01</td>
<td>above 0.05</td>
</tr>
<tr>
<td>Usable-band fraction above 1.2</td>
<td>above 0.01</td>
<td>above 0.05</td>
</tr>
<tr>
<td>Absolute correction difference, 99th percentile</td>
<td>above 0.20</td>
<td>above 0.50</td>
</tr>
<tr>
<td>Chunk-seam score</td>
<td>above 1.5</td>
<td>above 2.5</td>
</tr>
<tr>
<td>Spectral-response coverage</td>
<td>below 0.98</td>
<td>below 0.90</td>
</tr>
</tbody>
</table>
<p>Table 5: Provisional R10C screening rules, not independently
validated ecological decision lim- its <span class="citation"
data-cites="si_earthlab2026x">(Earth Lab 2026x)</span>. The supplied
bulk tables do not establish that these checks were run on every
input.</p>
<h2 id="validation-tiers-and-installed-artifact-checks">Validation tiers
and installed-artifact checks</h2>
<p>The inspected documentation separates validation into two tiers. Tier
A builds the wheel and source distribution, installs the exact artifact
into a clean environment outside the source checkout, blocks network
access, and runs small deterministic smoke fixtures through the NEON,
drone, and bulk entry points. This bounded strategy addresses a common
scientific-software problem: many computations lack a complete test
oracle even when their software contracts can be tested <span
class="citation" data-cites="si_kanewala2014">(Kanewala and Bieman
2014)</span>. The public validation page reports a separate offline
campaign with 40 of 40 passing variations: five variations for each of
eight modules. It records revision bebf707, marks the working tree as
dirty, and gives 14 August 2026 as its last update. This supports the
recorded module checks but does not uniquely identify a clean source
state <span class="citation" data-cites="si_earthlab2026al">(Earth Lab
2026al)</span>. The 4 September audit reports successful clean wheel
checks on local Python 3.10, 3.11, 3.12, and 3.14 interpreters and a
source-distribution check on Python 3.10. The tag-release workflow has
the narrower supported gate of the exact wheel on Linux with Python
3.10–3.12 and the source distribution on Python 3.10 <span
class="citation"
data-cites="si_earthlab2026ap si_earthlab2026v si_earthlab2026k">(Earth
Lab 2026ap, 2026v, 2026k)</span>. The NEON smoke fixture uses an 8 × 8 ×
32 synthetic cube and exercises geometry normalization, configured
target products, Parquet conversion and merging, QA, and restart. Drone
smoke tests exercise full-image and polygon routes, and bulk smoke tests
exercise census, relationship fitting, coefficient export,
leave-one-site-out evaluation, optional materialization, and restart.
The release- candidate README also identifies spectral-library reporting
as part of the bounded exact-artifact smoke <span class="citation"
data-cites="si_earthlab2026aj">(Earth Lab 2026aj)</span>. These tests
provide evidence for packaging, stage connectivity, artifact
readability, and bounded restart behavior. They do not test production
scale or scientific accuracy.</p>
<figure>
<img src="../supplement-assets/si-table-page-12.png"
alt="Source page 12 for table layout verification" />
<figcaption aria-hidden="true">Source page 12 for table layout
verification</figcaption>
</figure>
<p>Tier B consists of selected real-flightline records such as R10C and
is the appropriate tier for operational scaling and data-dependent QA
evidence <span class="citation"
data-cites="si_earthlab2026t si_earthlab2026v">(Earth Lab 2026t,
2026v)</span>. The following sections use those distinctions
consistently. The drone campaign examines campaign- scale orchestration
and completion; R10C records a completed flightline with warnings; WREF
preserves a more limited visual QA record; and the bulk exports support
collection-level analysis of target-band products that had already been
made.</p>
<h1 id="first-production-drone-campaign-attempt">First production drone
campaign attempt</h1>
<p>The supplied production inventory covers 43 historical flight
packages: 17 from 2023 and 26 from 2024. Source discovery and staging
produced 43 working HDF5 observations and approximately 7.15 GB of
output. The inventory does not identify the exact production commit,
resolved configuration, manifest, file checksums, per-stage timings, or
a corrective revision; we leave those fields unspecified rather than
inferring them <span class="citation"
data-cites="si_spectralbridgeprojectteam2026">(SpectralBridge project
team 2026)</span>.</p>
<p>Table 6: Observed inventory after the first 43-flight drone
production attempt. Counts describe files found by post-run inspection,
not products inferred from run status.</p>
<table>
<thead>
<tr>
<th>Artifact class</th>
<th>Observed count</th>
<th>Interpretation</th>
</tr>
</thead>
<tbody>
<tr>
<td>Working HDF5</td>
<td>43</td>
<td>Persisted intermediate observation state</td>
</tr>
<tr>
<td>JSON</td>
<td>215</td>
<td>Machine-readable run or QA records; detailed roles not</td>
</tr>
<tr>
<td></td>
<td></td>
<td>supplied</td>
</tr>
<tr>
<td>QA PDF</td>
<td>43</td>
<td>Visual QA artifacts found</td>
</tr>
<tr>
<td>QA PNG</td>
<td>43</td>
<td>Visual QA artifacts found</td>
</tr>
<tr>
<td>ENVI header</td>
<td>0</td>
<td>Expected downstream representation absent</td>
</tr>
<tr>
<td>ENVI image</td>
<td>0</td>
<td>Expected downstream representation absent</td>
</tr>
<tr>
<td>Parquet</td>
<td>0</td>
<td>Expected extracted analysis product absent</td>
</tr>
</tbody>
</table>
<p>The orchestration summary classified all 43 flights as processed and
none as failed. Yet the public output contract identifies a readable
merged Parquet table with matching QA, together with configured sensor
products when requested, as the primary completion signals <span
class="citation" data-cites="si_earthlab2026af">(Earth Lab
2026af)</span>. Those products were absent. The run therefore shows that
the HDF5 route can discover, stage, and preserve intermediate states
across a substantial campaign, but it does not demonstrate corrected
drone outputs, configured Landsat-like variables, completed extraction,
or drone/Landsat agreement. We treat the mismatch as an orchestration
and completion-accounting defect. Named artifact classes made the
incomplete state visible, but the orchestration did not use that same
record correctly when assigning completion. No root cause is assigned.
The 43 working HDF5 files may support restart after correction, but
their practical reuse and downstream completion must be shown by replay.
A publication replay should retain both records: the original incomplete
attempt and the corrected run. The new record should identify its
software revision, resolved configuration, artifact contract, input and
output checksums, per-stage status, any reused HDF5 files, and the rule
that prevents completion when required products are absent. The original
attempt should not be overwritten or counted retroactively as
complete.</p>
<figure>
<img src="../supplement-assets/si-table-page-13.png"
alt="Source page 13 for table layout verification" />
<figcaption aria-hidden="true">Source page 13 for table layout
verification</figcaption>
</figure>
<h1 id="r10c-real-flightline-demonstration">R10C real-flightline
demonstration</h1>
<p>The checked-in example processes the flightline</p>
<p>NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.</p>
<p>The workflow produced all of its declared artifacts, but the combined
interpretation remained warn <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026y">(Earth Lab 2026w,
2026y)</span>. The 2,532,249,598-byte source HDF5 decoded to 1,115 lines
by 5,351 samples by 426 bands. The run wrote approximately 21 GB of
local output, while the retained validation-report bundle occupied 4.6
MB. The archived reports identify package version 2.2.0 and the
following generating revision:</p>
<p>d88e8d0947718d1e33b534080c224b703987e536.</p>
<p>The inspected repository commit, f7e7ddd, archives those reports but
did not generate them. R10C also predates the 9 September
release-preparation snapshot. We therefore use it as a record of that
historical run, not as an exact-artifact replay <span class="citation"
data-cites="si_earthlab2026t">(Earth Lab 2026t)</span>. The combined
report uses schema version 1.3 and plot-contract version 1.1. Its
declared pipeline evolution.png uses fixed display ranges for
cross-report comparability; those limits are explicitly display-only,
and values outside them remain in the machine-readable metrics. The
corresponding figure in the main manuscript summarizes the combined JSON
rather than reproducing that original report plot; the tables below
retain the detailed numerical record without duplicating that figure
<span class="citation"
data-cites="si_earthlab2026w si_earthlab2026y">(Earth Lab 2026w,
2026y)</span>.</p>
<table>
<thead>
<tr>
<th>Stage</th>
<th>Status</th>
</tr>
</thead>
<tbody>
<tr>
<td>Source acquisition</td>
<td>pass</td>
</tr>
<tr>
<td>Input reflectance</td>
<td>warn</td>
</tr>
<tr>
<td>Correction parameters</td>
<td>warn</td>
</tr>
<tr>
<td>BRDF and topographic correction</td>
<td>warn</td>
</tr>
<tr>
<td>Spectral convolution (target-band weighting)</td>
<td>pass</td>
</tr>
<tr>
<td>Analysis tables</td>
<td>pass</td>
</tr>
</tbody>
</table>
<p>Table 7: Stage statuses in the R10C combined QA record <span
class="citation" data-cites="si_earthlab2026w">(Earth Lab
2026w)</span>.</p>
<p>Several apparently conflicting values become clear once their
denominators are stated. The 0.571 bounding-box footprint fraction
describes how much of the rectangular raster is occupied by the swath;
the 1.0 within-footprint valid fraction says that all pixels inside that
footprint passed the relevant check. Likewise, the provisional threshold
in Table 5 applies to the usable-band fraction above 1.2, 1.41814 × 10−5
, rather than the all-evaluated-band fraction, 0.0593153. The report
also records zero negative-reflectance fractions for the highlighted
input, geometry-normalized, and target-band states. These are
descriptive checks, not evidence that the transformations improved
agreement with another sensor <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026y">(Earth Lab 2026w,
2026y)</span>. The 68 known poor-quality wavelength bands were
classified in report only no masking mode, and the report records data
modified=false: the bands were labeled but neither masked nor replaced.
Four persisted geometry summaries fell outside their expected radian
ranges. The walkthrough</p>
<figure>
<img src="../supplement-assets/si-table-page-14.png"
alt="Source page 14 for table layout verification" />
<figcaption aria-hidden="true">Source page 14 for table layout
verification</figcaption>
</figure>
<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr>
<th>Diagnostic</th>
<th>Recorded value</th>
</tr>
</thead>
<tbody>
<tr>
<td>Package-declared poor-quality bands retained</td>
<td>68</td>
</tr>
<tr>
<td>Classification behavior for poor-quality bands</td>
<td>Report only; no masking</td>
</tr>
<tr>
<td></td>
<td>or replacement</td>
</tr>
<tr>
<td>Bounding-box footprint fraction</td>
<td>0.571275</td>
</tr>
<tr>
<td>Within-footprint valid fraction</td>
<td>1.0</td>
</tr>
<tr>
<td>Input median reflectance</td>
<td>0.250400</td>
</tr>
<tr>
<td>Input negative-reflectance fraction</td>
<td>0.0</td>
</tr>
<tr>
<td>Fraction of evaluated input-band values above 1.2</td>
<td>0.0593153</td>
</tr>
<tr>
<td>Fraction of usable input-band values above 1.2</td>
<td></td>
</tr>
<tr>
<td>Combined-correction median reflectance</td>
<td>0.250400</td>
</tr>
<tr>
<td>Combined-correction negative-reflectance fraction</td>
<td>0.0</td>
</tr>
<tr>
<td>Fraction of evaluated corrected values above 1.2</td>
<td>0.0593168</td>
</tr>
<tr>
<td>Combined-correction absolute-difference 99th percentile</td>
<td>0.00389395 reflectance</td>
</tr>
<tr>
<td>Convolved median reflectance</td>
<td>0.144450</td>
</tr>
<tr>
<td>Convolved negative-reflectance fraction</td>
<td>0.0</td>
</tr>
<tr>
<td>Fraction of evaluated convolved values above 1.2</td>
<td></td>
</tr>
<tr>
<td>Readable Parquet outputs</td>
<td>18</td>
</tr>
</tbody>
</table>
<p>Table 8: Selected machine-readable diagnostics from the R10C combined
QA JSON <span class="citation" data-cites="si_earthlab2026w">(Earth Lab
2026w)</span>. Values describe this run and are not estimates of
performance across sites.</p>
<p>suspects that no-data values affected these summaries, but the
archived evidence does not establish the cause or show whether the issue
was confined to persisted summaries rather than fitted correction terms.
The files were not silently repaired. The combined report summarizes
stage status and two pipeline-level findings; the fuller list of
unevaluated questions comes from the stage reports and real-data
walkthrough. Those questions include separate attribution of topographic
and BRDF effects, per-output-band weight support, held-out
affine-relationship residuals and cycle consistency, and direct Landsat
Collection 2 NBAR comparability <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026x si_earthlab2026y">(Earth
Lab 2026w, 2026x, 2026y)</span>. R10C therefore demonstrates end-to-end
artifact completion for its declared historical route, stage- specific
QA, and preservation of warnings. It does not measure correction
efficacy or cross-sensor agreement <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026y">(Earth Lab 2026w,
2026y)</span>. Read beside the drone campaign, it shows why a completed
artifact chain answers a different question from a successful process
return code.</p>
<h1 id="wref-visual-qa-example">WREF visual QA example</h1>
<p>A separate four-page visual QA report for flightline</p>
<p>NEON_D16_WREF_DP1_L040-1_20230625_directional_reflectance.</p>
<p>shows the products in more detail than the combined R10C status
summary. It includes every generated ENVI representation, pre- and
post-correction diagnostics, wavelength and header checks, target-band
locations, filtering summaries, and the Parquet merge inventory. Because
the PDF</p>
<figure>
<img src="../supplement-assets/si-table-page-15.png"
alt="Source page 15 for table layout verification" />
<figcaption aria-hidden="true">Source page 15 for table layout
verification</figcaption>
</figure>
<p>identifies neither its generating SpectralBridge commit nor its QA
schema, we treat it as a visual inspection record rather than a
machine-readable collection record. The complete four-page report is
retained unchanged as a supplied source artifact. Here, its correction
plots are reflowed for legibility and selected tabular-inventory values
are presented as a visual summary. Its product overview preserves the
narrow across-track geometry and displays every target representation,
but repeated short labels for the final MicaSense products are
ambiguous; future reports should include unique product identifiers or
output paths. The correction diagnostics in Figure 1 show nearly
overlapping aggregate pre- and post-correction histograms and
wavelength-dependent changes that are small in median but heterogeneous
across pixels. The same page also displays mean slope, aspect,
sensor-zenith, and sensor-azimuth values far outside physically
meaningful radian ranges. The visual report therefore reinforces the
need to retain the geometry warning; it does not establish whether the
out-of-range values affected correction fitting or only the displayed
summaries. The spectral page, retained in the supplied source report but
not reproduced here, confirms a monotonic, finite 426-band wavelength
vector spanning approximately 384–2512 nm and reports that the ENVI
header lacks band names. It also contrasts full-cube with filtered-table
summaries that use different observational supports and therefore should
not be compared as if they described the same statistical population.
The tabular inventory in Figure 2 reports 18 Parquet files totaling 32.9
MB and a merged table containing 151 rows and 964 columns. It also
exposes an internal reporting inconsistency: the merge- status panel
counts 16 resampled inputs, while the quality-check panel states that no
resampled products were found. This disagreement should be resolved in
the report generator before the visual page is used for automated cohort
interpretation.</p>
<figure id="fig:si1">
<img src="../supplement-assets/si-figure-17.png"
alt="Original WREF diagnostic plots from report page 2, reflowed with new panel headings and a reading guide; plotted data are unchanged. (A) Pre- and post-correction distributions nearly overlap. (B) Wavelength-resolved changes retain pixel-level spread; IQR denotes the interquartile range. (C, D) Persisted geometry means lie outside expected radian ranges. These summaries require investigation and do not establish whether correction fits were affected." />
<figcaption aria-hidden="true">Original WREF diagnostic plots from
report page 2, reflowed with new panel headings and a reading guide;
plotted data are unchanged. (A) Pre- and post-correction distributions
nearly overlap. (B) Wavelength-resolved changes retain pixel-level
spread; IQR denotes the interquartile range. (C, D) Persisted geometry
means lie outside expected radian ranges. These summaries require
investigation and do not establish whether correction fits were
affected.</figcaption>
</figure>
<figure id="fig:si2">
<img src="../supplement-assets/si-figure-18.png"
alt="Selected WREF inventory values from report page 4. (A) Column groups sum to the reported merged total of 964; strip widths are proportional to counts. (B) The merge-status and quality-check panels give contradictory resampled-product statements, retained here rather than reconciled. Inventory totals and merge-input counts describe different scopes. The displayed values were checked against the checksum-verified source PDF." />
<figcaption aria-hidden="true">Selected WREF inventory values from
report page 4. (A) Column groups sum to the reported merged total of
964; strip widths are proportional to counts. (B) The merge-status and
quality-check panels give contradictory resampled-product statements,
retained here rather than reconciled. Inventory totals and merge-input
counts describe different scopes. The displayed values were checked
against the checksum-verified source PDF.</figcaption>
</figure>
<h1 id="bulk-analysis-collection-and-variable-definitions">Bulk
analysis: collection and variable definitions</h1>
<p>The preceding records ask whether requested artifacts existed and
what their QA reported. The bulk analysis begins later in the chain. It
starts with eligible target-band products and asks how their same-source
relationships vary across the accepted collection. The available bundle
contains a visual report and CSV exports. Table 14 identifies the report
and the five primary numerical tables used here. They share the
following analysis run identifier:</p>
<p>986e495c2c8e9dda579528b41df44cb24f670055558c85f54941341403a48489</p>
<p>This identifies the analysis, not an executed Git revision. No
matching run manifest was sup- plied <span class="citation"
data-cites="si_spectralbridgebulkevidencebundle2026">(SpectralBridge
bulk evidence bundle 2026)</span>.</p>
<h2 id="collection-accounting-and-acquisition-coverage">Collection
accounting and acquisition coverage</h2>
<p>The tables contain 122 distinct flightline identifiers and 18
pair-band combinations per flightline, giving 2,196 local fits. They
also contain 54 candidate coefficient records—18 relationships under
three weightings—plus 54 site fits and 54 held-out-site evaluations.
Every exported fit status is ok, but that label says nothing about
upstream QA or unrepresented attempts. Because the selection rule,
attempted-input denominator, rejected-input inventory, and
processing-partition metadata are unavailable, these counts describe
accepted records rather than a completion rate or a completed version of
the earlier 100-flightline protocol. Summing the largest exported sample
count for each flightline gives 899,692,166 selected observations. For
each pair-band, the flightline counts sum to the pooled count, which is
either 899,686,966 or 899,692,166. We retain the 5,200-observation
difference because the tables do not reveal which masks or input
conditions caused it. These observations are not independent ecological
replicates and should not be multiplied by the 18 relationships. The
repository’s description of the staged archive and checkpoints is an
operator-reported production record, not a rerun performed for this
paper <span class="citation" data-cites="si_earthlab2026u">(Earth Lab
2026u)</span>.</p>
<p>Table 9: Acquisition years parsed from distinct exported flightline
identifiers. Dates require confirmation against source metadata and the
run manifest.</p>
<table>
<thead>
<tr>
<th>Site</th>
<th>2020</th>
<th>2023</th>
<th>Total</th>
</tr>
</thead>
<tbody>
<tr>
<td>NIWO</td>
<td>23</td>
<td>9</td>
<td>32</td>
</tr>
<tr>
<td>WREF</td>
<td>0</td>
<td>40</td>
<td>40</td>
</tr>
<tr>
<td>YELL</td>
<td>0</td>
<td>50</td>
<td>50</td>
</tr>
<tr>
<td>Total</td>
<td>23</td>
<td>99</td>
<td>122</td>
</tr>
</tbody>
</table>
<p>Site and acquisition year are unevenly represented (Table 9). Holding
out NIWO removes every 2020 observation from training, whereas holding
out WREF or YELL leaves mixed-year training data. The held-out scores
therefore describe the observed combinations of site and acquisition
rather than a pure site effect. The available per-flightline exports
permit a bounded year sensitivity for the focal TM matched band-3
diagnostic, but not a year-matched refit of the pooled, balanced, or
held-out models. Table 10</p>
<figure>
<img src="../supplement-assets/si-table-page-19.png"
alt="Source page 19 for table layout verification" />
<figcaption aria-hidden="true">Source page 19 for table layout
verification</figcaption>
</figure>
<p>separates NIWO’s two filename-derived years and summarizes the other
2023 groups. NIWO medians are similar in 2020 and 2023, while the lower
WREF and YELL distributions remain visible in 2023. This descriptive
check shows that NIWO’s local median is not created solely by combining
its two years; it does not separate site, acquisition year, atmospheric
conditions, phenology, or processing history. A 2023-only model refit
would contain 99 flightlines, including only nine at NIWO, and has not
been performed. The supplied models are therefore not relabeled as
year-controlled evidence.</p>
<p>Table 10: Filename-derived year sensitivity for within-flightline R2
of TM matched band 3. Values are recalculated from the supplied
local-fit export; they are descriptive ranges, not uncertainty intervals
<span class="citation"
data-cites="si_spectralbridgebulkevidencebundle2026">(SpectralBridge
bulk evidence bundle 2026)</span>.</p>
<table>
<thead>
<tr>
<th>Site</th>
<th>Year</th>
<th>Flightlines</th>
<th>Minimum</th>
<th>Median</th>
<th>Maximum</th>
</tr>
</thead>
<tbody>
<tr>
<td>NIWO</td>
<td>2020</td>
<td>23</td>
<td>0.6938</td>
<td>0.7547</td>
<td>0.8296</td>
</tr>
<tr>
<td>NIWO</td>
<td>2023</td>
<td>9</td>
<td>0.7285</td>
<td>0.7596</td>
<td>0.8317</td>
</tr>
<tr>
<td>WREF</td>
<td>2023</td>
<td>40</td>
<td>0.4287</td>
<td>0.5280</td>
<td>0.7017</td>
</tr>
<tr>
<td>YELL</td>
<td>2023</td>
<td>50</td>
<td>0.2623</td>
<td>0.6124</td>
<td>0.7888</td>
</tr>
</tbody>
</table>
<h2 id="what-exactly-is-compared">What exactly is compared?</h2>
<p>The exported equations use x for a matched MicaSense-derived product
variable and y for a configured Landsat-derived product variable, with
fitted target ŷ = ax + b. The four product pairs are listed in Table 11.
Their names identify computational products rather than four sets of
independently acquired satellite observations. Both sides derive from
corrected NEON spectra. The table preserves exported numbering without
assigning native sensor band names or wavelength intervals that the run
evidence does not establish.</p>
<p>Table 11: Exact exported product identifiers and matched indices.
Source identifiers are defined immediately below the table.</p>
<table>
<thead>
<tr>
<th>Source family</th>
<th>Target identifier</th>
<th>Matched indices</th>
</tr>
</thead>
<tbody>
<tr>
<td>A</td>
<td>Landsat_5_TM</td>
<td>1–4</td>
</tr>
<tr>
<td>A</td>
<td>Landsat_7_ETM+</td>
<td>1–4</td>
</tr>
<tr>
<td>B</td>
<td>Landsat_8_OLI</td>
<td>1–5</td>
</tr>
<tr>
<td>B</td>
<td>Landsat_9_OLI-2</td>
<td>1–5</td>
</tr>
</tbody>
</table>
<p>Family A is MicaSense_to-match_TM_and_ETM+; family B is
MicaSense_to-match_OLI_and_ OLI-2. Source and target index fields agree
in every exported row. In this manuscript, “TM matched band 3” means
family A index 3 against Landsat_5_TM index 3. It is not an assertion
about native Landsat or MicaSense band numbering. The numerical variable
definition is recoverable; the run-specific physical definition is not
yet complete. Required records are the source wavelengths, actual
response arrays on that grid, excluded-band treatment, brightness
coefficients and their order of application, and stored-value scale,
offset, units, and no-data rules for both products. Generic packaged
centers, widths, and defaults do not demonstrate which definitions
generated this run. The audited streaming reader uses stored values; it
does not establish physical scaling for them <span class="citation"
data-cites="si_earthlab2026an">(Earth Lab 2026an)</span>. We therefore
retain slopes, correlations, and descriptive scores while treating
intercepts, RMSE, bias, and reference displacements as quantities in
exported units. We do not apply an assumed scale factor, infer</p>
<figure>
<img src="../supplement-assets/si-table-page-20.png"
alt="Source page 20 for table layout verification" />
<figcaption aria-hidden="true">Source page 20 for table layout
verification</figcaption>
</figure>
<p>physical reflectance outliers from large stored numbers alone, or
attribute the TM result to a particular spectral region.</p>
<h2 id="numerical-summaries-and-their-estimands">Numerical summaries and
their estimands</h2>
<p>The primary collection summaries use 18 relationships within each
weighting scheme (Table 12). Pooling emphasizes pixels; the balanced
schemes change group contributions. The schemes reuse observations and
are sensitivity descriptions, not independent replications. No
confidence interval is estimated by treating the 54 records as a sample
of 54 independent relationships.</p>
<p>Table 12: Separate summaries across the same 18 pair-band
relationships. TM values refer to matched band 3.</p>
<table>
<thead>
<tr>
<th>Weighting</th>
<th>Relationships</th>
<th>Median</th>
<th>TM</th>
</tr>
</thead>
<tbody>
<tr>
<td>Pixel pooled</td>
<td>18</td>
<td>0.9944</td>
<td>0.5944</td>
</tr>
<tr>
<td>Flightline balanced</td>
<td>18</td>
<td>0.9909</td>
<td>0.5950</td>
</tr>
<tr>
<td>Site balanced</td>
<td>18</td>
<td>0.9948</td>
<td>0.6043</td>
</tr>
</tbody>
</table>
<p>For the TM diagnostic, the exported within-flightline R2 agrees
numerically with squared correlation. Correlation-based local fit is
invariant to a nonzero uniform affine rescaling of either variable, but
RMSE and intercepts are not scale-invariant. This algebraic property
does not rule out spatially or spectrally varying corrections,
inconsistent encodings across inputs, or nonlinear effects. A high R2 is
not agreement with the identity line; agreement between measurement
methods requires examination of their differences and scale, not
correlation alone <span class="citation"
data-cites="si_bland1986">(Martin Bland and Altman 1986)</span>. A lower
R2 is likewise not by itself an unacceptable physical error. Scores
depend on the response distribution and require an application-specific
interpretation.</p>
<p>Table 13: Different diagnostics for TM matched band 3. Local ranges
summarize separate within- flightline fits. The site-fit column is
in-sample; the held-out column evaluates a model trained on the other
two sites. These columns are not a controlled comparison of predictive
performance.</p>
<table>
<thead>
<tr>
<th>Site</th>
<th>Local median</th>
<th>Local range</th>
<th>Site-fit</th>
<th>Held-out</th>
</tr>
</thead>
<tbody>
<tr>
<td>NIWO</td>
<td>0.7560</td>
<td>0.6938–0.8317</td>
<td>0.7810</td>
<td>0.5529</td>
</tr>
<tr>
<td>WREF</td>
<td>0.5280</td>
<td>0.4287–0.7017</td>
<td>0.5041</td>
<td>0.3305</td>
</tr>
<tr>
<td>YELL</td>
<td>0.6124</td>
<td>0.2623–0.7888</td>
<td>0.6187</td>
<td>0.5898</td>
</tr>
</tbody>
</table>
<p>Eight of the 122 TM local fits exceed 0.8; the maximum is 0.8317. No
scientific acceptance threshold is implied. The descriptive conclusion
is that changing the supplied collection weights does not remove the
lower fit and that departures from a close linear relationship also
occur within flightlines. This does not isolate within- and
between-group contributions or exclude additional pooling effects. The
diagnostic was selected after inspection of the report and should be
understood as exploratory, not a pre-specified hypothesis test. WREF’s
held-out score of 0.3305 is separate from its in-sample site-fit score
of 0.5041. Their difference is not an estimate of a geographic transfer
penalty. A controlled comparison would reserve the same WREF test
observations for both models, fit the local baseline on other WREF
spatial units, fit the external model without WREF, and evaluate both in
identical verified units. Spatial blocking, comparable training
information, and year-matched sensitivity would help distinguish</p>
<figure>
<img src="../supplement-assets/si-table-page-21.png"
alt="Source page 21 for table layout verification" />
<figcaption aria-hidden="true">Source page 21 for table layout
verification</figcaption>
</figure>
<p>transfer from fitting optimism and acquisition composition <span
class="citation" data-cites="si_roberts2017">(Roberts et al.
2017)</span>. The supplied three-site collection does not establish a
general geographic domain of applicability <span class="citation"
data-cites="si_meyer2021">(Meyer and Pebesma 2021)</span>.</p>
<h2 id="reference-displacement-is-not-prediction-error">Reference
displacement is not prediction error</h2>
<p>The supplied displacement table evaluates each equation at the median
of the per-flightline source means for its pair-band. If x̄f is a
flightline source mean, its definitions are</p>
<p><math display="block" xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mrow><mi mathvariant="normal">r</mi><mi mathvariant="normal">e</mi><mi mathvariant="normal">f</mi></mrow></msub><mo>=</mo><msub><mi>median</mi><mo>&#8289;</mo><mi>f</mi></msub><msub><mover><mi>x</mi><mo accent="true">‾</mo></mover><mi>f</mi></msub><mo>,</mo><mspace width="2.0em"></mspace><mi mathvariant="normal">Δ</mi><mo>=</mo><mi>a</mi><msub><mi>x</mi><mrow><mi mathvariant="normal">r</mi><mi mathvariant="normal">e</mi><mi mathvariant="normal">f</mi></mrow></msub><mo>+</mo><mi>b</mi><mo>−</mo><msub><mi>x</mi><mrow><mi mathvariant="normal">r</mi><mi mathvariant="normal">e</mi><mi mathvariant="normal">f</mi></mrow></msub><mo>,</mo><mspace width="2.0em"></mspace><mi>p</mi><mo>=</mo><mn>100</mn><mi mathvariant="normal">Δ</mi><mi>/</mi><msub><mi>x</mi><mrow><mi mathvariant="normal">r</mi><mi mathvariant="normal">e</mi><mi mathvariant="normal">f</mi></mrow></msub><mi>.</mi></mrow><annotation encoding="application/x-tex">
x_{\mathrm{ref}} = \operatorname{median}_f \bar{x}_f, \qquad \Delta = a x_{\mathrm{ref}} + b - x_{\mathrm{ref}}, \qquad p = 100\Delta/x_{\mathrm{ref}}. \label{eq:si-displacement}
</annotation></semantics></math></p>
<p>The same reference is used under all three weightings. The field
named absolute_correction stores signed ∆ (24 of 54 entries are
negative); the median of |p| is 7.54%, and its maximum is 110.92%. The
maximum occurs for the pooled TM matched band-3 equation, evaluated at
xref = 357.971255 exported units. These are reference-dependent equation
displacements, not residual prediction error, an accuracy improvement,
or the amount of upstream brightness correction. The results
implementation inspected at c86da6a uses a pixel-pooled source-mean
reference by default <span class="citation"
data-cites="si_earthlab2026g">(Earth Lab 2026g)</span>. The supplied
export is described by Equation 3, not silently recomputed under that
later default. Neither definition establishes a physically meaningful
correction percentage without verified value definitions and a reason to
compare source and target to the identity line. Accordingly,
displacement is retained here for report reconstruction, not used as a
principal scientific performance claim.</p>
<h2 id="executable-audit-and-file-provenance">Executable audit and file
provenance</h2>
<p>Run python scripts/audit bulk.py from the manuscript directory using
Python with NumPy and pandas. The audit verifies file hashes, run
identifiers, unique scientific keys, counts, separate weighting
summaries, filename-derived years, the descriptive year sensitivity,
local and held-out diagnostic values, inline figure coordinates, and the
displacement arithmetic. It reads the supplied exports without modifying
them or downloading data. This is a reproducible compact-table example;
it does not execute SpectralBridge or verify the reduction of the
original raster archive. Several local convenience exports reorganize
the same supplied records:</p>
<p>all_candidate_coefficients.csv, correction_magnitude_all.csv,
weakest_translation_cases.csv, weakest_20_fits.csv,
largest_translation_corrections.csv, largest_20_corrections.csv,
pooling_strategy_comparison.csv, and visual_report_summary.csv.</p>
<p>These files are derived views for review and presentation, not
independent observations or additional production evidence. The five
primary numerical exports and visual report identified below remain the
evidential inputs to the audit.</p>
<p>Table 14: SHA-256 checksums of primary supplied evidence used in this
revision. Long filenames wrap; checksums identify bytes, not scientific
validity.</p>
<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr>
<th>File</th>
<th>SHA-256</th>
</tr>
</thead>
<tbody>
<tr>
<td>SpectralBridge_Bulk_Results_Visual_</td>
<td>ac597ef955813205689177f806a87e31ffa3195bc1af681160681279cc043e66</td>
</tr>
<tr>
<td>Report.pdf</td>
<td></td>
</tr>
<tr>
<td>translation_coefficients.csv</td>
<td>899eaa37521be89fb8aa521528962c807cd122770c5d606eab03540212a95382</td>
</tr>
<tr>
<td>per_flightline_regressions.csv</td>
<td>4911fb363bdbbae37c121c5c0c511b9fba05839d9f762e84e0f900e259d4e6e1</td>
</tr>
<tr>
<td>per_site_regressions.csv</td>
<td>8b43ae837cf8e1ecf0efd09c4658ccaacb25942f7cb1383c397c211a319e8cd7</td>
</tr>
<tr>
<td>leave_one_site_out.csv</td>
<td>a8b95002fb51ac74d7a050f5803fa6528633008922dd6eb525b1d41cf39e7f3a</td>
</tr>
<tr>
<td>translation_correction_magnitude.csv</td>
<td>ee0f60cf319f5e31c798ce596059410407054f66b14996769e4d721a17493a2d</td>
</tr>
</tbody>
</table>
<h1 id="what-remains-to-be-established">What remains to be
established</h1>
<p>The current records answer useful questions, but they do not yet
reconstruct a production run. The bulk tables lack the executed
revision, manifest, input checksums, configuration, product headers, and
performance measurements. The drone inventory likewise lacks its
production revision, resolved configuration, checksums, and verified
completion record. A reproducible example needs a manifest that connects
each run identifier to those materials, together with a bounded input
subset, an executable command, and expected outputs. The bulk audit
verifies the exported tables; the drone inventory verifies the observed
file census. R10C and WREF preserve historical warnings but are not
correction references. Table 15 keeps records generated under different
revisions separate. A “not supplied” entry identifies exactly what a
publication replay or archive still needs to add.</p>
<figure>
<img src="../supplement-assets/si-table-page-23.png"
alt="Source page 23 for table layout verification" />
<figcaption aria-hidden="true">Source page 23 for table layout
verification</figcaption>
</figure>
<p>Table 15: Lineage of the evidence used in this manuscript. Missing
fields are recorded rather than inferred.</p>
<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr>
<th>Evidence</th>
<th>Input or scope</th>
<th>Generating revision</th>
<th>Configuration and QA identity</th>
<th>Archive evidence</th>
</tr>
</thead>
<tbody>
<tr>
<td>Installed-package</td>
<td>Tiny deterministic</td>
<td>Revisions identified by</td>
<td>Fixture commands and</td>
<td>Exact-distribution</td>
</tr>
<tr>
<td>fixtures</td>
<td>normal, drone, and</td>
<td>the validation and</td>
<td>expected outputs are</td>
<td>smoke records; not</td>
</tr>
<tr>
<td></td>
<td>bulk inputs</td>
<td>release-preparation</td>
<td>recorded; the release</td>
<td>production</td>
</tr>
<tr>
<td></td>
<td></td>
<td>records</td>
<td>workflow’s supported gate</td>
<td>data (Earth Lab,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>covers Python 3.10–3.12 for</td>
<td>2026ap; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>wheels and 3.10 for the</td>
<td>2026v; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>source distribution.</td>
<td>2026l).</td>
</tr>
<tr>
<td>R10C flightline</td>
<td>Named NEON R10C</td>
<td>d88e8d0 (full identifier</td>
<td>Package version 2.2.0 and</td>
<td>Checked-in</td>
</tr>
<tr>
<td></td>
<td>HDF5; bounded</td>
<td>in the R10C section);</td>
<td>stage reports recorded; a</td>
<td>machine-readable</td>
</tr>
<tr>
<td></td>
<td>fingerprint and file size</td>
<td>reports later archived</td>
<td>single bundle containing</td>
<td>reports and cited</td>
</tr>
<tr>
<td></td>
<td>recorded</td>
<td>at f7e7ddd</td>
<td>command, resolved</td>
<td>walkthrough (Earth</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>configuration, environment,</td>
<td>Lab, 2026w; Earth</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>full input checksum,</td>
<td>Lab, 2026x; Earth</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>schema/threshold identifier,</td>
<td>Lab, 2026y).</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>and report checksum was not</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>supplied.</td>
<td></td>
</tr>
<tr>
<td>WREF visual</td>
<td>Separately supplied</td>
<td>Not identified in the</td>
<td>Generating configuration,</td>
<td>Source PDF</td>
</tr>
<tr>
<td>report</td>
<td>WREF report and</td>
<td>PDF</td>
<td>QA schema, and threshold</td>
<td>retained; checksum</td>
</tr>
<tr>
<td></td>
<td>displayed product</td>
<td></td>
<td>identifier not supplied.</td>
<td>and PDF metadata</td>
</tr>
<tr>
<td></td>
<td>inventory</td>
<td></td>
<td></td>
<td>recorded in the</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>provenance JSON.</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>Used only as a</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>historical visual</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>artifact.</td>
</tr>
<tr>
<td>Bulk analysis</td>
<td>122 accepted exported</td>
<td>Executed software</td>
<td>Manifest, resolved</td>
<td>Report plus five</td>
</tr>
<tr>
<td></td>
<td>flightline identities and</td>
<td>revision not supplied;</td>
<td>configuration, response</td>
<td>primary CSVs with</td>
</tr>
<tr>
<td></td>
<td>18 pair-band</td>
<td>analysis run ID is</td>
<td>arrays, scaling, input</td>
<td>recorded SHA-256</td>
</tr>
<tr>
<td></td>
<td>relationships</td>
<td>recorded in Section 12</td>
<td>checksums, and performance</td>
<td>hashes;</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>record not supplied.</td>
<td>compact-table audit</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>is</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>reproducible (Spec-</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>tralBridge bulk</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>evidence bundle</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>2026).</td>
</tr>
<tr>
<td>Drone campaign</td>
<td>43 historical flight</td>
<td>Not supplied</td>
<td>Resolved configuration,</td>
<td>Post-run inventory</td>
</tr>
<tr>
<td></td>
<td>packages: 17 from</td>
<td></td>
<td>completion contract, stage</td>
<td>records working</td>
</tr>
<tr>
<td></td>
<td>2023 and 26 from 2024</td>
<td></td>
<td>timing, checksums, and QA</td>
<td>HDF5, JSON, PDF,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>schema identity not supplied.</td>
<td>and PNG states</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>and absent</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>ENVI/Parquet</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>states; no</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>permanent archive</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>identifier</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>supplied (Spectral-</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>Bridge project team,</td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
<td>2026).</td>
</tr>
</tbody>
</table>
<figure>
<img src="../supplement-assets/si-table-page-24.png"
alt="Source page 24 for table layout verification" />
<figcaption aria-hidden="true">Source page 24 for table layout
verification</figcaption>
</figure>
<p>Table 16: Outstanding checks and the claims they would enable. None
is reported as completed by this table audit.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>Question</th>
<th>Required evidence or comparison</th>
<th>Claim enabled</th>
</tr>
</thead>
<tbody>
<tr>
<td>Did the drone route</td>
<td>Replay the staged campaign after orchestration</td>
<td>End-to-end artifact</td>
</tr>
<tr>
<td>complete?</td>
<td>correction; verify configuration-dependent ENVI,</td>
<td>completion of the campaign,</td>
</tr>
<tr>
<td></td>
<td>configured Landsat-like, extraction, Parquet, and QA</td>
<td>not sensor validation.</td>
</tr>
<tr>
<td></td>
<td>artifacts with a completion-enforcing manifest.</td>
<td></td>
</tr>
<tr>
<td>Which affine relationship</td>
<td>Archive the reviewed registry, registry version and</td>
<td>Reconstruct the configured</td>
</tr>
<tr>
<td>was applied?</td>
<td>checksum, source and target wavelength mapping,</td>
<td>Landsat-like drone variables</td>
</tr>
<tr>
<td></td>
<td>estimator identity, coefficients, confidence state, and</td>
<td>without implying empirical</td>
</tr>
<tr>
<td></td>
<td>resolved strictness policy.</td>
<td>sensor calibration.</td>
</tr>
<tr>
<td>How does a completed</td>
<td>Follow UAV surface-reflectance validation practice;</td>
<td>A bounded comparison with</td>
</tr>
<tr>
<td>drone product compare</td>
<td>record the Landsat Collection 2 product identifier,</td>
<td>an independent observation,</td>
</tr>
<tr>
<td>with Landsat?</td>
<td>acquisition time, scaling, masks, cache or query record,</td>
<td>not universal agreement.</td>
</tr>
<tr>
<td></td>
<td>common-grid definition, resampling, overlap, temporal</td>
<td></td>
</tr>
<tr>
<td></td>
<td>offset, reference characterization, and uncertainty</td>
<td></td>
</tr>
<tr>
<td></td>
<td>analysis (Origo et al., 2025; Origo et al., 2020; U.S.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Geological Survey, 2026).</td>
<td></td>
</tr>
<tr>
<td>What do target variables</td>
<td>Archive actual wavelength grids, response weights,</td>
<td>Physical interpretation of</td>
</tr>
<tr>
<td>represent?</td>
<td>excluded bands, brightness settings, scale/offset, and</td>
<td>band support and error units.</td>
</tr>
<tr>
<td></td>
<td>no-data rules for the executed run.</td>
<td></td>
</tr>
<tr>
<td>Did geometry warnings</td>
<td>Trace source geometry through unit conversion and</td>
<td>Distinguish faulty summaries</td>
</tr>
<tr>
<td>affect corrections?</td>
<td>fitted terms; compare corrected results after any</td>
<td>from altered computation.</td>
</tr>
<tr>
<td></td>
<td>necessary repair.</td>
<td></td>
</tr>
<tr>
<td>Did retained poor-quality</td>
<td>Calculate their nonzero target-weight contributions</td>
<td>Assess spectral-support</td>
</tr>
<tr>
<td>bands influence outputs?</td>
<td>and compare results under documented exclusion rules.</td>
<td>sensitivity.</td>
</tr>
<tr>
<td>What changes during</td>
<td>Compare pure weighting and adjusted products from</td>
<td>Attribute the adjustment</td>
</tr>
<tr>
<td>brightness adjustment?</td>
<td>identical inputs, preserving both states and coefficients.</td>
<td>separately from target-band</td>
</tr>
<tr>
<td></td>
<td></td>
<td>weighting.</td>
</tr>
<tr>
<td>How well does the</td>
<td>Evaluate local and external models on the same</td>
<td>Estimate a defined predictive</td>
</tr>
<tr>
<td>equation transfer?</td>
<td>spatially held-out observations, including year-matched</td>
<td>comparison rather than an</td>
</tr>
<tr>
<td></td>
<td>sensitivity.</td>
<td>in-sample/held-out</td>
</tr>
<tr>
<td></td>
<td></td>
<td>difference.</td>
</tr>
<tr>
<td>What resources does</td>
<td>Measure wall time, process-tree peak RAM, bytes</td>
<td>Workload-specific resource</td>
</tr>
<tr>
<td>processing require?</td>
<td>read/written, concurrency, and hardware on a bounded</td>
<td>estimates, not a</td>
</tr>
<tr>
<td></td>
<td>reproducible workload; use matched conditions for any</td>
<td>hardware-independent</td>
</tr>
<tr>
<td></td>
<td>comparator.</td>
<td>speedup.</td>
</tr>
</tbody>
</table>
<figure>
<img src="../supplement-assets/si-table-page-25.png"
alt="Source page 25 for table layout verification" />
<figcaption aria-hidden="true">Source page 25 for table layout
verification</figcaption>
</figure>
<h1 id="claims-and-their-boundaries">Claims and their boundaries</h1>
<p>Table 16 lists the work still needed. The next two tables summarize
what the present records already support and where each claim stops.</p>
<p>Table 17: Claims supported by the evidence reviewed here and their
boundaries.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>Claim</th>
<th>Evidence</th>
<th>Boundary</th>
</tr>
</thead>
<tbody>
<tr>
<td>The inspected production</td>
<td>Package dependencies and</td>
<td>This describes runtime dependency, not</td>
</tr>
<tr>
<td>pathway does not require HyTools</td>
<td>internal pipeline imports at the</td>
<td>source or intellectual independence from</td>
</tr>
<tr>
<td>at runtime.</td>
<td>inspected commit; the 27–28</td>
<td>HyTools.</td>
</tr>
<tr>
<td></td>
<td>October 2025 transition</td>
<td></td>
</tr>
<tr>
<td></td>
<td>history (Earth Lab, 2026ag;</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Earth Lab, 2026i; Earth Lab,</td>
<td></td>
</tr>
<tr>
<td></td>
<td>2025b).</td>
<td></td>
</tr>
<tr>
<td>Inspected components retain</td>
<td>Provenance notices in</td>
<td>The relationship differs by component:</td>
</tr>
<tr>
<td>documented HyTools lineage.</td>
<td>neon cube.py, envi writer.py,</td>
<td>adapted code, inherited algorithms,</td>
</tr>
<tr>
<td></td>
<td>and corrections.py (Earth</td>
<td>architectural influence, and</td>
</tr>
<tr>
<td></td>
<td>Lab, 2026n; Earth Lab, 2026ae;</td>
<td>SpectralBridge-specific development should</td>
</tr>
<tr>
<td></td>
<td>Earth Lab, 2026z).</td>
<td>not be conflated.</td>
</tr>
<tr>
<td>The intended drone pipeline</td>
<td>Drone workflow documentation,</td>
<td>The 43-flight campaign did not produce the</td>
</tr>
<tr>
<td>supports full-image and polygon</td>
<td>installed-artifact smoke tests,</td>
<td>expected downstream ENVI or Parquet</td>
</tr>
<tr>
<td>extraction, reviewed</td>
<td>and relevant UAV</td>
<td>artifacts; documented capability is not</td>
</tr>
<tr>
<td>registry-based affine variables,</td>
<td>calibration/validation</td>
<td>evidence that translation or external QA ran</td>
</tr>
<tr>
<td>and optional Landsat QA while</td>
<td>practice (Earth Lab, 2026m;</td>
<td>on real campaign data.</td>
</tr>
<tr>
<td>recording correction availability</td>
<td>Earth Lab, 2026aj; Earth Lab,</td>
<td></td>
</tr>
<tr>
<td>and provenance.</td>
<td>2026t; Cao et al., 2019; Origo</td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2025).</td>
<td></td>
</tr>
<tr>
<td>The pipeline preserves named</td>
<td>Canonical path registry,</td>
<td>Some realized parameters and exact weights</td>
</tr>
<tr>
<td>intermediate products.</td>
<td>pipeline source, and</td>
<td>are not fully serialized.</td>
</tr>
<tr>
<td></td>
<td>documented outputs (Earth</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Lab, 2026e; Earth Lab, 2026i;</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Earth Lab, 2026s).</td>
<td></td>
</tr>
<tr>
<td>Configured target-band weighting</td>
<td>Source inspection and five</td>
<td>Does not validate weight provenance or</td>
</tr>
<tr>
<td>executes the implemented discrete</td>
<td>controlled validation</td>
<td>satellite agreement; brightness-adjusted</td>
</tr>
<tr>
<td>weighted average.</td>
<td>variations (Earth Lab, 2026aa;</td>
<td>outputs are a subsequent state.</td>
</tr>
<tr>
<td></td>
<td>Earth Lab, 2026ar).</td>
<td></td>
</tr>
<tr>
<td>Stages can recover from</td>
<td>Restart implementation,</td>
<td>Structural checks and matching QA</td>
</tr>
<tr>
<td>interruption by reusing artifacts</td>
<td>controlled save/restart tests,</td>
<td>fingerprints do not by themselves establish</td>
</tr>
<tr>
<td>that pass their format-specific</td>
<td>and the public output</td>
<td>that every configuration-dependent artifact</td>
</tr>
<tr>
<td>checks; QA reuse additionally</td>
<td>contract (Earth Lab, 2026f;</td>
<td>was requested and produced.</td>
</tr>
<tr>
<td>matches schema, parameters,</td>
<td>Earth Lab, 2026aq; Earth Lab,</td>
<td></td>
</tr>
<tr>
<td>thresholds, version, and artifact</td>
<td>2026af).</td>
<td></td>
</tr>
<tr>
<td>fingerprints.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>Opt-in across-track processing</td>
<td>Half-flight implementation and</td>
<td>Memory benefit and numerical agreement</td>
</tr>
<tr>
<td>creates independent left and right</td>
<td>pipeline integration (Earth Lab,</td>
<td>with a full-flightline run have not yet been</td>
</tr>
<tr>
<td>pipeline units from one source</td>
<td>2026o; Earth Lab, 2026i).</td>
<td>quantified.</td>
</tr>
<tr>
<td>HDF5.</td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<p>The present records do not yet support broad claims of universal
sensor agreement, direct drone-to- Landsat calibration, equivalent
behavior across ecosystems, or improved ecological inference. The
immediate software need is a replay of the drone route with its artifact
contract enforced. Scientific agreement then requires paired
observations, explicit spatial aggregation, held-out evaluation,
uncertainty propagation, and characterized independent references <span
class="citation" data-cites="si_origo2025 si_origo2020">(Origo et al.
2025, 2020)</span>.</p>
<figure>
<img src="../supplement-assets/si-table-page-26.png"
alt="Source page 26 for table layout verification" />
<figcaption aria-hidden="true">Source page 26 for table layout
verification</figcaption>
</figure>
<p>Table 18: Collection and execution evidence (continued from Table
17).</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>Claim</th>
<th>Evidence</th>
<th>Boundary</th>
</tr>
</thead>
<tbody>
<tr>
<td>Bulk analysis provides grouped</td>
<td>Supplied CSVs and</td>
<td>Shared-source synthetic products, three sites,</td>
</tr>
<tr>
<td>fits for 122 flightlines across three</td>
<td>operator-reported production</td>
<td>and incomplete exact-run provenance limit</td>
</tr>
<tr>
<td>sites.</td>
<td>record (SpectralBridge bulk</td>
<td>calibration and generalization claims.</td>
</tr>
<tr>
<td></td>
<td>evidence bundle 2026; Earth</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Lab, 2026u).</td>
<td></td>
</tr>
<tr>
<td>TM matched band 3 has lower fit</td>
<td>Reanalysis of 122 local fits and</td>
<td>Descriptive group-level localization; no</td>
</tr>
<tr>
<td>under all supplied weightings and</td>
<td>three weighting</td>
<td>physical cause, accuracy threshold, or isolated</td>
</tr>
<tr>
<td>within individual flightlines.</td>
<td>schemes (SpectralBridge bulk</td>
<td>pooling effect is established.</td>
</tr>
<tr>
<td></td>
<td>evidence bundle 2026).</td>
<td></td>
</tr>
<tr>
<td>The exact built distribution can</td>
<td>Tier A wheel and</td>
<td>Tiny deterministic fixtures do not establish</td>
</tr>
<tr>
<td>execute bounded normal and</td>
<td>source-distribution smoke</td>
<td>production-scale performance or scientific</td>
</tr>
<tr>
<td>drone workflows and the bulk</td>
<td>records (Earth Lab, 2026ap;</td>
<td>accuracy.</td>
</tr>
<tr>
<td>pipeline after clean installation.</td>
<td>Earth Lab, 2026v).</td>
<td></td>
</tr>
<tr>
<td>The recorded offline validation</td>
<td>Public validation tables: eight</td>
<td>The record identifies revision bebf707 but</td>
</tr>
<tr>
<td>campaign reports 40 of 40 passing</td>
<td>modules with five variations</td>
<td>also a dirty working tree; it is bounded</td>
</tr>
<tr>
<td>module variations.</td>
<td>each (Earth Lab, 2026al).</td>
<td>software-contract evidence, not an exactly</td>
</tr>
<tr>
<td></td>
<td></td>
<td>reconstructable clean revision or scientific</td>
</tr>
<tr>
<td></td>
<td></td>
<td>validation.</td>
</tr>
<tr>
<td>Spectral-library preflight and</td>
<td>Release-candidate README</td>
<td>No executed spectral-library analysis was</td>
</tr>
<tr>
<td>reporting are documented public</td>
<td>and public interface</td>
<td>supplied as manuscript evidence, so no</td>
</tr>
<tr>
<td>routes and are included in the</td>
<td>description (Earth Lab,</td>
<td>scientific result from that route is claimed</td>
</tr>
<tr>
<td>bounded exact-artifact smoke.</td>
<td>2026aj).</td>
<td>here.</td>
</tr>
<tr>
<td>The real drone route discovered</td>
<td>Post-run campaign inventory:</td>
<td>Orchestration reported 43 processed and zero</td>
</tr>
<tr>
<td>and staged 43 observations and</td>
<td>17 packages from 2023, 26 from</td>
<td>failed despite absent ENVI and Parquet</td>
</tr>
<tr>
<td>persisted working HDF5 and QA</td>
<td>2024, and approximately</td>
<td>products; complete production traversal is</td>
</tr>
<tr>
<td>artifacts.</td>
<td>7.15 GB of</td>
<td>not established.</td>
</tr>
<tr>
<td></td>
<td>output (SpectralBridge project</td>
<td></td>
</tr>
<tr>
<td></td>
<td>team, 2026).</td>
<td></td>
</tr>
<tr>
<td>QA preserves warnings and</td>
<td>Machine-readable R10C</td>
<td>Statuses apply only to the diagnostics that</td>
</tr>
<tr>
<td>unevaluated questions.</td>
<td>combined report and</td>
<td>ran.</td>
</tr>
<tr>
<td></td>
<td>documented QA</td>
<td></td>
</tr>
<tr>
<td></td>
<td>semantics (Earth Lab, 2026w;</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Earth Lab, 2026y).</td>
<td></td>
</tr>
<tr>
<td>The documented R10C flightline</td>
<td>Checked-in stage artifacts and</td>
<td>One flightline is not a multi-site performance</td>
</tr>
<tr>
<td>completes end to end.</td>
<td>combined QA report (Earth</td>
<td>estimate.</td>
</tr>
<tr>
<td></td>
<td>Lab, 2026w; Earth Lab, 2026y).</td>
<td></td>
</tr>
<tr>
<td>Candidate study flightlines span</td>
<td>Recorded candidate source sizes</td>
<td>Variation in source size does not yet establish</td>
</tr>
<tr>
<td>approximately 2.5–16 GB in</td>
<td>and the pre-specified study</td>
<td>the corresponding variation in peak memory,</td>
</tr>
<tr>
<td>source-file size.</td>
<td>resource record (Earth Lab,</td>
<td>wall time, or other resource requirements.</td>
</tr>
<tr>
<td></td>
<td>2026t).</td>
<td></td>
</tr>
</tbody>
</table>
<figure>
<img src="../supplement-assets/si-table-page-27.png"
alt="Source page 27 for table layout verification" />
<figcaption aria-hidden="true">Source page 27 for table layout
verification</figcaption>
</figure>
<h1 id="reproducibility-checklist">Reproducibility checklist</h1>
<p>The checklist below turns those boundaries into a practical archive
specification. For every included flightline, record the following
items, consistent with guidance for reproducible computational research,
FAIR workflows, and packaged research objects <span class="citation"
data-cites="si_sandve2013 si_wilson2017 si_goble2020 si_soilandreyes2022">(Sandve
et al. 2013; Wilson et al. 2017; Goble et al. 2020; Soiland-Reyes et al.
2022)</span>:</p>
<ol type="1">
<li>the full input identifier, product code, site, date, input checksum,
and any embedded identity metadata used to verify the filename-derived
identity; 2. source file size in bytes; 3. the complete command and
resolved configuration, including full- or half-flight mode and window;
4. the required artifact contract implied by that configuration and the
completion rule applied to it; 5. the SpectralBridge commit, exact wheel
or source-distribution checksum, and dependency environment; 6. worker
count, host information, wall time, and peak resident memory; 7. hashes
for source-product, corrected, convolved, tabular, and QA outputs; 8.
stage-level and combined QA JSON records; 9. the exact spectral-response
definitions and brightness coefficients used; 10. for drone affine
products, the reviewed registry version and checksum, estimator
identity, wavelength mapping, coefficient identifiers and values,
confidence state, and strictness policy; 11. for optional external
Landsat QA, the product identifier, acquisition time, masks, query or
cache record, common grid, resampling, overlap rule, and temporal
offset; 12. any manual exclusions, reruns, or interpretation decisions;
13. both the original and corrected run records when a
completion-accounting defect is discovered, including which intermediate
artifacts were reused; 14. links between every reported study statistic
and the contributing source-flightline records; and 15. the bulk run
identifier, manifest, source catalog, duplicate decisions, weighting
scheme, stored- value scaling, reference-value definition, and
streaming, compatibility, or materialization mode when bulk analysis is
used.</li>
</ol>
<p>The R10C artifact records its generating commit and bounded input
fingerprint, but it does not package the command, resolved
configuration, dependency environment, full input checksum, and report
checksum as one replay record. A publication archive should close that
gap and should either rerun R10C under the publication commit or retain
the revision difference explicitly <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026y">(Earth Lab 2026w,
2026y)</span>. The drone archive has the complementary gap: it preserves
intermediate campaign output but does not identify the production
revision or demonstrate fulfillment of the requested downstream contract
<span class="citation"
data-cites="si_spectralbridgeprojectteam2026">(SpectralBridge project
team 2026)</span>.</p>
<h1 id="figure-and-table-provenance">Figure and table provenance</h1>
<p>The conceptual sensor figure is drawn directly in main.tex. Its
Landsat 8 OLI and MicaSense red- band centers and widths come from
figures/sensor_band_example.json, which records the pinned repository
source <span class="citation" data-cites="si_earthlab2026q">(Earth Lab
2026q)</span>. The native drawing uses centers of 654.6 and 650 nm and
full widths at half maximum of 37.5 and 16 nm, respectively. The
spectrum and Gaussian response profiles are illustrative and prominently
labeled as approximations rather than measured response curves. Landsat
8 measured relative spectral responses are documented independently
<span class="citation" data-cites="si_barsi2014">(Barsi et al.
2014)</span>; a future revision could replace the Gaussian illustration
with versioned measured curves if those data are incorporated with
matching provenance. No such substitution is made here. The R10C summary
figure is drawn directly in main.tex, with labels and rounded values
checked against figures/r10c_qa_extract.json. Stage statuses and
highlights in that extract are tran- scribed from the combined QA JSON;
unevaluated questions are drawn from the cited stage records and
walkthrough. The extract records both the archive commit and the
reports’ generating revi- sion <span class="citation"
data-cites="si_earthlab2026w si_earthlab2026x si_earthlab2026y">(Earth
Lab 2026w, 2026x, 2026y)</span>. Before submission, the extract should
be regenerated automatically from checksum-verified copies of those
records or independently checked against each one. The three-pipeline
diagram, completion-gate diagram, and bulk diagnostic figure are drawn
directly in main.tex. The pipeline’s bulk row follows the September
streaming revision; its drone row represents the intended contract and
is explicitly distinguished from the observed campaign inventory. The
completion-gate figure is conceptual and contains no measured
quantities. The bulk diagnostic’s three observed flightline ranges and
medians are checked against the supplied CSVs by scripts/ audit_bulk.py.
Results, definitions, and primary file hashes are included directly in
this supplement. The original report and exports are unchanged. The
audit checks numerical consistency and does not rerun the raster
workflow. Typography and colors are defined in the preambles; drawings
compile as vector graphics without Python execution. Status labels
distinguish warnings from passing checks without relying on color alone.
In the bulk figure, range lines and filled median markers represent
local fits; ranges are not confidence intervals. Held-out scores are
reported separately so the figure does not suggest a paired predictive
comparison. The WREF figures are composed directly in supplement.tex
from the retained original PDF, whose checksum was verified against
figures/wref_visual_qa_provenance.json. Original vector plots from page
2 are cropped and reflowed with new headings, top-row axis labels, and a
caution note; the plotted data, tick values, and legends are unchanged.
The nodata-exclusion note is retained in the new reading guide. Selected
page 4 inventory values were checked against the PDF text: 18 files,
32.9 MB, 151 merged rows, and 964 columns comprising 426 raw, 426
corrected, 58 convolved, and 54 metadata columns. The merge panel’s 16
resampled inputs and the quality check’s conflicting absence message are
both retained. This derivative does not reproduce every field on the
original page or resolve its conflicting messages. The complete source
report remains unchanged, including the product overview and spectral
checks not reproduced here. Its filename, checksum, PDF creation
metadata, and evidence limitations are recorded in the provenance JSON.
Values from this visual report are not used as cohort observations.</p>
<h1 id="a-software-lineage-and-implementation-provenance">A Software
lineage and implementation provenance</h1>
<p>SpectralBridge began as an effort to use HyTools directly for NEON
HDF5 and ENVI input/output, image and chunk iteration, topographic and
BRDF correction, spectral resampling, and output writing <span
class="citation" data-cites="si_chlus2025 si_earthlab2025a">(Chlus et
al. 2025; Earth Lab 2025a)</span>. As sensor-specific, operational, and
evidential requirements accumulated, the team repeatedly modified,
specialized, and replaced parts of that pathway. The current package is
therefore not a thin interface around HyTools. HyTools nevertheless
remains its closest implementation predecessor and an important part of
its scholarly provenance. The relationship is not captured by a single
label. It includes published scientific methods im- plemented by both
projects, source explicitly adapted from HyTools, historical HyTools
source retained outside the active package tree, interoperability work
during the transition, and workflow components for which the reviewed
evidence identifies no material HyTools implementation lineage. Because
the available audit does not quantify line-by-line derivation across the
complete codebase, the manuscript does not convert the team’s
qualitative experience of an extensive rewrite into a percentage-of-code
claim. These categories answer different questions. A scientific
citation identifies the origin and interpre- tation of a method. A
source notice identifies implementation lineage. A dependency
declaration states what must be installed at runtime. A historical
repository tree records development history. None substitutes for the
others. In particular, implementing the same published equation does not
by itself establish code adaptation, while removing HyTools from runtime
dependencies does not remove adaptation already present in source.</p>
<h2 id="a.1-evidence-and-revision-boundary">A.1 Evidence and revision
boundary</h2>
<p>The file-level claims below are bounded to explicit notices in the
source files pinned for the 4 September audit and to the repository
history already cited in this supplement. The later source audit
supplied for this manuscript additionally reports original HyTools
source and notices under deprecated/; the current repository exposes
that historical tree, but an exact commit for the completed provenance
audit was not supplied <span class="citation"
data-cites="si_earthlab2026ak si_earthlab2026ac">(Earth Lab 2026ak,
2026ac)</span>. No standalone HYTOOLS_PROVENANCE.md or provenance
manifest accompanied the manuscript materials. The table therefore uses
“uncertain” where the supplied evidence does not establish a stronger
classification, and it does not attribute later provenance documentation
backward to R10C, f7e7ddd, or c86da6a. The runtime transition is better
established. October 2025 history records direct compatibility work
followed by the addition of internal NEON access, ENVI writing,
correction, and resampling components <span class="citation"
data-cites="si_earthlab2025a si_earthlab2025b">(Earth Lab 2025a,
2025b)</span>. At both inspected manuscript snapshots, HyTools is absent
from the declared runtime dependencies <span class="citation"
data-cites="si_earthlab2026ag si_earthlab2026l">(Earth Lab 2026ag,
2026l)</span>. That supports the statement that the inspected production
pathway does not require HyTools to be installed. It does not support a
statement that SpectralBridge contains no HyTools-derived
implementation.</p>
<h2 id="a.2-component-level-provenance">A.2 Component-level
provenance</h2>
<p>Tables 19–21 separate scientific-method credit from implementation
credit. “Adapted from HyTools” is reserved for source files that say so.
“No material lineage detected” means only that the reviewed notices and
audit did not identify such lineage; it is not a universal claim of
independent creation.</p>
<p>Table 19: Scientific-method and implementation provenance for
correction components. Classifica- tions are evidence-bounded rather
than claims of originality.</p>
<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr>
<th>SpectralBridge component</th>
<th>Scientific method or source</th>
<th>HyTools relationship</th>
<th>SpectralBridge role</th>
<th>Attribution evidence</th>
</tr>
</thead>
<tbody>
<tr>
<td>Solar/incidence</td>
<td>Solar incidence on</td>
<td>calc cosine i is</td>
<td>Supplies pixelwise</td>
<td>Method literature plus source</td>
</tr>
<tr>
<td>geometry</td>
<td>sloped terrain;</td>
<td>explicitly adapted</td>
<td>illumination geometry for</td>
<td>notice (Earth Lab, 2026z).</td>
</tr>
<tr>
<td></td>
<td>established</td>
<td>from HyTools.</td>
<td>topographic fitting and</td>
<td></td>
</tr>
<tr>
<td></td>
<td>remote-sensing</td>
<td></td>
<td>application.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>geometry (Teillet</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 1997).</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Topographic-</td>
<td>Terrain-illumination</td>
<td>Portions of the</td>
<td>Adds SpectralBridge masks,</td>
<td>HyTools and pinned correction</td>
</tr>
<tr>
<td>correction</td>
<td>normalization in the</td>
<td>correction architecture</td>
<td>streamed flightline statistics,</td>
<td>sources (Chlus et al., 2025;</td>
</tr>
<tr>
<td>framework</td>
<td>remote-sensing</td>
<td>and geometry</td>
<td>neutral fallbacks, named</td>
<td>Earth Lab, 2026z; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>literature (Teillet</td>
<td>implementation retain</td>
<td>artifacts, and optional tiled</td>
<td>2026ao).</td>
</tr>
<tr>
<td></td>
<td>et al., 1997; Soenen</td>
<td>documented HyTools</td>
<td>fitting.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2005).</td>
<td>lineage.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>SCS+C</td>
<td>Sun-canopy-sensor</td>
<td>Shared published</td>
<td>Estimates and applies</td>
<td>Original method and software</td>
</tr>
<tr>
<td></td>
<td>plus C</td>
<td>method implemented</td>
<td>per-band topographic terms</td>
<td>lineage cited separately.</td>
</tr>
<tr>
<td></td>
<td>formulation (Soenen</td>
<td>inside a module with</td>
<td>in the configured processing</td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2005).</td>
<td>documented HyTools</td>
<td>mode.</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>adaptation; HyTools is</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>not credited as the</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>origin of SCS+C.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>BRDF</td>
<td>Kernel-driven</td>
<td>Adapted and</td>
<td>Fits or applies</td>
<td>Method papers, HyTools</td>
</tr>
<tr>
<td>correction and</td>
<td>normalization and</td>
<td>specialized from</td>
<td>NEON-focused coefficients,</td>
<td>release, and source</td>
</tr>
<tr>
<td>fitting</td>
<td>FlexBRDF</td>
<td>HyTools correction</td>
<td>reference geometry, masks,</td>
<td>notice (Chlus et al., 2025;</td>
</tr>
<tr>
<td></td>
<td>practice (Roujean</td>
<td>and kernel code.</td>
<td>fallbacks, and stage</td>
<td>Earth Lab, 2026z; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>et al., 1992; Wanner</td>
<td></td>
<td>diagnostics.</td>
<td>2026ao).</td>
</tr>
<tr>
<td></td>
<td>et al., 1995; Schaaf</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2002; Queally</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2022).</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Ross</td>
<td>Ross model family and</td>
<td>calc volume kernel is</td>
<td>Evaluates the</td>
<td>Original models plus function</td>
</tr>
<tr>
<td>volumetric</td>
<td>later kernel</td>
<td>explicitly adapted</td>
<td>volume-scattering term used</td>
<td>notice (Earth Lab, 2026z).</td>
</tr>
<tr>
<td>kernel</td>
<td>formulations (Ross,</td>
<td>from HyTools.</td>
<td>in BRDF fitting and</td>
<td></td>
</tr>
<tr>
<td></td>
<td>1981; Roujean et al.,</td>
<td></td>
<td>normalization.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>1992; Wanner et al.,</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>1995).</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Li geometric</td>
<td>Li geometric-optical</td>
<td>calc geom kernel is</td>
<td>Evaluates the</td>
<td>Original models plus function</td>
</tr>
<tr>
<td>kernel</td>
<td>model family and</td>
<td>explicitly adapted</td>
<td>geometric-scattering term</td>
<td>notice (Earth Lab, 2026z).</td>
</tr>
<tr>
<td></td>
<td>reciprocal kernels (Li</td>
<td>from HyTools.</td>
<td>used in BRDF fitting and</td>
<td></td>
</tr>
<tr>
<td></td>
<td>and Strahler, 1992;</td>
<td></td>
<td>normalization.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Wanner et al., 1995).</td>
<td></td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<h2 id="a.3-historical-source-packaging-and-licensing">A.3 Historical
source, packaging, and licensing</h2>
<p>The source under deprecated/ must be distinguished from both active
SpectralBridge modules and installed dependencies. Its presence
documents historical reuse and preserves original HyTools notices; it
does not by itself show that the active pipeline imports that tree or
that users must install HyTools. Conversely, describing the tree as
historical does not erase the adapted portions present in active files.
The inspected package metadata searches for importable packages under
src/ and does not declare</p>
<figure>
<img src="../supplement-assets/si-table-page-31.png"
alt="Source page 31 for table layout verification" />
<figcaption aria-hidden="true">Source page 31 for table layout
verification</figcaption>
</figure>
<p>Table 20: Scientific-method and implementation provenance for
input/output and sensor-translation components.</p>
<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr>
<th>SpectralBridge component</th>
<th>Scientific method or source</th>
<th>HyTools relationship</th>
<th>SpectralBridge role</th>
<th>Attribution evidence</th>
</tr>
</thead>
<tbody>
<tr>
<td>NEON HDF5</td>
<td>NEON product</td>
<td>Portions of NeonCube</td>
<td>Provides bounded NEON</td>
<td>File notice and pinned</td>
</tr>
<tr>
<td>reading and</td>
<td>structure and</td>
<td>are explicitly adapted</td>
<td>array, metadata, mask,</td>
<td>source (Earth Lab, 2026n).</td>
</tr>
<tr>
<td>ancillary access</td>
<td>metadata (National</td>
<td>and simplified from</td>
<td>wavelength, and ancillary</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Ecological Observatory</td>
<td>HyTools open neon</td>
<td>access for staged processing.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Network, 2026).</td>
<td>and related access</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>logic.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>ENVI header</td>
<td>ENVI representation</td>
<td>Portions of header and</td>
<td>Writes canonical</td>
<td>File notice and pinned</td>
</tr>
<tr>
<td>and writing</td>
<td>and NEON-derived</td>
<td>writer logic are</td>
<td>source-product and</td>
<td>source (Earth Lab, 2026ae).</td>
</tr>
<tr>
<td></td>
<td>metadata handling;</td>
<td>explicitly adapted</td>
<td>corrected raster/header</td>
<td></td>
</tr>
<tr>
<td></td>
<td>not a new scientific</td>
<td>from HyTools.</td>
<td>pairs with SpectralBridge</td>
<td></td>
</tr>
<tr>
<td></td>
<td>algorithm.</td>
<td></td>
<td>naming and stage contracts.</td>
<td></td>
</tr>
<tr>
<td>Target-band</td>
<td>Normalized</td>
<td>Early workflows used</td>
<td>Implements the tested</td>
<td>History and current source</td>
</tr>
<tr>
<td>weighting /</td>
<td>response-weighted</td>
<td>HyTools resampling.</td>
<td>discrete weight-matrix</td>
<td>cited without an independence</td>
</tr>
<tr>
<td>spectral</td>
<td>spectral</td>
<td>The reviewed</td>
<td>contract and records</td>
<td>claim (Earth Lab, 2025a; Earth</td>
</tr>
<tr>
<td>resampling</td>
<td>integration (Chander</td>
<td>resample.py citation</td>
<td>configured target products</td>
<td>Lab, 2025b; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>et al., 2013; Roy et al.,</td>
<td>does not itself</td>
<td>and subsequent</td>
<td>2026aa).</td>
</tr>
<tr>
<td></td>
<td>2016).</td>
<td>document current</td>
<td>adjustments.</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>adapted code; material</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>current lineage is</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>therefore uncertain.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>Sensor</td>
<td>Empirical affine</td>
<td>No material HyTools</td>
<td>Maintains reviewed</td>
<td>SpectralBridge documentation</td>
</tr>
<tr>
<td>translation</td>
<td>relationships fitted</td>
<td>implementation lineage</td>
<td>coefficient registries and</td>
<td>and bulk records (Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>among same-source</td>
<td>was detected in the</td>
<td>applies configured affine</td>
<td>2026m; Earth Lab, 2026b).</td>
</tr>
<tr>
<td></td>
<td>configured</td>
<td>reviewed evidence.</td>
<td>relationships as a distinct</td>
<td></td>
</tr>
<tr>
<td></td>
<td>representations; not a</td>
<td></td>
<td>state.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>HyTools scientific</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>method.</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Drone pipeline</td>
<td>UAV calibration and</td>
<td>Correction functions</td>
<td>Preserves drone identity,</td>
<td>Component-specific</td>
</tr>
<tr>
<td></td>
<td>correction</td>
<td>may traverse the</td>
<td>correction availability,</td>
<td>boundary (Earth Lab, 2026m;</td>
</tr>
<tr>
<td></td>
<td>requirements derive</td>
<td>HyTools-derived</td>
<td>native and configured</td>
<td>Earth Lab, 2026z).</td>
</tr>
<tr>
<td></td>
<td>from the UAV</td>
<td>correction components</td>
<td>products, extraction, and</td>
<td></td>
</tr>
<tr>
<td></td>
<td>remote-sensing</td>
<td>above; no material</td>
<td>QA.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>literature (Aasen et al.,</td>
<td>HyTools lineage was</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>2018; Mamaghani and</td>
<td>detected for drone</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>Salvaggio, 2019; Cao</td>
<td>discovery, staging,</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2019).</td>
<td>translation, extraction,</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>or campaign</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>orchestration.</td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<figure>
<img src="../supplement-assets/si-table-page-32.png"
alt="Source page 32 for table layout verification" />
<figcaption aria-hidden="true">Source page 32 for table layout
verification</figcaption>
</figure>
<p>Table 21: Implementation provenance for workflow, analysis, and
historical-source components.</p>
<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr>
<th>SpectralBridge component</th>
<th>Scientific method or source</th>
<th>HyTools relationship</th>
<th>SpectralBridge role</th>
<th>Attribution evidence</th>
</tr>
</thead>
<tbody>
<tr>
<td>Pipeline</td>
<td>File-mediated scientific</td>
<td>Earlier orchestration</td>
<td>Defines canonical paths,</td>
<td>Transition history and</td>
</tr>
<tr>
<td>contracts and</td>
<td>workflow design; no</td>
<td>interacted directly</td>
<td>required artifacts,</td>
<td>architecture (Earth Lab, 2025b;</td>
</tr>
<tr>
<td>restart</td>
<td>single</td>
<td>with HyTools; current</td>
<td>validation, reuse, and</td>
<td>Earth Lab, 2026p; Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>correction-method</td>
<td>stage architecture was</td>
<td>restart boundaries.</td>
<td>2026i; Earth Lab, 2026f).</td>
</tr>
<tr>
<td></td>
<td>source.</td>
<td>informed by that</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>history. No claim of</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>source independence is</td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>made.</td>
<td></td>
<td></td>
</tr>
<tr>
<td>QA and</td>
<td>Scientific validation</td>
<td>No material HyTools</td>
<td>Produces machine-readable</td>
<td>SpectralBridge QA and</td>
</tr>
<tr>
<td>provenance</td>
<td>and research-object</td>
<td>implementation lineage</td>
<td>stage and combined reports,</td>
<td>validation records (Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>principles (Morisette</td>
<td>was detected in the</td>
<td>diagnostic figures, evidence</td>
<td>2026s; Earth Lab, 2026ap).</td>
</tr>
<tr>
<td></td>
<td>et al., 2006; Goble</td>
<td>reviewed evidence.</td>
<td>levels, and artifact</td>
<td></td>
</tr>
<tr>
<td></td>
<td>et al., 2020;</td>
<td></td>
<td>contracts.</td>
<td></td>
</tr>
<tr>
<td></td>
<td>Soiland-Reyes et al.,</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td>2022).</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Bulk analysis</td>
<td>Grouped regression,</td>
<td>No material HyTools</td>
<td>Streams completed products</td>
<td>Bulk source and</td>
</tr>
<tr>
<td></td>
<td>balanced summaries,</td>
<td>implementation lineage</td>
<td>into per-flightline statistics,</td>
<td>documentation (Earth Lab,</td>
</tr>
<tr>
<td></td>
<td>and held-out site</td>
<td>was detected in the</td>
<td>pooled and balanced fits,</td>
<td>2026b; Earth Lab, 2026c; Earth</td>
</tr>
<tr>
<td></td>
<td>analysis as specified in</td>
<td>reviewed evidence.</td>
<td>site summaries, and</td>
<td>Lab, 2026g).</td>
</tr>
<tr>
<td></td>
<td>this study.</td>
<td></td>
<td>leave-one-site-out</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td>diagnostics.</td>
<td></td>
</tr>
<tr>
<td>Historical</td>
<td>Original HyTools</td>
<td>Historical/vendored</td>
<td>Development and archival</td>
<td>Later repository audit and</td>
</tr>
<tr>
<td>deprecated/</td>
<td>software and notices,</td>
<td>HyTools source with</td>
<td>context; not treated here as</td>
<td>current tree (Chlus et al., 2025;</td>
</tr>
<tr>
<td>source</td>
<td>not a distinct scientific</td>
<td>original authorship,</td>
<td>an active runtime</td>
<td>Earth Lab, 2026ac).</td>
</tr>
<tr>
<td></td>
<td>method.</td>
<td>copyright, and GPL</td>
<td>component.</td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td>information retained.</td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<p>HyTools as a dependency <span class="citation"
data-cites="si_earthlab2026ag si_earthlab2026l">(Earth Lab 2026ag,
2026l)</span>. However, the manuscript materials do not include an
unpacked wheel and source distribution from the later provenance-audit
revision. This supplement therefore does not make a final claim about
whether every file under deprecated/ is absent from both distribution
formats. That packaging question should be closed by recording the exact
audit commit and listing the contents of the built wheel and source
archive. HyTools 1.6.1 is distributed under GPL-3.0, and the inspected
SpectralBridge revisions declare GPLv3 or GPL-3.0-or-later. Active files
containing adapted portions retain HyTools attribution notices <span
class="citation"
data-cites="si_chlus2025 si_earthlab2026ag si_earthlab2026l si_earthlab2026n si_earthlab2026ae si_earthlab2026z">(Chlus
et al. 2025; Earth Lab 2026ag, 2026l, 2026n, 2026ae, 2026z)</span>. This
is a concise record of the licenses and notices present in the cited
software, not a legal interpretation.</p>
<h2 id="a.4-spectralbridge-contribution-boundary">A.4 SpectralBridge
contribution boundary</h2>
<p>The package’s contribution does not depend on presenting established
correction equations or adapted low-level components as newly invented.
The evidence supports a contribution at the level of organization and
application: explicit sensor and product handling; named intermediate
artifacts; target-band construction and recorded translation states;
drone preparation and extraction; restart and completion contracts; QA
and provenance records; and campaign- and collection-scale analysis
<span class="citation"
data-cites="si_earthlab2026p si_earthlab2026i si_earthlab2026m si_earthlab2026s si_earthlab2026b">(Earth
Lab 2026p, 2026i, 2026m, 2026s, 2026b)</span>. These components combine
established environmental remote-sensing methods and attributed prior
software into an inspectable system built for a specific cross-sensor
measurement problem.</p>
<figure>
<img src="../supplement-assets/si-table-page-33.png"
alt="Source page 33 for table layout verification" />
<figcaption aria-hidden="true">Source page 33 for table layout
verification</figcaption>
</figure>
<p>This distinction reinforces the manuscript’s broader evidential
argument. Inspectable scientific software should expose not only input
provenance, parameters, transformations, QA, and outputs, but also the
lineage of important implementations used to perform those
transformations. A reader can then distinguish the origin of a
scientific method, the ancestry of its code, the package required at
runtime, and the workflow contribution made by SpectralBridge without
collapsing them into a single novelty claim.</p>
<h1 id="b-relationship-to-neighboring-software">B Relationship to
neighboring software</h1>
<p>SpectralBridge overlaps several established software families, but
the resemblance occurs at different layers. Table 22 distinguishes
similarity in algorithms, scientific objective, data access, orchestra-
tion, and scalable analysis. This comparison is important because the
package’s contribution is architectural and evidential rather than a
claim to have invented the underlying normalization or weighting
methods.</p>
<p>Table 22: Relationship between SpectralBridge and neighboring
correction, harmonization, and retrieval software.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>System</th>
<th>Important resemblance</th>
<th>Boundary relative to SpectralBridge</th>
</tr>
</thead>
<tbody>
<tr>
<td>HyTools</td>
<td>The enabling predecessor and closest</td>
<td>A general hyperspectral-processing library.</td>
</tr>
<tr>
<td></td>
<td>methodological relative: early</td>
<td>Current SpectralBridge does not require it at</td>
</tr>
<tr>
<td></td>
<td>SpectralBridge used it directly, and</td>
<td>runtime; the divergence is a specialized file</td>
</tr>
<tr>
<td></td>
<td>current components retain documented</td>
<td>contract, explicit measurement states, restart</td>
</tr>
<tr>
<td></td>
<td>adapted and algorithmic lineage (Chlus</td>
<td>pathway, tabular products, and staged QA</td>
</tr>
<tr>
<td></td>
<td>et al., 2025; Earth Lab, 2026n; Earth</td>
<td>evidence, not an absence of HyTools-derived code.</td>
</tr>
<tr>
<td></td>
<td>Lab, 2026ae; Earth Lab, 2026z).</td>
<td></td>
</tr>
<tr>
<td>Harmonized Landsat</td>
<td>Applies atmospheric correction, cloud</td>
<td>An operational harmonized satellite data product</td>
</tr>
<tr>
<td>and Sentinel-2 (HLS)</td>
<td>and shadow masking, co-registration,</td>
<td>at common spatial support. Its multi-step design</td>
</tr>
<tr>
<td></td>
<td>common gridding, BRDF normalization,</td>
<td>and evaluated bandpass methods clarify why</td>
</tr>
<tr>
<td></td>
<td>and spectral bandpass adjustment to</td>
<td>SpectralBridge’s configured representations or</td>
</tr>
<tr>
<td></td>
<td>operational Landsat and Sentinel-2</td>
<td>affine variables are not, by themselves, a complete</td>
</tr>
<tr>
<td></td>
<td>observations (Claverie et al., 2018; Ju</td>
<td>harmonized satellite observation (Claverie, 2023).</td>
</tr>
<tr>
<td></td>
<td>et al., 2025).</td>
<td></td>
</tr>
<tr>
<td>Sen2Like</td>
<td>Generates Sentinel-2-like harmonized or</td>
<td>A satellite virtual-constellation processor whose</td>
</tr>
<tr>
<td></td>
<td>fused products from Landsat and</td>
<td>goal includes common geometry and resolution.</td>
</tr>
<tr>
<td></td>
<td>Sentinel-2 using geometric correction,</td>
<td>SpectralBridge instead uses NEON as a</td>
</tr>
<tr>
<td></td>
<td>atmospheric correction, spectral band</td>
<td>translating reference and deliberately leaves</td>
</tr>
<tr>
<td></td>
<td>adjustment, BRDF normalization, and</td>
<td>spatial reconciliation to downstream analysis.</td>
</tr>
<tr>
<td></td>
<td>optional spatial fusion (Saunier et al.,</td>
<td></td>
</tr>
<tr>
<td></td>
<td>2022).</td>
<td></td>
</tr>
<tr>
<td>FORCE</td>
<td>Mass-processes Landsat and Sentinel-2</td>
<td>An operational archive-processing and data-cube</td>
</tr>
<tr>
<td></td>
<td>archives into analysis-ready data and</td>
<td>system. SpectralBridge is smaller in scope and</td>
</tr>
<tr>
<td></td>
<td>supports large-area time-series analysis,</td>
<td>emphasizes persisted intermediate measurement</td>
</tr>
<tr>
<td></td>
<td>including radiometric, topographic, and</td>
<td>states for diagnosing a cross-sensor comparison.</td>
</tr>
<tr>
<td></td>
<td>BRDF-related processing (Frantz,</td>
<td></td>
</tr>
<tr>
<td></td>
<td>2019).</td>
<td></td>
</tr>
<tr>
<td>ISOFIT</td>
<td>Uses optimal estimation and</td>
<td>Solves an upstream atmospheric-retrieval problem.</td>
</tr>
<tr>
<td></td>
<td>radiative-transfer modeling to estimate</td>
<td>SpectralBridge inherits the reflectance state of the</td>
</tr>
<tr>
<td></td>
<td>surface reflectance and atmospheric</td>
<td>NEON directional-reflectance product rather than</td>
</tr>
<tr>
<td></td>
<td>state from imaging-spectrometer</td>
<td>retrieving reflectance from radiance.</td>
</tr>
<tr>
<td></td>
<td>radiance (Thompson et al., 2018).</td>
<td></td>
</tr>
</tbody>
</table>
<p>SpectralBridge is thus closest to HyTools in methods and portions of
code, to HLS and Sen2Like</p>
<figure>
<img src="../supplement-assets/si-table-page-34.png"
alt="Source page 34 for table layout verification" />
<figcaption aria-hidden="true">Source page 34 for table layout
verification</figcaption>
</figure>
<p>Table 23: Relationship between SpectralBridge and neighboring
toolbox, workflow, and data- infrastructure software.</p>
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th>System</th>
<th>Important resemblance</th>
<th>Boundary relative to SpectralBridge</th>
</tr>
</thead>
<tbody>
<tr>
<td>EnMAP-Box</td>
<td>Provides a broad environment for</td>
<td>A general QGIS-based imaging-spectroscopy</td>
</tr>
<tr>
<td></td>
<td>visualizing and processing multi- and</td>
<td>toolbox. It supplies interactive algorithms and</td>
</tr>
<tr>
<td></td>
<td>hyperspectral imagery, spectral profiles,</td>
<td>applications rather than SpectralBridge’s</td>
</tr>
<tr>
<td></td>
<td>and derived analyses (Jakimow et al.,</td>
<td>opinionated cross-sensor sequence and evidence</td>
</tr>
<tr>
<td></td>
<td>2023).</td>
<td>vocabulary.</td>
</tr>
<tr>
<td>NEON utilities</td>
<td>Tools such as neonUtilities support</td>
<td>Data-access and preparation utilities do not</td>
</tr>
<tr>
<td></td>
<td>discovery, download, stacking, and</td>
<td>themselves define the geometry normalization,</td>
</tr>
<tr>
<td></td>
<td>preparation of NEON data</td>
<td>target-band construction, staged artifacts, or</td>
</tr>
<tr>
<td></td>
<td>products (Lunch et al., 2026).</td>
<td>cross-sensor QA used here.</td>
</tr>
<tr>
<td>Snakemake and</td>
<td>Express file- or data-dependent</td>
<td>Domain-general workflow engines do not supply</td>
</tr>
<tr>
<td>Nextflow</td>
<td>computational workflows, manage</td>
<td>reflectance semantics, sensor transformations,</td>
</tr>
<tr>
<td></td>
<td>ordered execution, and support</td>
<td>spatial-support distinctions, or scientifically</td>
</tr>
<tr>
<td></td>
<td>reproducible restart across computing</td>
<td>interpreted QA. They could orchestrate</td>
</tr>
<tr>
<td></td>
<td>environments (K¨oster and Rahmann,</td>
<td>SpectralBridge but do not replace its domain</td>
</tr>
<tr>
<td></td>
<td>2012; Di Tommaso et al., 2017).</td>
<td>model.</td>
</tr>
<tr>
<td>Open Data Cube</td>
<td>Organize and analyze large</td>
<td>Data infrastructure addresses cataloging, storage,</td>
</tr>
<tr>
<td>and Pangeo</td>
<td>Earth-observation or geoscience</td>
<td>and computation at scale. It does not specify how</td>
</tr>
<tr>
<td></td>
<td>collections and provide scalable access</td>
<td>cross-sensor reflectance comparability should be</td>
</tr>
<tr>
<td></td>
<td>to multidimensional data (Killough,</td>
<td>constructed or which intermediate measurement</td>
</tr>
<tr>
<td></td>
<td>2018; Pangeo Community, 2026).</td>
<td>states should be retained.</td>
</tr>
</tbody>
</table>
<p>in scientific motivation, to FORCE in operational organization, and
to workflow systems in its file-mediated execution. It does not replace
any of them. Its narrower role is to preserve the stages of a
cross-sensor construction, keep band space distinct from spatial
support, and show where an unexpected pattern first appears. It is not a
new correction algorithm, atmospheric-retrieval system, global
harmonized product, spatial-fusion method, general workflow engine, or
direct drone-to-Landsat calibration.</p>
<h1 id="c-prospective-qa-and-resource-protocol">C Prospective QA and
resource protocol</h1>
<p>An earlier study plan specified 100 NEON flightlines. We retain it as
a prospective protocol rather than applying it retroactively to either
the 122 accepted flightlines in the bulk collection or the separate
43-package drone attempt. Before NEON collections are combined, the
selection rule, attempted-input list, configurations, and missing QA and
resource records must be reconciled. These runs answer different
questions and should remain separate records. The study treats each
original source flightline as one operational unit for completion, QA
prevalence, and resource reporting. Pixels are not pooled across
flightlines for the primary summaries, because cube dimensions differ
and pooled pixels would allow larger flightlines to dominate. Left and
right processing halves, where used, remain paired partitions of one
source flightline and are not counted as independent flightlines. Site
is the highest unit for statements about out-of-site operational or
diagnostic stability <span class="citation"
data-cites="si_hurlbert1984">(Hurlbert 1984)</span>. The study record
should define the sampling frame and selection rule; represented sites
and years; attempted, completed, excluded, and repeated flightlines;
processing partitions; publication commit and resolved configuration;
execution environment; and missing or unreadable QA reports. Missing</p>
<figure>
<img src="../supplement-assets/si-table-page-35.png"
alt="Source page 35 for table layout verification" />
<figcaption aria-hidden="true">Source page 35 for table layout
verification</figcaption>
</figure>
<p>reports remain in the denominator. Runs combined in one summary must
use the same response and brightness definitions, QA schema, and
thresholds. If a run is replaced, the original attempt and the reason
for replacement should remain in the archive. Completion and status
outcomes will be reported as counts and percentages; continuous
diagnostics will be summarized by median, interquartile range, and
range. Balanced summaries will remain distinct from pooled pixel
descriptions. The completed synthetic-translation results do not supply
the missing upstream QA and resource measurements.</p>
<h2 id="c.1-resource-use-analysis">C.1 Resource-use analysis</h2>
<p>Hyperspectral processing is computationally demanding because
hundreds of co-registered bands create high-dimensional data volumes,
and useful analysis must also manage noise, calibration, dimensionality,
and algorithmic scaling <span class="citation"
data-cites="si_plaza2009 si_bioucasdias2013">(Plaza et al. 2009;
Bioucas-Dias et al. 2013)</span>. SpectralBridge adds correction models,
multiple target products, tabular extraction, and QA records to that
baseline workload, making resource behavior part of the reproducibility
evidence rather than a purely operational detail. Candidate source HDF5
files recorded for the study range from approximately 2.5–16 GB.
Repository guidance notes that some production workflows may require
roughly 250 GB of RAM, but that value is an operational planning
estimate rather than a study result <span class="citation"
data-cites="si_earthlab2026t si_earthlab2026ai">(Earth Lab 2026t,
2026ai)</span>. On-disk HDF5 size is only one candidate predictor
because compression, decoded dimensions, band count, data type,
processing mode, and concurrency can alter memory demand. Resource
reporting will therefore avoid a single unqualified memory requirement.
For each run, the analysis will retain source size in bytes; raster
lines, samples, bands, and data type; available compression metadata;
complete-process-tree peak resident memory; wall time; worker count;
backend; full- or half-flight mode and window; completion status; and
host CPU and RAM information. Peak memory will be sampled for the parent
process and descendants throughout each run, with the sampling interval
and aggregation rule recorded. The primary resource figure will plot
peak resident memory against both source file size and decoded cube
size, identify failed or incomplete runs, and distinguish worker count
and full- versus half-flight processing. Associations will be stratified
or adjusted for these execution settings rather than pooled without
qualification. Memory-aborted runs will be reported as right-censored
operational observations, not treated as completed peak- memory
measurements or silently excluded. The analysis will report rank
associations with each size measure; a regression will be added only if
its form and residual behavior are defensible. This describes
operational scaling for the evaluated environment, not a
hardware-independent complexity guarantee. For the updated bulk route,
profile selected ENVI bytes and decoded dimensions, eligible
observations, requested pair-bands, window size, concurrent readers,
storage characteristics, process-tree peak RAM, and
checkpoint/temporary/output bytes. Time cataloging, the statistics pass,
aggregation, the second error-evaluation pass, and compact report
generation separately. Compatibility and explicit
dataset-materialization modes require their own measurements. A bounded
representative workload can establish resource use for that workload; a
claim of superior performance requires a stated comparator under matched
conditions. The staged archive’s size does not establish a speedup or
measured peak-memory reduction <span class="citation"
data-cites="si_earthlab2026c si_earthlab2026u">(Earth Lab 2026c,
2026u)</span>.</p>
<p>D Availability and citation status</p>
<p>The historical 4 September metadata snapshot reports version 2.2.0
and Python 3.10 or newer. Its license and CI/release configuration are
described by the pinned sources <span class="citation"
data-cites="si_earthlab2026ag si_earthlab2026ab si_earthlab2026h si_earthlab2026k">(Earth
Lab 2026ag, 2026ab, 2026h, 2026k)</span>. Those records remain the basis
of the historical flightline source audit, not proof of the software
configuration that generated either the supplied bulk run or the drone
campaign attempt. The 4 September hardening audit identified metadata,
licensing, provenance, dependency, and publication-configuration issues
<span class="citation" data-cites="si_earthlab2026v">(Earth Lab
2026v)</span>. The 9 September commit c86da6a prepares 2.3.0rc1,
synchronizes metadata, and reports source and exact-distribution smoke
checks. External publisher configuration, tag creation, and publication
remain separate owner-controlled steps <span class="citation"
data-cites="si_earthlab2026l">(Earth Lab 2026l)</span>. As of 25
September 2026, the repository README documented candidate installation
but the public GitHub release page listed no 2.3.0rc1 release; a live
check on 12 October lists v1.0.0 as latest <span class="citation"
data-cites="si_earthlab2026aj si_earthlab2026ah">(Earth Lab 2026aj,
2026ah)</span>. The exact revision used for the later 43-flight drone
production attempt was not supplied, so neither f7e7ddd nor c86da6a is
assigned to it. The completion-accounting defect is under investigation,
but this manuscript cites no corrective commit and makes no claim that a
fix has passed human review or campaign replay <span class="citation"
data-cites="si_spectralbridgeprojectteam2026">(SpectralBridge project
team 2026)</span>. The public GitHub Pages validation record was last
updated on 14 August 2026 and should not be read as a live summary of
the later release-preparation or drone-campaign evidence. Its landing
page also uses broader language about harmonization, Landsat
referencing, and model transfer than the evidence reviewed here
establishes. This supplement therefore uses the site for documented
interfaces and recorded tests while retaining the manuscript’s narrower
distinctions among configured representations, artifact completion, QA,
and independent scientific validation <span class="citation"
data-cites="si_earthlab2026al si_earthlab2026ad">(Earth Lab 2026al,
2026ad)</span>. The DOI 10.5281/zenodo.11167877 identifies the 9 May
2024 pre-rename cross-sensor-cal archive <span class="citation"
data-cites="si_earthlab2026j">(Earth Lab 2026j)</span>. Submission
should use a permanent post-rename software archive and a packaged
results record linking the run manifest, inputs, software,
configuration, executable examples, outputs, and exact numerical
definitions <span class="citation"
data-cites="si_smith2016 si_soilandreyes2022">(Smith et al. 2016;
Soiland-Reyes et al. 2022)</span>. The local bulk-bundle citation
explicitly records that no permanent public identifier was supplied.</p>
<h1 class="unnumbered" id="references">References</h1>
<div id="refs" class="references csl-bib-body hanging-indent"
data-entry-spacing="0" role="list">
<div id="ref-si_aasen2018" class="csl-entry" role="listitem">
Aasen, Helge, Eija Honkavaara, Arko Lucieer, and Pablo J. Zarco-Tejada.
2018. <span>“<span class="nocase">Quantitative Remote Sensing at
Ultra-High Resolution with UAV Spectroscopy: A Review of Sensor
Technology, Measurement Procedures, and Data Correction
Workflows</span>.”</span> <em>Remote Sensing</em> 10 (7): 1091. <a
href="https://doi.org/10.3390/rs10071091">https://doi.org/10.3390/rs10071091</a>.
</div>
<div id="ref-si_barsi2014" class="csl-entry" role="listitem">
Barsi, Julia, Kenton Lee, Geir Kvaran, Brian Markham, and Jeffrey
Pedelty. 2014. <span>“<span class="nocase">The Spectral Response of the
Landsat-8 Operational Land Imager</span>.”</span> <em>Remote
Sensing</em> 6 (10): 10232–51. <a
href="https://doi.org/10.3390/rs61010232">https://doi.org/10.3390/rs61010232</a>.
</div>
<div id="ref-si_bioucasdias2013" class="csl-entry" role="listitem">
Bioucas-Dias, Jose M., Antonio Plaza, Gustavo Camps-Valls, Paul
Scheunders, Nasser Nasrabadi, and Jocelyn Chanussot. 2013. <span>“<span
class="nocase">Hyperspectral Remote Sensing Data Analysis and Future
Challenges</span>.”</span> <em>IEEE Geoscience and Remote Sensing
Magazine</em> 1 (2): 6–36. <a
href="https://doi.org/10.1109/MGRS.2013.2244672">https://doi.org/10.1109/MGRS.2013.2244672</a>.
</div>
<div id="ref-si_cao2019" class="csl-entry" role="listitem">
Cao, Sen, Brad Danielson, Shari Clare, Shantel Koenig, Carlos
Campos-Vargas, and Arturo Sanchez-Azofeifa. 2019. <span>“<span
class="nocase">Radiometric calibration assessments for UAS-borne
multispectral cameras: Laboratory and field protocols</span>.”</span>
<em>ISPRS Journal of Photogrammetry and Remote Sensing</em> 149: 132–45.
<a
href="https://doi.org/10.1016/j.isprsjprs.2019.01.016">https://doi.org/10.1016/j.isprsjprs.2019.01.016</a>.
</div>
<div id="ref-si_chander2013" class="csl-entry" role="listitem">
Chander, Gyanesh, Nischal Mishra, Dennis L. Helder, David B. Aaron, Amit
Angal, Taeyoung Choi, Xiaoxiong Xiong, and David R. Doelling. 2013.
<span>“<span class="nocase">Applications of Spectral Band Adjustment
Factors (SBAF) for Cross-Calibration</span>.”</span> <em>IEEE
Transactions on Geoscience and Remote Sensing</em> 51 (3): 1267–81. <a
href="https://doi.org/10.1109/TGRS.2012.2228007">https://doi.org/10.1109/TGRS.2012.2228007</a>.
</div>
<div id="ref-si_chlus2025" class="csl-entry" role="listitem">
Chlus, Adam, Zhiwei Ye, Ting Zheng, Natalie Queally, Evan Greenberg, and
Philip A. Townsend. 2025. <span>“<span class="nocase">HyTools:
Hyperspectral image processing library</span>.”</span> <a
href="https://doi.org/10.5281/zenodo.16900026">https://doi.org/10.5281/zenodo.16900026</a>.
<p class="si-reference-note">Source note: Version 1.6.1. Software release</p></div>
<div id="ref-si_claverie2023" class="csl-entry" role="listitem">
Claverie, Martin. 2023. <span>“<span class="nocase">Evaluation of
surface reflectance bandpass adjustment techniques</span>.”</span>
<em>ISPRS Journal of Photogrammetry and Remote Sensing</em> 198: 210–22.
<a
href="https://doi.org/10.1016/j.isprsjprs.2023.03.011">https://doi.org/10.1016/j.isprsjprs.2023.03.011</a>.
</div>
<div id="ref-si_claverie2018" class="csl-entry" role="listitem">
Claverie, Martin, Junchang Ju, Jeffrey G. Masek, Jennifer L. Dungan,
Eric F. Vermote, Jean-Claude Roger, Sergii V. Skakun, and Christopher
Justice. 2018. <span>“<span class="nocase">The Harmonized Landsat and
Sentinel-2 surface reflectance data set</span>.”</span> <em>Remote
Sensing of Environment</em> 219: 145–61. <a
href="https://doi.org/10.1016/j.rse.2018.09.002">https://doi.org/10.1016/j.rse.2018.09.002</a>.
</div>
<div id="ref-si_ditommaso2017" class="csl-entry" role="listitem">
Di Tommaso, Paolo, Maria Chatzou, Evan W Floden, Pablo Prieto Barja,
Emilio Palumbo, and Cedric Notredame. 2017. <span>“<span
class="nocase">Nextflow enables reproducible computational
workflows</span>.”</span> <em>Nature Biotechnology</em> 35 (4): 316–19.
<a
href="https://doi.org/10.1038/nbt.3820">https://doi.org/10.1038/nbt.3820</a>.
</div>
<div id="ref-si_dungan2002" class="csl-entry" role="listitem">
Dungan, J. L., J. N. Perry, M. R. T. Dale, P. Legendre, S.
Citron‐Pousty, M.‐J. Fortin, A. Jakomulska, M. Miriti, and M. S.
Rosenberg. 2002. <span>“<span class="nocase">A balanced view of scale in
spatial statistical analysis</span>.”</span> <em>Ecography</em> 25 (5):
626–40. <a
href="https://doi.org/10.1034/j.1600-0587.2002.250510.x">https://doi.org/10.1034/j.1600-0587.2002.250510.x</a>.
</div>
<div id="ref-si_earthlab2025a" class="csl-entry" role="listitem">
Earth Lab. 2025a. <span>“<span class="nocase">SpectralBridge history:
HyTools compatibility and dependency work, 8–23 October
2025</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/commits/main/?since=2025-10-08&amp;until=2025-10-23">https://github.com/earthlab/spectralbridge/commits/main/?since=2025-10-08&amp;until=2025-10-23</a>.
</div>
<div id="ref-si_earthlab2025b" class="csl-entry" role="listitem">
———. 2025b. <span>“<span class="nocase">SpectralBridge history:
transition to internal NEON processing components, 27–28 October
2025</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/commits/main/?since=2025-10-27&amp;until=2025-10-28">https://github.com/earthlab/spectralbridge/commits/main/?since=2025-10-27&amp;until=2025-10-28</a>.
</div>
<div id="ref-si_earthlab2026a" class="csl-entry" role="listitem">
———. 2026a. <span>“<span class="nocase">Build a bulk cross-run
analysis</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/docs/vignettes/bulk-analysis.md">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/docs/vignettes/bulk-analysis.md</a>.
<p class="si-reference-note">Source note: Source snapshot inspected 9 September 2026.</p></div>
<div id="ref-si_earthlab2026b" class="csl-entry" role="listitem">
———. 2026b. <span>“<span class="nocase">Build a production bulk
population analysis</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/bulk-analysis.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/bulk-analysis.md</a>.
</div>
<div id="ref-si_earthlab2026c" class="csl-entry" role="listitem">
———. 2026c. <span>“<span class="nocase">Bulk pipeline implementation:
September snapshot</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/pipelines/bulk.py">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/pipelines/bulk.py</a>.
<p class="si-reference-note">Source note: Source snapshot inspected 9 September 2026.</p></div>
<div id="ref-si_earthlab2026d" class="csl-entry" role="listitem">
———. 2026d. <span>“<span class="nocase">Bulk population-analysis
pipeline source</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/pipelines/bulk.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/pipelines/bulk.py</a>.
</div>
<div id="ref-si_earthlab2026e" class="csl-entry" role="listitem">
———. 2026e. <span>“<span class="nocase">Canonical path
registry</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/paths.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/paths.py</a>.
</div>
<div id="ref-si_earthlab2026f" class="csl-entry" role="listitem">
———. 2026f. <span>“<span class="nocase">Carry On My Wayward Son: resume
a run</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/carry-on-wayward-son.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/carry-on-wayward-son.md</a>.
</div>
<div id="ref-si_earthlab2026g" class="csl-entry" role="listitem">
———. 2026g. <span>“<span class="nocase">Compact bulk results
interpretation implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/bulk/results.py">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/bulk/results.py</a>.
<p class="si-reference-note">Source note: Source snapshot inspected 9 September 2026.</p></div>
<div id="ref-si_earthlab2026h" class="csl-entry" role="listitem">
———. 2026h. <span>“<span class="nocase">Continuous-integration
workflow</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/.github/workflows/ci.yml">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/.github/workflows/ci.yml</a>.
</div>
<div id="ref-si_earthlab2026i" class="csl-entry" role="listitem">
———. 2026i. <span>“<span class="nocase">Core NEON pipeline
source</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/pipelines/pipeline.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/pipelines/pipeline.py</a>.
</div>
<div id="ref-si_earthlab2026j" class="csl-entry" role="listitem">
———. 2026j. <span>“<span class="nocase">DOI and Zenodo
status</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/doi-zenodo.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/doi-zenodo.md</a>.
</div>
<div id="ref-si_earthlab2026k" class="csl-entry" role="listitem">
———. 2026k. <span>“<span class="nocase">Exact-artifact release
workflow</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/.github/workflows/release.yml">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/.github/workflows/release.yml</a>.
<p class="si-reference-note">Source note: Accessed 4 September 2026</p></div>
<div id="ref-si_earthlab2026l" class="csl-entry" role="listitem">
———. 2026l. <span>“<span class="nocase">Finalize SpectralBridge 2.3.0rc1
preparation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/commit/c86da6a642a8a0bef37108df31af1fed1a882bd2">https://github.com/earthlab/spectralbridge/commit/c86da6a642a8a0bef37108df31af1fed1a882bd2</a>.
<p class="si-reference-note">Source note: Commit inspected 9 September 2026; preparation is distinct from publication.</p></div>
<div id="ref-si_earthlab2026m" class="csl-entry" role="listitem">
———. 2026m. <span>“<span class="nocase">Module vignette 6: process drone
imagery</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/drone-processing.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/vignettes/drone-processing.md</a>.
</div>
<div id="ref-si_earthlab2026n" class="csl-entry" role="listitem">
———. 2026n. <span>“<span class="nocase">NeonCube and NEON ancillary-data
implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/neon_cube.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/neon_cube.py</a>.
</div>
<div id="ref-si_earthlab2026o" class="csl-entry" role="listitem">
———. 2026o. <span>“<span class="nocase">Opt-in across-track half-flight
processing</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/half_flight.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/half_flight.py</a>.
<p class="si-reference-note">Source note: Implementation and pipeline documentation inspected 4 September 2026</p></div>
<div id="ref-si_earthlab2026p" class="csl-entry" role="listitem">
———. 2026p. <span>“<span class="nocase">Package
architecture</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/architecture.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/architecture.md</a>.
</div>
<div id="ref-si_earthlab2026q" class="csl-entry" role="listitem">
———. 2026q. <span>“<span class="nocase">Packaged Landsat and MicaSense
band definitions</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/data/landsat_band_parameters.json">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/data/landsat_band_parameters.json</a>.
</div>
<div id="ref-si_earthlab2026r" class="csl-entry" role="listitem">
———. 2026r. <span>“<span class="nocase">Packaged Landsat brightness
adjustments derived from Table Moun- tain HLS medians</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/tree/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/data/brightness">https://github.com/earthlab/spectralbridge/tree/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/data/brightness</a>.
</div>
<div id="ref-si_earthlab2026s" class="csl-entry" role="listitem">
———. 2026s. <span>“<span class="nocase">Pipeline outputs and file
structure</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/pipeline/outputs.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/pipeline/outputs.md</a>.
</div>
<div id="ref-si_earthlab2026t" class="csl-entry" role="listitem">
———. 2026t. <span>“<span class="nocase">Production validation
record</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/production-validation-record.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/production-validation-record.md</a>.
</div>
<div id="ref-si_earthlab2026u" class="csl-entry" role="listitem">
———. 2026u. <span>“<span class="nocase">Production validation record:
September snapshot</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/docs/dev/production-validation-record.md">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/docs/dev/production-validation-record.md</a>.
<p class="si-reference-note">Source note: Operator-reported production evidence; inspected 9 September 2026.</p></div>
<div id="ref-si_earthlab2026v" class="csl-entry" role="listitem">
———. 2026v. <span>“<span class="nocase">PyPI publication-hardening
audit</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/publication-hardening-audit-2026-09-04.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/dev/publication-hardening-audit-2026-09-04.md</a>.
<p class="si-reference-note">Source note: Review dated 4 September 2026</p></div>
<div id="ref-si_earthlab2026w" class="csl-entry" role="listitem">
———. 2026w. <span>“<span class="nocase">R10C combined QA
record</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/artifacts/r10c-l002-20210915/qa/combined/combined_qa.json">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/artifacts/r10c-l002-20210915/qa/combined/combined_qa.json</a>.
</div>
<div id="ref-si_earthlab2026x" class="csl-entry" role="listitem">
———. 2026x. <span>“<span class="nocase">R10C source-acquisition QA
record and threshold provenance</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/artifacts/r10c-l002-20210915/qa/stages/00_acquisition/stage_qa.json">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/artifacts/r10c-l002-20210915/qa/stages/00_acquisition/stage_qa.json</a>.
<p class="si-reference-note">Source note: Records generating commit d88e8d0947718d1e33b534080c224b703987e536</p></div>
<div id="ref-si_earthlab2026y" class="csl-entry" role="listitem">
———. 2026y. <span>“<span class="nocase">Real flightline QA walkthrough:
R10C, D10, L002, 2021-09-15</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/real-data-example.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/real-data-example.md</a>.
</div>
<div id="ref-si_earthlab2026z" class="csl-entry" role="listitem">
———. 2026z. <span>“<span class="nocase">SCS+C and kernel-driven BRDF
correction implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/corrections.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/corrections.py</a>.
</div>
<div id="ref-si_earthlab2026aa" class="csl-entry" role="listitem">
———. 2026aa. <span>“<span class="nocase">Spectral resampling
source</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/resample.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/resample.py</a>.
</div>
<div id="ref-si_earthlab2026ab" class="csl-entry" role="listitem">
———. 2026ab. <span>“<span class="nocase">SpectralBridge citation
metadata</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/CITATION.cff">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/CITATION.cff</a>.
</div>
<div id="ref-si_earthlab2026ac" class="csl-entry" role="listitem">
———. 2026ac. <span>“<span class="nocase">SpectralBridge deprecated
historical source tree</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/tree/main/deprecated">https://github.com/earthlab/spectralbridge/tree/main/deprecated</a>.
<p class="si-reference-note">Source note: Current repository tree inspected 26 September 2026; the exact commit for the later provenance audit was not supplied with the manuscript materials</p></div>
<div id="ref-si_earthlab2026ad" class="csl-entry" role="listitem">
———. 2026ad. <span>“<span class="nocase">SpectralBridge documentation
landing page</span>.”</span> <a
href="https://earthlab.github.io/spectralbridge/">https://earthlab.github.io/spectralbridge/</a>.
<p class="si-reference-note">Source note: Documentation inspected 25 September 2026; public scientific framing is broader than the bounded evidence evaluated in this manuscript.</p></div>
<div id="ref-si_earthlab2026ae" class="csl-entry" role="listitem">
———. 2026ae. <span>“<span class="nocase">SpectralBridge ENVI header and
writer implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/envi_writer.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/envi_writer.py</a>.
</div>
<div id="ref-si_earthlab2026af" class="csl-entry" role="listitem">
———. 2026af. <span>“<span class="nocase">SpectralBridge outputs and file
structure</span>.”</span> <a
href="https://earthlab.github.io/spectralbridge/pipeline/outputs/">https://earthlab.github.io/spectralbridge/pipeline/outputs/</a>.
<p class="si-reference-note">Source note: Documentation inspected 25 September 2026; defines the public per-flightline artifact contract, success signals, restart checks, and QA reuse fingerprints.</p></div>
<div id="ref-si_earthlab2026ag" class="csl-entry" role="listitem">
———. 2026ag. <span>“<span class="nocase">SpectralBridge package
metadata</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/pyproject.toml">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/pyproject.toml</a>.
</div>
<div id="ref-si_earthlab2026ah" class="csl-entry" role="listitem">
———. 2026ah. <span>“<span class="nocase">SpectralBridge public GitHub
releases</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/releases">https://github.com/earthlab/spectralbridge/releases</a>.
<p class="si-reference-note">Source note: Inspected 12 October 2026; v1.0.0 was listed as latest; no public 2.3.0rc1 GitHub release was listed.</p></div>
<div id="ref-si_earthlab2026ai" class="csl-entry" role="listitem">
———. 2026ai. <span>“<span class="nocase">SpectralBridge README and
command-line quickstart</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/README.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/README.md</a>.
</div>
<div id="ref-si_earthlab2026aj" class="csl-entry" role="listitem">
———. 2026aj. <span>“<span class="nocase">SpectralBridge repository
README: September release-candidate snapshot</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/README.md">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/README.md</a>.
<p class="si-reference-note">Source note: Pinned source inspected 25 September 2026; documents the affine drone-translation registry, optional Landsat QA, compact bulk analysis, spectral-library reporting, and exact-artifact smoke scope.</p></div>
<div id="ref-si_earthlab2026ak" class="csl-entry" role="listitem">
———. 2026ak. <span>“<span class="nocase">SpectralBridge source
repository, commit
f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/tree/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705">https://github.com/earthlab/spectralbridge/tree/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705</a>.
</div>
<div id="ref-si_earthlab2026al" class="csl-entry" role="listitem">
———. 2026al. <span>“<span class="nocase">SpectralBridge validation
evidence</span>.”</span> <a
href="https://earthlab.github.io/spectralbridge/validation/">https://earthlab.github.io/spectralbridge/validation/</a>.
<p class="si-reference-note">Source note: Documentation inspected 25 September 2026; page reports 40 of 40 offline contract variations passing at revision bebf707 from a dirty working tree and identifies 14 August 2026 as its last update.</p></div>
<div id="ref-si_earthlab2026am" class="csl-entry" role="listitem">
———. 2026am. <span>“<span>SpectralBridge: Start Here</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/START_HERE.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/START_HERE.md</a>.
</div>
<div id="ref-si_earthlab2026an" class="csl-entry" role="listitem">
———. 2026an. <span>“<span class="nocase">Streaming bulk statistics
implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/bulk/streaming.py">https://github.com/earthlab/spectralbridge/blob/c86da6a642a8a0bef37108df31af1fed1a882bd2/src/spectralbridge/bulk/streaming.py</a>.
<p class="si-reference-note">Source note: Source snapshot inspected 9 September 2026.</p></div>
<div id="ref-si_earthlab2026ao" class="csl-entry" role="listitem">
———. 2026ao. <span>“<span class="nocase">Topographic and BRDF
implementation</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/brdf_topo.py">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/src/spectralbridge/brdf_topo.py</a>.
</div>
<div id="ref-si_earthlab2026ap" class="csl-entry" role="listitem">
———. 2026ap. <span>“<span class="nocase">Validation evidence
index</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/index.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/index.md</a>.
</div>
<div id="ref-si_earthlab2026aq" class="csl-entry" role="listitem">
———. 2026aq. <span>“<span class="nocase">Validation—save and restart
behavior</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/save_restart.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/save_restart.md</a>.
</div>
<div id="ref-si_earthlab2026ar" class="csl-entry" role="listitem">
———. 2026ar. <span>“<span class="nocase">Validation—sensor
convolution</span>.”</span> <a
href="https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/sensor_convolution.md">https://github.com/earthlab/spectralbridge/blob/f7e7ddd2e01ee5f7cd74688eb479fd12fbc0b705/docs/validation/sensor_convolution.md</a>.
</div>
<div id="ref-si_frantz2019" class="csl-entry" role="listitem">
Frantz, David. 2019. <span>“<span class="nocase">FORCE—Landsat +
Sentinel-2 Analysis Ready Data and Beyond</span>.”</span> <em>Remote
Sensing</em> 11 (9): 1124. <a
href="https://doi.org/10.3390/rs11091124">https://doi.org/10.3390/rs11091124</a>.
</div>
<div id="ref-si_goble2020" class="csl-entry" role="listitem">
Goble, Carole, Sarah Cohen-Boulakia, Stian Soiland-Reyes, Daniel Garijo,
Yolanda Gil, Michael R. Crusoe, Kristian Peters, and Daniel Schober.
2020. <span>“<span>FAIR Computational Workflows</span>.”</span> <em>Data
Intelligence</em> 2 (1-2): 108–21. <a
href="https://doi.org/10.1162/dint_a_00033">https://doi.org/10.1162/dint_a_00033</a>.
</div>
<div id="ref-si_goetz1985" class="csl-entry" role="listitem">
Goetz, Alexander F. H., Gregg Vane, Jerry E. Solomon, and Barrett N.
Rock. 1985. <span>“<span class="nocase">Imaging Spectrometry for Earth
Remote Sensing</span>.”</span> <em>Science</em> 228 (4704): 1147–53. <a
href="https://doi.org/10.1126/science.228.4704.1147">https://doi.org/10.1126/science.228.4704.1147</a>.
</div>
<div id="ref-si_huang2002" class="csl-entry" role="listitem">
Huang, Chengquan, John R. G. Townshend, Shunlin Liang, Satya N. V.
Kalluri, and Ruth S. DeFries. 2002. <span>“<span class="nocase">Impact
of sensor’s point spread function on land cover characterization:
assessment and deconvolution</span>.”</span> <em>Remote Sensing of
Environment</em> 80 (2): 203–12. <a
href="https://doi.org/10.1016/S0034-4257(01)00298-X">https://doi.org/10.1016/S0034-4257(01)00298-X</a>.
</div>
<div id="ref-si_hurlbert1984" class="csl-entry" role="listitem">
Hurlbert, Stuart H. 1984. <span>“<span class="nocase">Pseudoreplication
and the Design of Ecological Field Experiments</span>.”</span>
<em>Ecological Monographs</em> 54 (2): 187–211. <a
href="https://doi.org/10.2307/1942661">https://doi.org/10.2307/1942661</a>.
</div>
<div id="ref-si_jakimow2023" class="csl-entry" role="listitem">
Jakimow, Benjamin, Andreas Janz, Fabian Thiel, Akpona Okujeni, Patrick
Hostert, and Sebastian van der Linden. 2023. <span>“<span
class="nocase">EnMAP-Box: Imaging spectroscopy in QGIS</span>.”</span>
<em>SoftwareX</em> 23: 101507. <a
href="https://doi.org/10.1016/j.softx.2023.101507">https://doi.org/10.1016/j.softx.2023.101507</a>.
</div>
<div id="ref-si_ju2025" class="csl-entry" role="listitem">
Ju, Junchang, Qiang Zhou, Brian Freitag, David P. Roy, Hankui K. Zhang,
Madhu Sridhar, John Mandel, et al. 2025. <span>“<span class="nocase">The
Harmonized Landsat and Sentinel-2 version 2.0 surface reflectance
dataset</span>.”</span> <em>Remote Sensing of Environment</em> 324:
114723. <a
href="https://doi.org/10.1016/j.rse.2025.114723">https://doi.org/10.1016/j.rse.2025.114723</a>.
</div>
<div id="ref-si_kampe2010" class="csl-entry" role="listitem">
Kampe, Thomas U., Brian R. Johnson, Michele A. Kuester, and Michael
Keller. 2010. <span>“<span class="nocase">NEON: the first
continental-scale ecological observatory with airborne remote sensing of
vegetation canopy biochemistry and structure</span>.”</span> <em>Journal
of Applied Remote Sensing</em> 4 (01): 1–24. <a
href="https://doi.org/10.1117/1.3361375">https://doi.org/10.1117/1.3361375</a>.
</div>
<div id="ref-si_kanewala2014" class="csl-entry" role="listitem">
Kanewala, Upulee, and James M. Bieman. 2014. <span>“<span
class="nocase">Testing scientific software: A systematic literature
review</span>.”</span> <em>Information and Software Technology</em> 56
(10): 1219–32. <a
href="https://doi.org/10.1016/j.infsof.2014.05.006">https://doi.org/10.1016/j.infsof.2014.05.006</a>.
</div>
<div id="ref-si_killough2018" class="csl-entry" role="listitem">
Killough, Brian. 2018. <span>“<span class="nocase">Overview of the Open
Data Cube Initiative</span>.”</span> <em>2018 IEEE International
Geoscience and Remote Sensing Symposium, Pp. 8629–8632. Doi: 10 .</em>
1109: / IGARSS. <a
href="https://doi.org/10.1109/IGARSS.2018.8517694">https://doi.org/10.1109/IGARSS.2018.8517694</a>.
</div>
<div id="ref-si_koontz2022" class="csl-entry" role="listitem">
Koontz, Michael J., Victoria M. Scholl, Anna I. Spiers, Megan E. Cattau,
John Adler, Joseph McGlinchy, Tristan Goulden, Brett A. Melbourne, and
Jennifer K. Balch. 2022. <span>“<span class="nocase">Democratizing
macroecology: Integrating unoccupied aerial systems with the National
Ecological Observatory Network</span>.”</span> <em>Ecosphere</em> 13
(8): e4206. <a
href="https://doi.org/10.1002/ecs2.4206">https://doi.org/10.1002/ecs2.4206</a>.
</div>
<div id="ref-si_koster2012" class="csl-entry" role="listitem">
Köster, Johannes, and Sven Rahmann. 2012. <span>“<span
class="nocase">Snakemake—a scalable bioinformatics workflow
engine</span>.”</span> <em>Bioinformatics</em> 28 (19): 2520–22. <a
href="https://doi.org/10.1093/bioinformatics/bts480">https://doi.org/10.1093/bioinformatics/bts480</a>.
</div>
<div id="ref-si_li1992" class="csl-entry" role="listitem">
Li, X., and A. H. Strahler. 1992. <span>“<span
class="nocase">Geometric-optical bidirectional reflectance modeling of
the discrete crown vegetation canopy: effect of crown shape and mutual
shadowing</span>.”</span> <em>IEEE Transactions on Geoscience and Remote
Sensing</em> 30 (2): 276–92. <a
href="https://doi.org/10.1109/36.134078">https://doi.org/10.1109/36.134078</a>.
</div>
<div id="ref-si_lunch2026" class="csl-entry" role="listitem">
Lunch, Claire, NEON (National Ecological Observatory Network), Christine
Laney, Nathan Mietkiewicz, Eric Sokol, and Kaelin Cawley. 2026.
<span>“<span class="nocase">neonUtilities: Utilities for Working with
NEON Data</span>.”</span> The R Foundation. <a
href="https://doi.org/10.32614/CRAN.package.neonUtilities">https://doi.org/10.32614/CRAN.package.neonUtilities</a>.
<p class="si-reference-note">Source note: R package version 4.0.1</p></div>
<div id="ref-si_mamaghani2019" class="csl-entry" role="listitem">
Mamaghani, Baabak, and Carl Salvaggio. 2019. <span>“<span
class="nocase">Multispectral Sensor Calibration and Characterization for
sUAS Remote Sensing</span>.”</span> <em>Sensors</em> 19 (20): 4453. <a
href="https://doi.org/10.3390/s19204453">https://doi.org/10.3390/s19204453</a>.
</div>
<div id="ref-si_bland1986" class="csl-entry" role="listitem">
Martin Bland, J., and DouglasG. Altman. 1986. <span>“<span>STATISTICAL
METHODS FOR ASSESSING AGREEMENT BETWEEN TWO METHODS OF CLINICAL
MEASUREMENT</span>.”</span> <em>The Lancet</em> 327 (8476): 307–10. <a
href="https://doi.org/10.1016/S0140-6736(86)90837-8">https://doi.org/10.1016/S0140-6736(86)90837-8</a>.
</div>
<div id="ref-si_meyer2021" class="csl-entry" role="listitem">
Meyer, Hanna, and Edzer Pebesma. 2021. <span>“<span
class="nocase">Predicting into unknown space? Estimating the area of
applicability of spatial prediction models</span>.”</span> <em>Methods
in Ecology and Evolution</em> 12 (9): 1620–33. <a
href="https://doi.org/10.1111/2041-210X.13650">https://doi.org/10.1111/2041-210X.13650</a>.
</div>
<div id="ref-si_morisette2006" class="csl-entry" role="listitem">
Morisette, J. T., F. Baret, J. L. Privette, R. B. Myneni, J. E.
Nickeson, S. Garrigues, N. V. Shabanov, et al. 2006. <span>“<span
class="nocase">Validation of global moderate-resolution LAI products: a
framework proposed within the CEOS land product validation
subgroup</span>.”</span> <em>IEEE Transactions on Geoscience and Remote
Sensing</em> 44 (7): 1804–17. <a
href="https://doi.org/10.1109/TGRS.2006.872529">https://doi.org/10.1109/TGRS.2006.872529</a>.
</div>
<div id="ref-si_nationalecologicalobservatorynetwork2026"
class="csl-entry" role="listitem">
National Ecological Observatory Network. 2026. <span>“<span
class="nocase">Spectrometer orthorectified surface directional
reflectance - flightline (DP1.30006.001)</span>.”</span> National
Ecological Observatory Network (NEON). <a
href="https://doi.org/10.48443/jhbd-n155">https://doi.org/10.48443/jhbd-n155</a>.
<p class="si-reference-note">Source note: Data product DP1.30006.001. Accessed 4 September 2026</p></div>
<div id="ref-si_origo2025" class="csl-entry" role="listitem">
Origo, Niall et al. 2025. <span>“<span class="nocase">Good Practice
Guidelines for UAV-Based Surface Reflectance Validation</span>.”</span>
<a
href="https://ceos.org/document_management/Working_Groups/WGCV/GPG_UAV_SR_CEOS_version1.pdf">https://ceos.org/document_management/Working_Groups/WGCV/GPG_UAV_SR_CEOS_version1.pdf</a>.
<p class="si-reference-note">Source note: Tech. rep. Version 1. Version 1; official CEOS-hosted guideline; report author list is abbreviated here. Committee on Earth Observation Satellites Working Group on Calibration and Validation.</p></div>
<div id="ref-si_origo2020" class="csl-entry" role="listitem">
Origo, Niall, Javier Gorroño, James Ryder, Joanne Nightingale, and
Agnieszka Bialek. 2020. <span>“<span class="nocase">Fiducial Reference
Measurements for validation of Sentinel-2 and Proba-V surface
reflectance products</span>.”</span> <em>Remote Sensing of
Environment</em> 241: 111690. <a
href="https://doi.org/10.1016/j.rse.2020.111690">https://doi.org/10.1016/j.rse.2020.111690</a>.
</div>
<div id="ref-si_pangeocommunity2026" class="csl-entry" role="listitem">
Pangeo Community. 2026. <span>“<span class="nocase">Pangeo: A community
for open, reproducible, scalable geoscience</span>.”</span> <a
href="https://pangeo.io/">https://pangeo.io/</a>.
</div>
<div id="ref-si_plaza2009" class="csl-entry" role="listitem">
Plaza, Antonio, Jon Atli Benediktsson, Joseph W. Boardman, Jason
Brazile, Lorenzo Bruzzone, Gustavo Camps-Valls, Jocelyn Chanussot, et
al. 2009. <span>“<span class="nocase">Recent advances in techniques for
hyperspectral image processing</span>.”</span> <em>Remote Sensing of
Environment</em> 113: S110–22. <a
href="https://doi.org/10.1016/j.rse.2007.07.028">https://doi.org/10.1016/j.rse.2007.07.028</a>.
</div>
<div id="ref-si_queally2022" class="csl-entry" role="listitem">
Queally, Natalie, Zhiwei Ye, Ting Zheng, Adam Chlus, Fabian Schneider,
Ryan P. Pavlick, and Philip A. Townsend. 2022. <span>“<span
class="nocase">FlexBRDF: A Flexible BRDF Correction for Grouped
Processing of Airborne Imaging Spectroscopy Flightlines</span>.”</span>
<em>Journal of Geophysical Research: Biogeosciences</em> 127 (1):
e2021JG006622. <a
href="https://doi.org/10.1029/2021JG006622">https://doi.org/10.1029/2021JG006622</a>.
</div>
<div id="ref-si_roberts2017" class="csl-entry" role="listitem">
Roberts, David R., Volker Bahn, Simone Ciuti, Mark S. Boyce, Jane Elith,
Gurutzeta Guillera‐Arroita, Severin Hauenstein, et al. 2017.
<span>“<span class="nocase">Cross‐validation strategies for data with
temporal, spatial, hierarchical, or phylogenetic
structure</span>.”</span> <em>Ecography</em> 40 (8): 913–29. <a
href="https://doi.org/10.1111/ecog.02881">https://doi.org/10.1111/ecog.02881</a>.
</div>
<div id="ref-si_ross1981" class="csl-entry" role="listitem">
Ross, Juhan. 1981. <em><span class="nocase">The radiation regime and
architecture of plant stands</span></em>. Springer Netherlands. <a
href="https://doi.org/10.1007/978-94-009-8647-3">https://doi.org/10.1007/978-94-009-8647-3</a>.
</div>
<div id="ref-si_roujean1992" class="csl-entry" role="listitem">
Roujean, Jean‐Louis, Marc Leroy, and Pierre‐Yves Deschamps. 1992.
<span>“<span class="nocase">A bidirectional reflectance model of the
Earth’s surface for the correction of remote sensing
data</span>.”</span> <em>Journal of Geophysical Research:
Atmospheres</em> 97 (D18): 20455–68. <a
href="https://doi.org/10.1029/92JD01411">https://doi.org/10.1029/92JD01411</a>.
</div>
<div id="ref-si_roy2016" class="csl-entry" role="listitem">
Roy, D. P., V. Kovalskyy, H. K. Zhang, E. F. Vermote, L. Yan, S. S.
Kumar, and A. Egorov. 2016. <span>“<span class="nocase">Characterization
of Landsat-7 to Landsat-8 reflective wavelength and normalized
difference vegetation index continuity</span>.”</span> <em>Remote
Sensing of Environment</em> 185: 57–70. <a
href="https://doi.org/10.1016/j.rse.2015.12.024">https://doi.org/10.1016/j.rse.2015.12.024</a>.
</div>
<div id="ref-si_sandve2013" class="csl-entry" role="listitem">
Sandve, Geir Kjetil, Anton Nekrutenko, James Taylor, and Eivind Hovig.
2013. <span>“<span class="nocase">Ten Simple Rules for Reproducible
Computational Research</span>.”</span> <em>PLoS Computational
Biology</em> 9 (10): e1003285. <a
href="https://doi.org/10.1371/journal.pcbi.1003285">https://doi.org/10.1371/journal.pcbi.1003285</a>.
</div>
<div id="ref-si_saunier2022" class="csl-entry" role="listitem">
Saunier, Sébastien, Bringfried Pflug, Italo Lobos, Belen Franch, Jérôme
Louis, Raquel De Los Reyes, Vincent Debaecker, et al. 2022. <span>“<span
class="nocase">Sen2Like: Paving the Way towards Harmonization and Fusion
of Optical Data</span>.”</span> <em>Remote Sensing</em> 14 (16): 3855.
<a
href="https://doi.org/10.3390/rs14163855">https://doi.org/10.3390/rs14163855</a>.
</div>
<div id="ref-si_schaaf2002" class="csl-entry" role="listitem">
Schaaf, Crystal B, Feng Gao, Alan H Strahler, Wolfgang Lucht, Xiaowen
Li, Trevor Tsang, Nicholas C Strugnell, et al. 2002. <span>“<span
class="nocase">First operational BRDF, albedo nadir reflectance products
from MODIS</span>.”</span> <em>Remote Sensing of Environment</em> 83
(1-2): 135–48. <a
href="https://doi.org/10.1016/S0034-4257(02)00091-3">https://doi.org/10.1016/S0034-4257(02)00091-3</a>.
</div>
<div id="ref-si_schneiderzapp2019" class="csl-entry" role="listitem">
Schneider-Zapp, Klaus, Manuel Cubero-Castan, Dai Shi, and Christoph
Strecha. 2019. <span>“<span class="nocase">A new method to determine
multi-angular reflectance factor from lightweight multispectral cameras
with sky sensor in a target-less workflow applicable to
UAV</span>.”</span> <em>Remote Sensing of Environment</em> 229: 60–68.
<a
href="https://doi.org/10.1016/j.rse.2019.04.007">https://doi.org/10.1016/j.rse.2019.04.007</a>.
</div>
<div id="ref-si_smith2016" class="csl-entry" role="listitem">
Smith, Arfon M., Daniel S. Katz, Kyle E. Niemeyer, and FORCE11 Software
Citation Working Group. 2016. <span>“<span class="nocase">Software
citation principles</span>.”</span> <em>PeerJ Computer Science</em> 2:
e86. <a
href="https://doi.org/10.7717/peerj-cs.86">https://doi.org/10.7717/peerj-cs.86</a>.
</div>
<div id="ref-si_soenen2005" class="csl-entry" role="listitem">
Soenen, S. A., D. R. Peddle, and C. A. Coburn. 2005. <span>“<span
class="nocase">SCS+C: a modified Sun-canopy-sensor topographic
correction in forested terrain</span>.”</span> <em>IEEE Transactions on
Geoscience and Remote Sensing</em> 43 (9): 2148–59. <a
href="https://doi.org/10.1109/TGRS.2005.852480">https://doi.org/10.1109/TGRS.2005.852480</a>.
</div>
<div id="ref-si_soilandreyes2022" class="csl-entry" role="listitem">
Soiland-Reyes, Stian, Peter Sefton, Mercè Crosas, Leyla Jael Castro,
Frederik Coppens, José M. Fernández, Daniel Garijo, et al. 2022.
<span>“<span class="nocase">Packaging research artefacts with
RO-Crate</span>.”</span> <em>Data Science</em> 5 (2): 97–138. <a
href="https://doi.org/10.3233/DS-210053">https://doi.org/10.3233/DS-210053</a>.
</div>
<div id="ref-si_spectralbridgebulkevidencebundle2026" class="csl-entry"
role="listitem">
SpectralBridge bulk evidence bundle. 2026. <span>“<span
class="nocase">SpectralBridge bulk results visual report and numerical
exports</span>.”</span>
<p class="si-reference-note">Source note: Author-supplied local evidence bundle. Report and CSV exports reviewed 9 September 2026. Primary filenames, analysis identifier, and SHA-256 checksums are recorded in the supplement. No permanent public identifier was supplied</p></div>
<div id="ref-si_spectralbridgeprojectteam2026" class="csl-entry"
role="listitem">
SpectralBridge project team. 2026. <span>“<span class="nocase">2023–2024
drone campaign production inventory</span>.”</span>
<p class="si-reference-note">Source note: Author-supplied production inventory. Reviewed 18 September 2026. Records 43 staged working HDF5 observations, approximately 7.15 GB of output, QA and JSON artifacts, absent ENVI and Parquet products, and orchestration status of 43 processed and zero failed. Exact production revision, manifest, checksums, resolved configuration, root cause, and corrective revision were not supplied</p></div>
<div id="ref-si_teillet1997" class="csl-entry" role="listitem">
Teillet, P. 1997. <span>“<span class="nocase">Effects of spectral,
spatial, and radiometric characteristics on remote sensing vegetation
indices of forested regions</span>.”</span> <em>Remote Sensing of
Environment</em> 61 (1): 139–49. <a
href="https://doi.org/10.1016/S0034-4257(96)00248-9">https://doi.org/10.1016/S0034-4257(96)00248-9</a>.
</div>
<div id="ref-si_thompson2018" class="csl-entry" role="listitem">
Thompson, David R., Vijay Natraj, Robert O. Green, Mark C. Helmlinger,
Bo-Cai Gao, and Michael L. Eastwood. 2018. <span>“<span
class="nocase">Optimal estimation for imaging spectrometer atmospheric
correction</span>.”</span> <em>Remote Sensing of Environment</em> 216:
355–73. <a
href="https://doi.org/10.1016/j.rse.2018.07.003">https://doi.org/10.1016/j.rse.2018.07.003</a>.
</div>
<div id="ref-si_usgeologicalsurvey2026" class="csl-entry"
role="listitem">
U.S. Geological Survey. 2026. <span>“<span>Landsat 8–9 Collection 2
Level-2 Science Product Guide</span>.”</span> <a
href="https://www.usgs.gov/media/files/landsat-8-9-collection-2-level-2-science-product-guide">https://www.usgs.gov/media/files/landsat-8-9-collection-2-level-2-science-product-guide</a>.
<p class="si-reference-note">Source note: U.S. Geological Survey product documentation. Accessed 25 September 2026.</p></div>
<div id="ref-si_wang2015" class="csl-entry" role="listitem">
Wang, Chuyuan, and Soe W. Myint. 2015. <span>“<span class="nocase">A
Simplified Empirical Line Method of Radiometric Calibration for Small
Unmanned Aircraft Systems-Based Remote Sensing</span>.”</span> <em>IEEE
Journal of Selected Topics in Applied Earth Observations and Remote
Sensing</em> 8 (5): 1876–85. <a
href="https://doi.org/10.1109/JSTARS.2015.2422716">https://doi.org/10.1109/JSTARS.2015.2422716</a>.
</div>
<div id="ref-si_wanner1995" class="csl-entry" role="listitem">
Wanner, W., X. Li, and A. H. Strahler. 1995. <span>“<span
class="nocase">On the derivation of kernels for kernel‐driven models of
bidirectional reflectance</span>.”</span> <em>Journal of Geophysical
Research: Atmospheres</em> 100 (D10): 21077–89. <a
href="https://doi.org/10.1029/95JD02371">https://doi.org/10.1029/95JD02371</a>.
</div>
<div id="ref-si_wilson2017" class="csl-entry" role="listitem">
Wilson, Greg, Jennifer Bryan, Karen Cranston, Justin Kitzes, Lex
Nederbragt, and Tracy K. Teal. 2017. <span>“<span class="nocase">Good
enough practices in scientific computing</span>.”</span> <em>PLOS
Computational Biology</em> 13 (6): e1005510. <a
href="https://doi.org/10.1371/journal.pcbi.1005510">https://doi.org/10.1371/journal.pcbi.1005510</a>.
</div>
<div id="ref-si_woodcock1987" class="csl-entry" role="listitem">
Woodcock, Curtis E., and Alan H. Strahler. 1987. <span>“<span
class="nocase">The factor of scale in remote sensing</span>.”</span>
<em>Remote Sensing of Environment</em> 21 (3): 311–32. <a
href="https://doi.org/10.1016/0034-4257(87)90015-0">https://doi.org/10.1016/0034-4257(87)90015-0</a>.
</div>
<div id="ref-si_wulder2022" class="csl-entry" role="listitem">
Wulder, Michael A., David P. Roy, Volker C. Radeloff, Thomas R.
Loveland, Martha C. Anderson, David M. Johnson, Sean Healey, et al.
2022. <span>“<span class="nocase">Fifty years of Landsat science and
impacts</span>.”</span> <em>Remote Sensing of Environment</em> 280:
113195. <a
href="https://doi.org/10.1016/j.rse.2022.113195">https://doi.org/10.1016/j.rse.2022.113195</a>.
</div>
</div>
</div>
