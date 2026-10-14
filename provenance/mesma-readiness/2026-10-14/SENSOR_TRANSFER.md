# Paired spectral reduction versus real-sensor validation

The same held-out source identities, fraction vectors, candidate proposal pools and NEON-selected endmember IDs are used in both representations. Corrected NEON uses the inherited disconnected wavelength quadrature; OLI uses seven equally weighted verified synthetic channels. No per-spectrum brightness normalization is used. Relative RMSE normalization uses one training-only NEON scalar for BOTH sensors. Differences therefore include the declared spectral metric as well as representation loss; no literal information-retention percentage is claimed.

| scheme | sensor | fraction_RMSE | fraction_MAE | reconstruction_RMSE |
| --- | --- | --- | --- | --- |
| inferred_pft | NEON | 0.344 | 0.215 | 0.121 |
| inferred_pft | OLI | 0.351 | 0.222 | 0.089 |
| material | NEON | 0.292 | 0.166 | 0.112 |
| material | OLI | 0.291 | 0.165 | 0.091 |
| researcher | NEON | 0.380 | 0.255 | 0.274 |
| researcher | OLI | 0.380 | 0.252 | 0.201 |

Previous P120 retention of 15/16 NEON-supported inferred-PFT contrasts concerned sampled-group spectral differences. It does not contradict poor fraction recovery or establish abundance information retention. Here the paired sensor_comparison.csv directly records OLI-minus-NEON fraction RMSE within exact fold/class/method pairs.

P121 compares one real R10C next-day Landsat observation: pooled undarkened SR RMSE 0.01477, angle 2.089 degrees, mixed brightness effects and conditional legacy UTC timing. It is not cross-site validation, noise truth, endmember purity or fraction validation. Library scales are unverified, so adding 0.01477 reflectance Gaussian noise to stored library values would be indefensible. Actual Landsat fractions remain unvalidated.

The required four-way native/30 m spatial/spectral experiment cannot be completed for library sites from sparse polygon extractions. No full NIWO/WREF/YELL rasters and independent fractional maps were available. P121's correctly aggregated R10C image supports a different pixel-support diagnostic but not ecological fraction truth. Spatial mixing and spectral reduction must not be conflated; the present recovery study isolates only representation under its linear synthetic model.
