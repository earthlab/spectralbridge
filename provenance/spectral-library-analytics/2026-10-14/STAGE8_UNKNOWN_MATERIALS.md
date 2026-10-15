# 13 · Does the library know when it lacks the answer?

For each class challenge, that entire ecological class is removed from proper training and known calibration. Final test plants from the omitted class become proxy unknowns. A model trained on the remaining classes is asked to reject them, rather than simply force their assignment.

We compare nearest spectral angle, nearest distance, scaled PCA radius and reconstruction residual, classifier confidence and empty raw-score conformal sets. Distance thresholds are chosen from known calibration identities alone. Unknown labels never tune them.

Unknown recall is low at the resulting low known-class rejection rates. This is a strong reason not to interpret a confident closed-set class label as proof of membership. Precision and average precision also depend on the challenge prevalence; the tables retain that baseline.

The omitted labels are ecological proxies. They do not exhaust water, soil, snow, mixed vegetation, shadow or new mineral materials. Earlier absent-class MESMA residual and ambiguity checks reinforce the same warning: unknown materials can lie inside the known library’s convex spectral space.

A zero vector in selected coordinates has no spectral angle; the angle result is explicitly undefined while valid distance/PCA diagnostics remain available. No artificial angle is assigned.

Evidence: unknown_material_detection.csv; withheld memberships/predictions; earlier unknown residual audit
