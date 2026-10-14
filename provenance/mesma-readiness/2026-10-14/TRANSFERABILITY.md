# Grouped generalization

| scheme | kind | sensor | median_fraction_RMSE | p25_fraction_RMSE | p75_fraction_RMSE | folds |
| --- | --- | --- | --- | --- | --- | --- |
| inferred_pft | flight | NEON | 0.409 | 0.335 | 0.501 | 103 |
| inferred_pft | flight | OLI | 0.400 | 0.327 | 0.501 | 103 |
| inferred_pft | plant | NEON | 0.345 | 0.322 | 0.363 | 3 |
| inferred_pft | plant | OLI | 0.353 | 0.310 | 0.400 | 3 |
| inferred_pft | site | NEON | 0.366 | 0.335 | 0.400 | 3 |
| inferred_pft | site | OLI | 0.345 | 0.297 | 0.400 | 3 |
| inferred_pft | within_site_year | NEON | 0.493 | 0.385 | 0.504 | 1 |
| inferred_pft | within_site_year | OLI | 0.459 | 0.360 | 0.473 | 1 |
| inferred_pft | year | NEON | 0.388 | 0.339 | 0.461 | 2 |
| inferred_pft | year | OLI | 0.358 | 0.329 | 0.426 | 2 |
| material | flight | NEON | 0.330 | 0.286 | 0.384 | 115 |
| material | flight | OLI | 0.330 | 0.287 | 0.384 | 115 |
| material | plant | NEON | 0.276 | 0.257 | 0.288 | 3 |
| material | plant | OLI | 0.277 | 0.260 | 0.288 | 3 |
| material | site | NEON | 0.292 | 0.276 | 0.298 | 3 |
| material | site | OLI | 0.286 | 0.273 | 0.310 | 3 |
| material | within_site_year | NEON | 0.280 | 0.263 | 0.284 | 1 |
| material | within_site_year | OLI | 0.278 | 0.244 | 0.299 | 1 |
| material | year | NEON | 0.292 | 0.268 | 0.310 | 2 |
| material | year | OLI | 0.288 | 0.270 | 0.319 | 2 |
| researcher | flight | NEON | 0.363 | 0.310 | 0.417 | 115 |
| researcher | flight | OLI | 0.370 | 0.313 | 0.427 | 115 |
| researcher | plant | NEON | 0.344 | 0.319 | 0.391 | 3 |
| researcher | plant | OLI | 0.346 | 0.320 | 0.405 | 3 |
| researcher | site | NEON | 0.361 | 0.304 | 0.388 | 3 |
| researcher | site | OLI | 0.373 | 0.342 | 0.418 | 3 |
| researcher | within_site_year | NEON | 0.347 | 0.334 | 0.364 | 1 |
| researcher | within_site_year | OLI | 0.353 | 0.343 | 0.377 | 1 |
| researcher | year | NEON | 0.373 | 0.332 | 0.453 | 2 |
| researcher | year | OLI | 0.375 | 0.339 | 0.471 | 2 |

Three class/site-stratified plant folds; every available leave-one-site, leave-one-year and within-NIWO year direction; and all available actual-flight holdouts were considered. Exact class/fold support, omitted classes and source memberships are in fold_support.csv/fold_membership.parquet. Candidate selection is repeated INSIDE training. Every test GlobalID, across all years and flights, is excluded from training. Flight tests use actual flight-specific spectra, never all-flight annual medians. Unsupported directions are not turned into estimates.

Some repeated NIWO years cannot provide a reverse-direction training set once every held-out identity is removed. This is a sampling-structure limit, not a failure of the optimizer. Year transfer therefore concerns new identities as well as dates. Flight/site folds overlap in their source plants; their errors are correlated, not independent ecological replicates. Sample sizes and class sets vary with support. Differences between the displayed holdout summaries cannot isolate a pure geographic or temporal penalty. Within-site plant folds do not impose a spatial buffer or independent-plot split; nearby or overlapping annotations can remain correlated. GlobalIDs denote disjoint records, not proof of independent organisms or genotypes. Species remain nested/confounded in PFTs; no species-independent functional mechanism or held-out-species generalization is inferred.
