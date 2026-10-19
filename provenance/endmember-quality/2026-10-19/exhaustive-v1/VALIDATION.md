# Validation record

- 23 targeted tests passed: streaming exhaustive kernel, existing mixture
  routines and preceding selected-endmember contracts. Streaming checks cover
  three batch sizes, independent direct-affine enumeration, pure/boundary/
  degenerate targets, lower-dimensional ties, checkpoint reuse, partial restart
  and configuration/input mismatch rejection.
- Twelve prespecified pilot targets include one pure, one pair and one equal-third
  triple in each of four observed site/year cells. Pilot search took 22.14 s.
- Full 360-target search evaluated all 16,918,447 discrete candidates per target,
  taking 364.32 s of numerical search (6,090,640,920 target–model evaluations).
  All 25 composition checkpoints completed. `full_summary.json` and saved model
  counts establish completion. The optional macOS `/usr/bin/time -l` wrapper
  returned exit 1 after the successful Python run because `sysctl kern.clockrate`
  is unavailable in the sandbox; peak-memory counters were therefore not claimed.
  Timing inside the Python search is recorded independently.
- Reconstructed all 360 targets' winning predictions from original supplied
  reference spectra, stored indices and fractions. Verified nonnegative sum-one
  fractions, at most three distinct categories and independent class aggregation.
- Independently checked every winning model's affine solution with direct
  seven-band least squares and constrained SLSQP optimization. The first unscaled
  finite-difference SLSQP check stopped too early for tiny residuals; validation
  now uses an analytic gradient and scales the optimizer objective by 10,000
  (not the input spectra). Objective errors agree to absolute MSE 1e-12;
  direct-affine weights agree within 1e-7. This adjustment changed no search
  results, spectra, fractions or model-selection rules.
- Independently enumerated every full-library candidate for prespecified target
  30 using direct seven-band differences, separate generic linear solves and
  direct reconstruction residuals. Its minimum MSE is 1.509065887336997e-8 and
  agrees with the Gram-based streaming search to absolute MSE 1e-13.
- All 12 pilot minima/fractions agree with the full target-batched run. Reusing
  full checkpoints reproduces fractions exactly without rewriting checkpoints.
- Full-search spectral residuals never exceed screened three- or five-reference
  per-category residuals beyond 1e-9 supplied-array units.
- Prior target truths and all supplied input hashes are checked; 53 preceding
  packet files are unchanged (cache directories excluded). Arrays and original
  polygon Parquet were read in place. No previous fit/report was overwritten.
- Scoped Ruff, documentation links and code whitespace checks pass. One earlier
  verbatim prompt's trailing blank is preserved in the prompt log.

The illustrated report describes pooled fraction RMSE and MAE, paired whole-
bundle bootstrap differences, class false detections, parent/site/year limits,
and restricted near-category-set ambiguity. It does not treat synthetic rows as
independent field replicates or present exact search as ecological validation.

All four PNG/SVG figure pairs were visually reviewed. The category legend was
moved below the bars, and generating-component colors were explicitly labelled.
The portable HTML was rendered at 1360-pixel desktop and 390-pixel mobile widths: 
four embedded images loaded, with no horizontal page overflow.
