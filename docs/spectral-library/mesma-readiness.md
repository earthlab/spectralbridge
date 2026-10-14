# Is this library ready for spectral mixture analysis?

!!! warning "Experimental / research validation"
    Tested numerical solvers and controlled synthetic mixtures exist. Reliable
    ecological abundance mapping is not established by the current library.

Different spectra → identifiable endmembers → recoverable fractions → transferable
abundance inference is a hierarchy of evidence. A successful stage does not
certify the next. MESMA (multiple endmember spectral mixture analysis) allows
candidate endmember combinations to vary; a low reconstruction residual does
not guarantee correct material composition.

## Readiness gates

| Dimension | Current evidence | Operational status |
|---|---|---|
| Integrity / units | Native-grid and finite-value QC; source scaling still unresolved | Needs source provenance |
| Class/material coverage | Broad cover labels and conservative subclass proxies | Missing verified pure materials/purity |
| Endmember selection | EAR, MASA, CoB, IES and explicit adaptations benchmarked | Conditional training-pool diagnostics |
| Identifiability | Other-class mixtures can approximate held-out pure-label curves | Ambiguity remains |
| Fraction recovery | Held-out empirical parent curves mixed algebraically | Controlled synthetic evidence only |
| Transfer / sensor effects | Identity-purged site/year/flight folds, paired NEON/OLI | Conditional; support varies by class/fold |
| Rejection / uncertainty | Adequacy flags, alternate compositions, Monte Carlo spread | No calibrated membership confidence |
| Ecological abundance | Independent complete fraction truth unavailable | Insufficient evidence |

## What the experimental code evaluates

EAR (endmember average RMSE) scores same-class models with a candidate plus
idealized zero shade; MASA averages spectral angle. CoB counts newly modeled
spectra under a threshold; IES adds/removes candidates using training
classification performance. Multiple-candidate ranking and budget/completion
extensions are declared adaptations, not identical to every published algorithm.
Selection happens inside training folds. Candidate budgets are explicit; no
combinatorial pruning is hidden.

FCLS (fully constrained least squares) enforces nonnegative fractions summing
to one. The small-library solver enumerates feasible faces; variable-library
fits constrain candidate class combinations and retain ambiguity diagnostics.
An exact fit may have several valid compositions. Near-fraction ranges in the
current diagnostic summarize best models per class set and can underestimate
within-set candidate variability; they are not confidence intervals.

Synthetic mixtures combine held-out empirical polygon curves, with parents kept
separate from training endmembers across their entire identity history. Fraction
bias/MAE/RMSE, detection frequency, false positives/negatives, shade/unknown
sensitivity and grouped transfer are examined. Detection depends on the stated
fraction threshold and denominator; conditional frequencies are not population
detection limits. Idealized black shade is algebra, not measured canopy shade.

## Current conclusion

Primary mean class/fold fraction RMSE is about 0.344 for inferred PFTs, 0.380 for
researcher cover, and 0.292 for conservative material proxies in NEON; OLI values
are about 0.351, 0.380 and 0.291. These are synthetic mixing-weight errors, **not
field-cover accuracy**. More candidates can improve reconstruction while adding
wrong-class alternatives. Monte Carlo averages improve some errors but do not
provide calibrated abundance intervals.

Unknown material is not validated membership merely because an A/B model fits.
Residual inadequacy can reject a poor fit; a small residual still lacks
independent membership validation. Missing pure soil/litter/water/snow/shade,
annotation reconciliation, independent purity and complete abundance truth
prevent operational readiness. [Label systems](labels.md) must remain separate.

[Full readiness audit, algorithms and evidence](https://github.com/earthlab/spectralbridge/tree/main/provenance/mesma-readiness/2026-10-14)
· [Experimental API boundary](../api/scientific-analysis.md)
