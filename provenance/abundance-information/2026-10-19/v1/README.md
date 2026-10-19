# Stable-stage audit: source-scale gate

**Status: stopped before implementation or new empirical analysis.**
Main baseline `38f646a` (`mesma reports`), package 2.3.0rc1; 19 October 2026.
The checkout was clean when this task began. No release is being prepared or
published by this audit. The requested next stage is **not completed**.

The attached request, section 15, explicitly says:

> Stop and document rather than silently fixing around any of these:
> ... source scaling is unclear.

That condition is present. The canonical researcher-information input record says
`stored spectral units; absolute reflectance scale unresolved`; the subsequent
foundation records `NOT TESTABLE: stored numerical units; absolute reflectance
scale unresolved`. The merged source has **no schema metadata and no scale/unit/
gain/offset columns**. Paired compact products have only pandas schema metadata.
The verified compact generating manifest contains hashes/settings, not an
absolute scale contract. A unit conversion cannot be established from these
records. We did not guess one from ranges or apply an inferred multiplier.

This is a scientific instruction gate from the user's request, not a filesystem
permission failure. It does not retroactively invalidate the earlier explicitly
conditional stored-unit results. A new stored-unit experiment could be useful,
but running it now would bypass the user's stated gate. Authoritative source-
linked scaling metadata, or an explicit revision of that condition, is needed.

## A. Current repository status

Already present: twelve generic `library_analysis` functions, grouped feature
selection/recognition, synthetic mixtures, FCLS/small MESMA/ridge, numerical
ambiguity/fraction diagnostics, the researcher-only canonical evidence packets,
formal proofs and conformance/audit records, selected-library diagnostics and the
completed 603-reference exhaustive finite-library experiment. Recent commits
include `38f646a` mesma reports, `d18cf73` doc updates, `cf98a97` more reports,
`731c32d` lean proof, `01e6d1c` mesma readiness report and `5682be2` readiness analysis.

The queue still retains P133 source-impact/production-audit work. The formal audit
records band-axis inference, overlapping extraction windows and other limitations;
none was silently repaired or assumed to have affected these historical results.
P137's narrative progress line is stale (says running), but its completion,
checkpoint metadata and verified summary establish completion. P136's older
“full search not run” limit is superseded by the separate P137 packet, not erased.

See [the A–E classification and implementation plan](IMPLEMENTATION_PLAN.md) for
what exists, what is reusable, what remains study-specific, documentation work
and observations still required. The original merged scientific table remains
in place and was not copied.

## B. Package changes

**None.** No new API is claimed. The proposed coherent reference-library audit
and streaming backend are planned for promotion after the gate. The provenance
runner is not safe to copy unchanged as a universal backend: its library Gram
matrix is quadratic, all targets enter each batch, and checkpoint output bytes
need integrity protection in addition to compatible input/configuration checks.
Existing small-MESMA eager defaults remain unchanged.

## C. Scientific experiment

The [planned design](DESIGN.md) preserves the earlier proper/tuning/target parents,
170-mixture bundle recipes, categories, domains and metrics while varying spectral
support. It lists all requested budgets, selected versus five deterministic
random paths, PCA scope, fixed estimator/capacity controls, bundle uncertainty and
identity/support gates. This is a design for resumption, not fitted results.
One-band MESMA requires deliberate numerical support because the existing kernel
requires at least two channels. Historical loaders that write sealed input records
must not be reused as entry points.

## D. Preserved results

The seven canonical integration source hashes and all 1,039 unique owned files
across four historical manifests match. Existing results are preserved:

- All 10 recorded-category pairs differ across four acquisition-matched cohorts.
- Full NEON recognition BA is approximately 85.2% unseen polygons / 73.8% held
  sites, versus synthetic OLI 66.8% / 57.7%.
- Ridge120 synthetic fraction RMSE is approximately 0.216 / 0.269, but matched15
  loses that original advantage and global-year ridge fails the prior on average.
- The separate 603-reference exhaustive OLI benchmark searched 16,918,447 models
  for each of 360 targets (6,090,640,920 target–model evaluations). Spectral RMSE
  fell from 0.003721 to 0.000792 while fraction RMSE changed 0.3215 to 0.3336;
  156 target fraction errors improved, 203 worsened and one was unchanged.

These are **preserved prior findings**, not a newly fitted information curve.
Exact prior values/source hashes are in `source_scale_audit.json`. Mean-fold
scores and pooled target/class RMSEs from different studies are not equivalent
aggregation estimands and must not be compared as one uniform benchmark.

## E. Scientific interpretation and requested decision questions

1. Increasing information improves recognition in the existing full-NEON versus
   synthetic-OLI comparison. The requested new budget curve has not been run.
2. The new constant-parent abundance curve is unavailable; previous capacity and
   prior controls prevent a claim of intrinsic ridge superiority.
3. Ambiguity reduction with the requested budgets is not determined here.
4. A plateau or minimum-band range cannot be estimated without those curves.
5. Woody shrub is weak in held-site recognition; recognition difficulty is not
   proof of fundamental physical or abundance nonidentifiability.
6. Previously selected wavelengths are conditional training-derived evidence;
   no new repeated-selection frequency or universal useful-band claim is made.
7. No new matched-capacity hyperspectral-versus-OLI abundance answer is available.
   More bands do not alone establish a unique biological inverse.
8. The exhaustive experiment demonstrates that a better spectral fit need not
   produce better fractions. Candidate screening is not a sufficient explanation
   for that experiment's fraction errors. This is not a blanket MESMA rejection.
9. Current evidence cannot uniquely apportion information loss, library coverage,
   category overlap, domain shift and model inadequacy. No causal ranking is made.
10. Field abundance needs independently measured complete contemporaneous cover
    fractions at matched spatial support, verified units and source lineage,
    adequate/purity-audited references and independently held domains.

Fixed affine/linear maps can preserve mixture algebra while losing injectivity,
as the formal layer conditionally proves. No theorem validates scale metadata,
researcher categories as pure materials, real mixing or field fractions. The
new empirical dimensionality/ambiguity questions remain unanswered.

## F. Website/documentation changes

No scientific website pages, navigation or canonical numerical snapshots changed.
The existing interpretation remains intact. New audit/design/plan records are in
this separate packet. Website result integration is deferred until valid new
results exist; pending curves were not fabricated to complete a page.

## G. Validation

Reproduce this read-only audit:

```bash
.venv/bin/python provenance/abundance-information/2026-10-19/v1/audit_main.py
```

It checks original source/compact identities, four prior manifests and the seven
canonical integration source hashes; writes only this new packet; and raises
on a historical hash mismatch. It reports the unresolved-scale gate explicitly.
See [VALIDATION.md](VALIDATION.md) for tests and unrun downstream gates. New packet
hashes are in `packet_manifest.json`. No formal proof sources changed.

## H. Remaining limitations

Source scaling is unresolved; P138 is blocked under the user's instruction.
The reusable APIs, new fitting/curves, publication figures, website integration,
package build and full release/readiness gates are **not completed**. No feature
selections, identity memberships, metrics or uncertainty files are presented as
new experiment outputs. Historical packets remain unchanged. Field abundance
remains unestablished regardless of how this gate is resolved.

## I. Recommendation and resumption

Obtain the source-linked corrected NEON/OLI unit/multiplier/offset record first.
A controlled information-loss experiment remains scientifically motivated, but
cannot be launched under the present stop rule. It should not become another
arbitrary algorithm contest. If high-information experiments retain substantial
ambiguity after controls pass, the next requirement is independent observations,
especially complete contemporaneous fractional-cover measurements, rather than
more searches on the same spectra.
