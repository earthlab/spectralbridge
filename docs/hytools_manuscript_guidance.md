# HyTools manuscript guidance

## How to describe the relationship

HyTools is important prior software for hyperspectral correction and I/O. The
SpectralBridge paper should distinguish five facts: both projects use published
topographic and BRDF methods; selected SpectralBridge incidence, Ross/Li kernel,
NEON-reader, ENVI-writer, and legacy-resampling code has HyTools implementation
lineage; SpectralBridge adds distinct restart-safe orchestration, sensor
harmonization/translation, drone and bulk workflows, compact statistics,
product contracts, and QA/provenance infrastructure; the supported pipeline no
longer requires HyTools at runtime; and removal of that dependency does not
remove the obligation to credit HyTools.

Do not describe SpectralBridge as containing “no HyTools code” or as an entirely
independent reimplementation. Use “does not require HyTools as a runtime
dependency” for the narrower and accurate engineering claim. Cite the original
scientific literature for SCS+C and Ross/Li methods, and cite HyTools as the
implementation source where the component-level audit records adaptation.

## Suggested Methods/Software paragraph

> SpectralBridge provides restart-safe, file-based workflows for NEON,
> drone, cross-sensor translation, bulk analysis, and quality assessment. Its
> supported pipeline does not require HyTools at runtime, but selected
> correction, NEON HDF5, ENVI, and legacy resampling components were adapted
> from or informed by HyTools and remain explicitly attributed. The SCS+C
> topographic correction follows Soenen et al. (2005), while Ross/Li BRDF
> kernels follow the cited kernel literature; where the HyTools implementation
> informed SpectralBridge's implementation, both the scientific source and
> HyTools are credited. SpectralBridge's distinct contributions include its
> restart-safe artifact contracts, sensor harmonization and empirical
> translation workflows, separate drone and bulk-analysis systems, compact
> hierarchical statistics, and integrated QA and provenance outputs.

Adjust the list of contributions to match the manuscript's actual evaluated
scope. Do not claim algorithmic novelty for standard SCS+C, Ross, Li, NDVI, or
Gaussian-response methods.

## Suggested acknowledgement

> We acknowledge the HyTools developers—Adam Chlus, Zhiwei Ye, Philip
> Townsend, and the other contributors named by the HyTools project—for prior
> hyperspectral processing software and for implementation foundations adapted
> in SpectralBridge.

## Citations to include

- Cite the HyTools software/repository using its preferred citation metadata at
  the version actually discussed in the manuscript.
- Cite Soenen, Peddle, and Coburn (2005), DOI
  `10.1109/TGRS.2005.852480`, for SCS+C.
- Cite Wanner, Li, and Strahler (1995), DOI `10.1029/95JD02371`, and Lucht,
  Schaaf, and Strahler (2000), DOI `10.1109/36.841980`, for the Ross/Li kernel
  family, adding the more specific references appropriate to the exact kernels
  discussed.
- Cite the released SpectralBridge version and archive/DOI used for the paper.

See the repository-root
[HyTools provenance audit](https://github.com/earthlab/spectralbridge/blob/main/HYTOOLS_PROVENANCE.md)
for the audited versions, component classifications, Git-history evidence,
limitations, and packaging status. This guidance is scholarly wording, not a
legal assessment.
