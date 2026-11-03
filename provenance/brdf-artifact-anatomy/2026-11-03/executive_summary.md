# Anatomy of a Red Artifact

## How Missing Viewing Geometry and an Unsupported BRDF Model Corrupted the Goldhill Drone Orthomosaic

2026-11-03 · Read-only scientific reconstruction · SpectralBridge P165

The red artifact was generated downstream by the historical BRDF correction. It is absent from the source and reproduced exactly using the unchanged saved model.

- Adjacent 10 cm pixels jump from factor 1 to 11,742,750 when the 650 nm predicted denominator changes from zero to 0.0078125. The reference prediction is 91,740.234375.

- All 2,933 main-streak native edges match the denominator-sign transition exactly. Four separate edges surround one NDVI-bin exception cell.

- All three drone flights have corrected-kernel rank 1/3 and zero supported band fits. Millions of pixels do not replace missing directional observations.

- The source view maps are zero placeholders; the solar grids are derived at an unverified time. Historical red fitting used only 14 eligible normalized pixels and ignored deficient rank.

- 650 and 717 nm are corrupted, but the generic 668/560/475 RGB omits both. A clean RGB preview does not validate the data.

- The same Deciduous polygon's median spectrum rotates 84.72°; its 650-based NDVI changes from 0.8444 to nearly −1. Smaller within-polygon spread can accompany worse spectra.

- Topographic SCS+C has a separate denominator-cancellation problem, reaching factor 356.55 at 531 nm. It remains unapproved.

- Current unsupported-fit rejection prevents this historical failure. Scientifically valid correction still requires verified calibration, real geometry/timing or independent applicable validation. No production data or algorithms were changed.

[Full report](report.md) · [PDF](anatomy_of_a_red_artifact.pdf) · [Reproducibility](reproducibility.md)
