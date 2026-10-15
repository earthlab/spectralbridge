# Website scientific claims audit

Scope: all Markdown under docs/ searched for calibration, classification,
NBAR, universal/validated-across-sites, mixture readiness and information-loss
language; primary user pages manually reviewed. Retained historical reports are
not rewritten as contemporary application certificates. Full evidence stays in
provenance rather than being duplicated in navigation.

| Claim | Source / evidence level | Status and allowed wording | Wording to avoid |
|---|---|---|---|
| Processes NEON/drone/bulk products | Package orchestration, pipeline tests; level 2 | Separate restart-safe workflows with named outputs and QA | Every run performs empirical sensor calibration |
| Library size/coverage | Publication numerical validation and panel manifest; empirical inventory | Source-specific dated snapshot generated from verified provenance, not package constants | These counts describe every possible library |
| 1,140 columns form one spectrum | Atlas native-grid audit; level 1/2 | Union of three native grids; structural NaNs are absent native coordinates | Zero-fill or globally impute every union column |
| Biological structure exists | PFT/researcher audit; level 3 | Conditional sampled-group whole-spectrum associations | Validated unknown-species classifier; causal PFT mechanism |
| Strong/weak contrasts | Canonical effect_retention.csv and method audit | DBS/ECT and DBT/ECT repeated strong; DBT/ECS unsupported in eligible cohorts | All PFTs are always distinguishable |
| Spectral localization | Canonical family maximum envelopes | Null-envelope excursions; pointwise bootstrap bands separate | Simultaneous effect confidence from pointwise intervals |
| Ecological information survives OLI | Canonical paired 21-comparison experiment; level 4 | 15/16 supported contrasts retained; rank/magnitude structure broadly retained | 82.4% of all ecological information; classification accuracy |
| OLI diagnostic projection | Packaged Gaussian centers/FWHM; tests | Shared-source response diagnostic, after medians | Independent satellite observation or exact measured SRF |
| MicaSense physical transfer | Source coordinate audit | Blocked pending original band-coordinate provenance | Ten physically validated MicaSense bands in this export |
| Agreement with real Landsat | One R10C next-day pilot; level 5 | Scoped QA/footprint-aware radiometric/spectral comparison | Reproduces Landsat everywhere; multisite validation |
| Landsat SR versus NBAR | Pilot STAC/product identity and scaling | Current pilot is Collection 2 Level-2 SR | Treat the supplied NBAR conceptual artwork as validation evidence |
| Correlation versus agreement | Pilot bias/error/identity fits | High correlation can coexist with residual radiometric differences | High R² proves interchangeability |
| Library reflectance scale | Retained library/source audit | Stored units; absolute scaling unresolved | Assume divide-by-10,000 from appearance |
| Class labels/material purity | Source category/subcategory inventory | Species, inferred PFT, researcher cover and physical materials separate | Non-vegetated & dead is a single pure endmember |
| FCLS/MESMA readiness | Constrained-solver tests and held-out synthetic experiments; level 6 partial | Tested experimental diagnostics; independent ecological abundance truth missing | Operational abundance accuracy, universal MESMA readiness |
| Detection/unknowns | Explicit thresholds and adequacy guards | Conditional rates; low residual is unvalidated membership | A fit certifies an unknown belongs to known classes |
| Uncertainty | GlobalID/spatial-block bootstrap and synthetic MC coverage | Conditional intervals; MC uncertainty not calibrated abundance confidence | Universal geographic coverage or precise field detection limit |
| Software publication status | Metadata, CI and release gates | Local checked release candidate; JOSS author/DOI and scientific validation tasks explicit | Published release, accepted JOSS paper or minted DOI without evidence |

## Corrections made

- Pipeline reference now describes reflectance processing/target-band weighting
  rather than empirical calibration for every flight.
- Output guidance asks users to inspect processing diagnostics instead of
  certifying calibration quality from QA alone.
- Home and stage-QA text distinguish retained conceptual NBAR artwork from the
  actual Collection 2 Level-2 SR pilot. Historical run reports remain scoped to
  what those runs evaluated.
- Sensor-harmonization text no longer uses an ambiguous evidence-level number
  from an older framework; it links the new six-level scientific evidence map.
- New scientific pages consistently separate significance, classification,
  identifiability, fraction recovery, synthetic sensors and real observations.

No coefficients, physical scale, taxonomy assignments or SRF definitions were
changed to strengthen a website claim. Only an additive finite/dimension/order
input guard was added to the diagnostic OLI projector; valid-input calculations
remain unchanged. Experimental readiness now explicitly validates training pools
and records adequacy status without promoting low residuals to membership.
