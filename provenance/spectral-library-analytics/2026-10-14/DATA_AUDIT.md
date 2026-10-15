# Data/QC and canonical index

Original Parquet SHA256: `cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978`. It is verified and read in place. No original pixel copy or pixel cache is created. The canonical metadata/reference index has no wavelength matrix; it retains keys, site/year/labels, compact references, native grids, full source/acquisition history and quality counts.

Upstream paired ownership is verified before use. Three native grids yield common finite NEON support without interpolation across atmospheric gaps. OLI physical responses are verified; MicaSense fallback/padded coordinates remain blocked for physical sensor claims.

Finite negatives remain valid. Stored units are unresolved: no guessed division or empirically scaled Landsat residual is applied. Full-spectrum zero norms are explicitly masked. Selected coordinates can have zero norm despite a nonzero full spectrum; angles are undefined there, with valid PCA/distance diagnostics retained.

Index: artifacts/plant_spectral_atlas/analytics/canonical_analysis_index.parquet. Exact counts: tables/library_summary.csv. Support failures and absent-training/open-set cases: tables/fold_support.csv. Original/compact hashes protect immutable data; display bounds do not alter analysis.
