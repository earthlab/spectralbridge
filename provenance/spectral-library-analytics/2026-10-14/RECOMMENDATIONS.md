# 16 · Is the library ready for MESMA?

Readiness is evaluated by dimension: spectral integrity, ecological distinction, plant recognition, domain transfer, endmember uniqueness, fraction recovery, unknown rejection, uncertainty calibration and operational validation. No arbitrary composite readiness score is calculated.

Conditional uses include sampled-library characterization, matched group contrasts, controlled synthetic sensor-response comparisons and held-out closed-set recognition in explicitly evaluated domains.

Operational fractions are NOT READY or have INSUFFICIENT EVIDENCE. The reasons are traceable: unknown library scale/purity, ecological labels that are not pure physical materials, ambiguity under convex mixtures, substantial synthetic fraction error, weak unknown rejection and absent independent abundance truth.

“Green vegetation,” “Non-vegetated & dead,” woody shrubs and dead-material proxies must not be silently treated as pure endmembers for water, soil, snow, shade or species abundance. A missing physical material remains missing, even if an ecological classifier performs well.

Every class × dimension decision links to the exact supporting master table and limitation. Human review should apply the intended ecological error tolerance and deployment domain before approving any narrower application.

Evidence: readiness_matrix.csv; MATERIAL_CLASS_AUDIT.md; RECOMMENDATIONS.md

# 17 · The three most valuable new datasets

First: co-located, independently measured fractional cover and endmember purity. Measure actual green, senescent/dead, soil/mineral, water and shade fractions at the relevant footprint, with repeat observers or uncertainty estimates. Include small positive fractions and true absences. This directly tests inversion, false detection and interval coverage.

Second: a balanced repeated site × year × species/PFT panel with persistent plant identities, native wavelength metadata, units, acquisition geometry and physiological/environmental measurements. Prioritize currently rare or geographically restricted classes. This separates ecological variability from domain structure and supports stronger transfer claims.

Third: matched independent NEON, Landsat and verified drone acquisitions across sites/seasons, with tight timing, documented QA, spatial footprints and scale. This tests real sensor/domain shift rather than only convolution of one reference.

Analysis priorities after collection: freeze deployment questions and error tolerances; repeat the same grouped evaluation; assess class-specific physical unknown rejection and fraction uncertainty against independent truth; only then consider more complex representations if they solve a documented failure.

The current negative results change the description of SpectralBridge: it is a reproducible translation and scientific diagnostic system with demonstrated conditional ecological signal, not a universally calibrated sensor or validated ecological abundance engine.

Evidence: RECOMMENDATIONS.md; LIMITATIONS.md; readiness_matrix.csv
