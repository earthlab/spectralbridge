# SpectralBridge 2.3.0rc2

RC2 stabilizes the completed experimental drone engineering scope and the
cross-sensor analysis tools added since the October 13 RC1 preparation. It is a
release candidate, not a certificate of physical reflectance accuracy.

## What changed

- Drone TIFF/HDF5/ENVI grids preserve orientation and corner/center conventions;
  ancillary alignment and restart signatures prevent reuse of incompatible grids.
- Explicit scalar/per-band calibration uses `physical = scale * stored + offset`.
  Alpha, NoData and band minima remain traceable. BRDF eligibility uses decoded
  units, and unknown physical calibration stays blocked.
- Shared RossThick/LiDenseR kernels, rank, prediction uncertainty and application
  checks are versioned. Experimental camera rays and kernel mixtures preserve
  the distinction between inferred and actual image contributors.
- Advanced spatial fitting masks and cluster covariance retain training provenance.
  Conditioned SCS+C distinguishes missing, unsupported and corrected observations,
  retains both stages in combined products and does not cap gains.
- Spectral-library, PFT/sensor-transfer and MESMA diagnostics have expanded evidence
  and documentation. These do not establish universal sensor interchangeability.

## Stabilization in this candidate

Topographic correction preserves valid bands when another wavelength is missing.
Convolved ENVI headers retain the serialized affine calibration as one scalar,
so downstream physical Parquet extraction can validate it. Polygon extraction
uses the canonical package namespace, avoiding import-order-dependent legacy
module bindings. Test/campaign fixtures now declare their known synthetic units
and fit a supported BRDF model rather than supplying unvalidated coefficients.

The API reference includes the new advanced modules. Practical guides distinguish
current conditional capabilities from earlier unsupported zero-view experiments.
The strict website build retains links to immutable research evidence.

## Compatibility and limits

Distribution: `earthlab-spectralbridge`; import: `spectralbridge`. Supported
release checks target Python 3.10-3.12. Existing NEON correction mathematics,
reference geometry and valid-data results remain stable. Historical libraries
with missing units or incompatible BRDF policies need explicit review and are not
silently accepted by the newer scientific contract.

Goldhill DN/32768 calibration, actual contributors and independently validated
directional/ecological performance remain scientific limitations. They are not
unfinished RC2 software fixes. Experimental products remain ineligible for
approved spectral libraries. No further scientific investigation is part of this
release preparation.

Citation author placeholders are retained for maintainer approval; no authors or
ORCIDs are invented. RC2 publication, release-tag creation/push, GitHub release
and merge require separate explicit approval. See the
[release procedure](releasing.md) for exact-artifact gates and publishing steps.
