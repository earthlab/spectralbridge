# Integrated spectral-library analytics: audit before new experiments

Date: 2026-10-14. The active documentation/test integration is being verified;
its new experimental guards and API explanations are prerequisites, not new
scientific evidence. Earlier source/result products will remain immutable.

| Analysis | Implementation / inputs / unit | Existing outputs, tests and provenance | Decision |
|---|---|---|---|
| Library/atlas | plant_spectral_atlas; original polygon Parquet read in place; pixel → polygon/flight → GlobalID/year | Compact native/harmonized plant/flight and 4,807 paired polygon/year curves; atlas tests, publication-figure manifests | Reuse valid compact products and dated empirical counts; do not copy original pixel library |
| Quantiles/regions/years | plant_spectral_quantiles, regions, years, pfts; original identities and acquisitions | 99 fitted percentile curves, matching baselines, source-specific plots; respective tests; provenance/quantile-models/2026-10-13 | Reuse description/limitations; not independent endmembers or established novel-site classifiers |
| Biological differences | plant_pft_statistics, pft_method_audit, researcher_pft_statistics; common-support polygon/year curves and exact history blocks | Audited max/integrated/NPC, energy/FPCA/rank sensitivities; strong/weak contrasts; provenance/{pft-audit,researcher-pft}/2026-10-14 | Reuse canonical inference unchanged, including null-family caveats |
| Sensor resolution | sensor_pft_transfer; same paired curve memberships; NEON 360 support coordinates versus physical seven-band synthetic OLI | 21 inferred and 40 researcher comparisons, effect/rank/direction results; blocked MicaSense coordinates; tests and provenance/sensor-pft-transfer/2026-10-14 | Reuse canonical effects; extend grouped prediction/selected-band experiments only |
| Independent Landsat | landsat_agreement, landsat_flight_validation/report; full R10C source and actual Collection 2 L2 scene, 30 m support | One next-day pair, 3,583 footprints, spatial uncertainty/QA/registration/brightness diagnostics; numerical/transport tests and provenance/real-landsat-validation/2026-10-14 | Reuse pilot; not ecological fraction truth; empirical-residual perturbation only if scale/domain rationale holds |
| Endmembers/unmixing | mixtures, mesma_readiness; training-only candidate pools, globally purged identities, empirical held-out parents | 360 supported tests, fixed/variable libraries, selection, ambiguity, size/shade/MC/detection/transfer diagnostics; independent optimizer and analytic tests; provenance/mesma-readiness/2026-10-14 | Reuse full NEON/OLI results and physical-material audit; selected-band counterpart must preserve exact parents/fractions/folds |
| Publication figures | examples/publication_figures; canonical atlas and evidence | Two four-panel figures, PCA scores/variance, deterministic observed representatives; source/output manifest and independent validator | Reuse verified figures/numerics; no new PCA on the 1,140-column raw union |
| Classical ecological ML | No general grouped logistic/PLS/SVM/RF audit currently implemented | Earlier quantile matching is not the requested supervised generalization ladder | New work required: nested group-aware tuning/selection, calibration, baselines, domain/open-set diagnostics |
| Unknown/calibration | Existing residual/alternate-model/MC diagnostics; new adequacy guard explicitly withholds membership certification | No calibrated geographic prediction guarantee or population abundance limits | New classification calibration/open-set evaluation required; retain synthetic fraction uncertainty failures |

## Source and support

Original SHA256: cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978.
Source has 85,706 pixel records / 3,639 GlobalIDs / 4,807 polygon-years, three
sites and two years. Metadata labels remain separate. Three native 426-band
grids contribute the 1,140-column union; structural NaNs are not missing plants.
Absolute library units and material purity are unresolved. Finite negative
corrected reflectance is not automatically nodata. Physical MicaSense transfer
is blocked; no coordinates will be guessed.

Original and all earlier source/result hashes will be checked. New canonical
index will reference keys/paths and exposure histories, not duplicate raw pixels.
Retain earlier implementation hashes as historical provenance: documentation or
additive validation guards in current code do not retroactively regenerate old
scientific evidence. Every new run records its own current code/data identity.

## Computational/method gates

Start with a controlled small run and measured cost before full grouped fits.
All scaling, component/feature/prototype choices and tuning occur inside training
folds. Keep seed, fold support, absent training classes/open-set cases and failures
explicit. Do not fit neural representations by default. No existing large-data
scientific experiment is rerun just because its code is available.
