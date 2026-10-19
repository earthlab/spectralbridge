"""Experimental, exact small convex mixture models and audited library selection.

No operational abundance claim or stable top-level API. Model spectra and targets
must share explicit support and one common scale; never normalize each separately.
"""

from itertools import combinations, product
import numpy as np


def _matrix(values):
    a = np.asarray(values, float)
    if a.ndim != 2 or a.shape[1] < 2 or not np.isfinite(a).all():
        raise ValueError("Finite two-dimensional common-support spectra required")
    return a


def model_indices(labels, max_components=3, maximum_models=20000):
    """Enumerate distinct-class candidate sets, including every simplex face."""
    labels = np.asarray(labels)
    groups = [np.flatnonzero(labels == c) for c in np.unique(labels)]
    count = sum(
        sum(
            np.prod([len(groups[j]) for j in comb], dtype=np.int64)
            for comb in combinations(range(len(groups)), size)
        )
        for size in range(1, min(max_components, len(groups)) + 1)
    )
    if count > maximum_models:
        raise ValueError(f"Model budget exceeded: {count} > {maximum_models}")
    return [
        np.array(ix, int)
        for size in range(1, min(max_components, len(groups)) + 1)
        for comb in combinations(groups, size)
        for ix in product(*comb)
    ]


def fit_models(
    targets,
    labels,
    endmembers,
    *,
    max_components=3,
    tolerance=0.01,
    maximum_models=20000,
    chunk_models=128,
):
    """Exact active-face search, not unconstrained fractions clipped afterwards.

    Interior affine least squares is admitted only inside its simplex. Every
    boundary face appears explicitly. Singular interiors are skipped; their
    convex hull remains covered by affinely independent lower-dimensional faces.
    Near-composition counts count distinct CLASS sets, not redundant candidates.
    """
    y = _matrix(targets)
    e = _matrix(endmembers)
    labels = np.asarray(labels)
    if e.shape[1] != y.shape[1] or len(labels) != len(e) or not len(e):
        raise ValueError("Aligned nonempty endmember library and targets required")
    models = model_indices(labels, max_components, maximum_models)
    classes = np.unique(labels)
    classpos = {v: i for i, v in enumerate(classes)}
    n = len(y)
    bands = e.shape[1]
    gram = e @ e.T
    dot = y @ e.T
    yy = np.sum(y * y, axis=1)
    best = np.full(n, np.inf)
    bestf = np.zeros((n, len(classes)))
    complexity = np.zeros(n, int)
    bestmodel = np.full((n, max_components), -1, int)
    composition_errors = {}
    composition_fractions = {}
    # Chunked candidates bound memory independently of image/mixture count.
    for size in range(1, min(max_components, len(classes)) + 1):
        subset = [m for m in models if len(m) == size]
        for start in range(0, len(subset), chunk_models):
            ix = np.array(subset[start : start + chunk_models])
            m = len(ix)
            if not m:
                continue
            if size == 1:
                f = np.ones((n, m, 1))
            else:
                base = ix[:, 0]
                others = ix[:, 1:]
                g = (
                    gram[others[:, :, None], others[:, None, :]]
                    - gram[others, base[:, None]][:, :, None]
                    - gram[base[:, None], others][:, None, :]
                    + gram[base, base][:, None, None]
                )
                eigen = np.linalg.eigvalsh(g)
                good = eigen[:, 0] > np.maximum(1e-12, eigen[:, -1] * 1e-10)
                inv = np.zeros_like(g)
                if good.any():
                    inv[good] = np.linalg.inv(g[good])
                rhs = (
                    dot[:, others]
                    - dot[:, base, None]
                    - gram[base[:, None], others][None, :, :]
                    + gram[base, base][None, :, None]
                )
                tail = np.einsum("nmi,mij->nmj", rhs, inv)
                f = np.concatenate([1 - tail.sum(2, keepdims=True), tail], axis=2)
                f[:, ~good, :] = np.nan
            valid = np.isfinite(f).all(2) & (f.min(2) > 1e-9) & (f.max(2) <= 1 + 1e-9)
            # Zero-fraction additions are boundary faces, not distinct material compositions.
            # Numerical boundary roundoff only; not a replacement for constrained optimization.
            f = np.clip(f, 0, 1)
            f /= f.sum(2, keepdims=True)
            err = (
                yy[:, None]
                - 2 * np.einsum("nmi,nmi->nm", f, dot[:, ix])
                + np.einsum(
                    "nmi,mij,nmj->nm", f, gram[ix[:, :, None], ix[:, None, :]], f
                )
            ) / bands
            err = np.where(valid, np.maximum(err, 0), np.inf)
            local = err.argmin(1)
            vals = err[np.arange(n), local]
            improve = vals < best - 1e-14
            if improve.any():
                chosen = np.flatnonzero(improve)
                best[chosen] = vals[chosen]
                complexity[chosen] = size
                bestf[chosen] = 0
                bestmodel[chosen] = -1
                for row in chosen:
                    j = local[row]
                    bestmodel[row, :size] = ix[j]
                    for k, index in enumerate(ix[j]):
                        bestf[row, classpos[labels[index]]] += f[row, j, k]
            for j, ids in enumerate(ix):
                key = tuple(sorted(classpos[labels[i]] for i in ids))
                if key not in composition_errors:
                    composition_errors[key] = np.full(n, np.inf)
                    composition_fractions[key] = np.zeros((n, len(classes)))
                better = err[:, j] < composition_errors[key]
                composition_errors[key][better] = err[better, j]
                if better.any():
                    composition_fractions[key][better] = 0
                    for k, index in enumerate(ids):
                        composition_fractions[key][better, classpos[labels[index]]] = f[
                            better, j, k
                        ]
    errors = np.sqrt(np.column_stack(list(composition_errors.values())))
    rmse = np.sqrt(best)
    near = (errors <= rmse[:, None] + tolerance).sum(1)
    order = np.sort(errors, axis=1)
    near_mask = errors <= rmse[:, None] + tolerance
    candidates = np.stack(list(composition_fractions.values()), axis=1)
    ranges = np.max(
        np.where(near_mask[:, :, None], candidates, -np.inf), axis=1
    ) - np.min(np.where(near_mask[:, :, None], candidates, np.inf), axis=1)

    reconstruction = np.zeros_like(y)
    for j in range(max_components):
        good = bestmodel[:, j] >= 0
        if not good.any():
            continue
        for row in np.flatnonzero(good):
            index = bestmodel[row, j]
            reconstruction[row] += bestf[row, classpos[labels[index]]] * e[index]
    norms = np.linalg.norm(y, axis=1) * np.linalg.norm(reconstruction, axis=1)
    cosine = np.divide(
        np.sum(y * reconstruction, axis=1),
        norms,
        out=np.full(n, np.nan),
        where=norms > 1e-12,
    )
    angles = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
    return dict(
        fractions=bestf,
        spectral_angle_deg=angles,
        reconstruction=reconstruction,
        near_fraction_range=ranges,
        classes=classes,
        RMSE=rmse,
        complexity=complexity,
        model_indices=bestmodel,
        model_count=len(models),
        near_compositions=near,
        composition_errors=composition_errors,
        runner_up_gap=order[:, 1] - order[:, 0]
        if errors.shape[1] > 1
        else np.full(n, np.nan),
    )


def fcls(targets, endmembers) -> dict:
    """Exactly fit a small fixed library under nonnegative sum-one constraints.

    Args:
        targets (array-like): Finite spectra (N, B), B >= 2, in common units.
        endmembers (array-like): Finite candidate spectra (M, B), 1 <= M <= 12.

    Returns:
        dict: Fractions (N, M), RMSE/reconstructions, angle and ambiguity details
            from fit_models. Fractions are dimensionless; RMSE retains input units.

    Raises:
        ValueError: Nonfinite/inconsistent matrices or oversized library.

    Experimental numerical utility, not an ecological abundance validation.
    Every feasible face is considered at declared numerical rank tolerances;
    degenerate/near-collinear candidates can leave fractions nonidentifiable.
    """
    e = _matrix(endmembers)
    if len(e) > 12:
        raise ValueError("Exact FCLS is limited to 12 fixed endmembers")
    return fit_models(
        targets, np.arange(len(e)), e, max_components=len(e), maximum_models=4095
    )


def shade_model_errors(targets, candidates):
    """RMSE(target, f*candidate+(1-f)*0), 0<=f<=1; rows target, cols candidate."""
    y = _matrix(targets)
    e = _matrix(candidates)
    dot = y @ e.T
    norm = np.sum(e * e, axis=1)
    f = np.divide(dot, norm, out=np.zeros_like(dot), where=norm > 1e-15)
    f = np.clip(f, 0, 1)
    return np.sqrt(
        np.maximum(
            0,
            (np.sum(y * y, axis=1)[:, None] - 2 * f * dot + f * f * norm) / y.shape[1],
        )
    )


def _angles(a, b):
    norm = np.linalg.norm(a, axis=1)[:, None] * np.linalg.norm(b, axis=1)[None, :]
    cos = np.divide(a @ b.T, norm, out=np.full(norm.shape, np.nan), where=norm > 1e-12)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def selection_scores(spectra, labels):
    """Published EAR and MASA within-class means excluding self."""
    e = _matrix(spectra)
    labels = np.asarray(labels)
    n = len(e)
    ear = np.full(n, np.nan)
    masa = ear.copy()
    medoid = ear.copy()
    for label in np.unique(labels):
        ix = np.flatnonzero(labels == label)
        v = e[ix]
        if len(ix) == 1:
            ear[ix] = masa[ix] = medoid[ix] = 0
            continue
        err = shade_model_errors(v, v)
        angles = _angles(v, v)
        np.fill_diagonal(err, 0)
        np.fill_diagonal(angles, 0)
        ear[ix] = err.sum(0) / (len(ix) - 1)
        masa[ix] = angles.sum(0) / (len(ix) - 1)
        squared = np.maximum(
            0, np.sum(v * v, 1)[:, None] + np.sum(v * v, 1)[None, :] - 2 * v @ v.T
        )
        medoid[ix] = np.sqrt(squared).sum(0) / (len(ix) - 1)
    return dict(EAR=ear, MASA=masa, medoid=medoid)


def _kappa(truth, pred):
    labels = np.unique(np.concatenate([truth, pred]))
    n = len(truth)
    observed = np.mean(truth == pred)
    chance = sum(np.sum(truth == c) * np.sum(pred == c) for c in labels) / (n * n)
    return (observed - chance) / (1 - chance) if chance < 1 else 0.0


def _ies(error, labels, threshold, budget):
    """Schaaf/Roth add/remove training kappa; size-limited, no rare-class forcing."""
    _, truth = np.unique(labels, return_inverse=True)

    def score(ix):
        ix = np.asarray(ix, int)
        r = error[:, ix]
        j = r.argmin(1)
        pred = truth[ix[j]].copy()
        pred[r[np.arange(len(r)), j] > threshold] = -1
        return _kappa(truth, pred)

    if len(labels) < 2:
        return list(range(len(labels)))
    pairs = list(combinations(range(len(labels)), 2))
    scores = [score(pair) for pair in pairs]
    chosen = list(pairs[int(np.argmax(scores))])
    best = max(scores)
    while len(chosen) < budget:
        remaining = [i for i in range(len(labels)) if i not in chosen]
        if not remaining:
            break
        scores = [score([*chosen, i]) for i in remaining]
        j = int(np.argmax(scores))
        if scores[j] <= best + 1e-12:
            break
        chosen.append(remaining[j])
        best = scores[j]
        while len(chosen) > 2:
            alternatives = [chosen[:j] + chosen[j + 1 :] for j in range(len(chosen))]
            scores = [score(ix) for ix in alternatives]
            j = int(np.argmax(scores))
            if scores[j] <= best + 1e-12:
                break
            chosen = alternatives[j]
            best = scores[j]
    return chosen


def select_endmembers(
    spectra, labels, method, count_per_class, *, seed=20261014, threshold=0.02
):
    """Training-only selections. IES budget is global count_per_class x classes.

    CoB may stop early once all training spectra are covered. Ranking EAR/MASA
    beyond their minimum and capped IES/hybrid are explicitly size adaptations.
    """
    e = _matrix(spectra)
    labels = np.asarray(labels)
    if len(labels) != len(e) or count_per_class < 1:
        raise ValueError("Invalid selection settings")
    methods = {"random", "medoid", "EAR", "MASA", "CoB", "IES", "diversity", "hybrid"}
    if method not in methods:
        raise ValueError("Unknown selection method")
    rng = np.random.default_rng(seed)
    classes = np.unique(labels)
    scores = selection_scores(e, labels)
    error = None
    if method in {"IES", "hybrid"}:
        error = shade_model_errors(e, e)
        chosen = _ies(
            error, labels, threshold, min(len(e), count_per_class * len(classes))
        )
        if method == "IES":
            return np.array(chosen, int)
        for c in classes:
            if not np.any(labels[chosen] == c):
                ix = np.flatnonzero(labels == c)
                chosen.append(int(ix[np.argmin(scores["EAR"][ix])]))
        return np.array(chosen, int)
    chosen = []
    for c in classes:
        ix = np.flatnonzero(labels == c)
        n = min(count_per_class, len(ix))
        if method == "random":
            take = rng.choice(ix, n, replace=False)
        elif method in {"EAR", "MASA", "medoid"}:
            take = ix[np.argsort(scores[method][ix], kind="stable")[:n]]
        elif method == "diversity":
            take = [int(ix[np.argmin(scores["medoid"][ix])])]
            while len(take) < n:
                dist = np.min(
                    np.sum((e[ix, None, :] - e[np.array(take)][None, :, :]) ** 2, 2), 1
                )
                dist[np.isin(ix, take)] = -np.inf
                take.append(int(ix[np.argmax(dist)]))
        else:
            err = shade_model_errors(e[ix], e[ix])
            covered = np.zeros(len(ix), bool)
            take = []
            while len(take) < n:
                marginal = ((err <= threshold) & ~covered[:, None]).sum(0)
                marginal[np.isin(ix, take)] = -1
                best = np.flatnonzero(marginal == marginal.max())
                if marginal[best[0]] <= 0:
                    break
                j = int(best[np.argmin(scores["EAR"][ix[best]])])
                take.append(int(ix[j]))
                covered |= err[:, j] <= threshold
        chosen.extend(take)
    return np.asarray(chosen, int)


def grouped_identity_split(identities, test_rows):
    """Purge every held-out identity from training while preserving the supplied test-row mask."""

    ids = np.asarray(identities)
    test = np.array(test_rows, dtype=bool, copy=True)
    if ids.shape != test.shape:
        raise ValueError("Aligned identities and split required")
    train = ~np.isin(ids, ids[test])
    return train, test


def mixture_truth(
    spectra, labels, *, pairs_per_composition=2, seed=20261014, include_triples=True
):
    """Generate linear mixtures ONLY from a caller-provided held-out source set."""
    e = _matrix(spectra)
    labels = np.asarray(labels)
    classes = np.unique(labels)
    pos = {c: i for i, c in enumerate(classes)}
    rng = np.random.default_rng(seed)
    members = {c: np.flatnonzero(labels == c) for c in classes}
    values = []
    truth = []
    sources = []
    fraction_vectors = []
    gradient = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1]
    compositions = list(combinations(classes, 2))
    if include_triples:
        compositions += list(combinations(classes, 3))
    for comp in compositions:
        for _ in range(pairs_per_composition):
            ix = np.array([rng.choice(members[c]) for c in comp])
            fractions = (
                [[f, 1 - f] for f in gradient]
                if len(comp) == 2
                else [[1 / 3] * 3, [0.1, 0.2, 0.7], [0.05, 0.45, 0.5], [0.8, 0.1, 0.1]]
            )
            for f in fractions:
                t = np.zeros(len(classes))
                for c, weight in zip(comp, f):
                    t[pos[c]] = weight
                values.append(np.asarray(f) @ e[ix])
                truth.append(t)
                sources.append(np.pad(ix, (0, 3 - len(ix)), constant_values=-1))
                fraction_vectors.append(np.pad(f, (0, 3 - len(f))))
    return dict(
        spectra=np.asarray(values),
        truth=np.asarray(truth),
        sources=np.asarray(sources),
        source_fractions=np.asarray(fraction_vectors),
        classes=classes,
    )


def validate_holdout(identities, train, test, selected=None) -> None:
    """Reject identity leakage or endmembers selected outside a training fold.

    Args:
        identities (array-like): Nonmissing identity vector, shape (N,).
        train (array-like): Boolean training mask, shape (N,).
        test (array-like): Boolean test mask, shape (N,). Unused rows are allowed.
        selected (array-like, optional): Integer candidate indices into these N rows.

    Raises:
        ValueError: Shapes/identities are invalid, identities cross folds, or a
            selected index is not a training row. Split by site/flight first;
            this guard then purges/checks the complete identity history.
    """
    ids = np.asarray(identities)
    tr, te = np.asarray(train, bool), np.asarray(test, bool)
    if ids.ndim != 1 or ids.shape != tr.shape or ids.shape != te.shape:
        raise ValueError("Aligned identity and fold masks required")
    if any(v is None or v != v or str(v).strip() == "" for v in ids):
        raise ValueError("Nonmissing holdout identities required")
    if np.any(tr & te) or np.intersect1d(ids[tr], ids[te]).size:
        raise ValueError("Held-out identity leakage")
    if selected is not None:
        selected = np.asarray(selected)
        if selected.ndim != 1 or selected.dtype.kind not in "iu":
            raise ValueError("Selected endmembers must be integer row indices")
        if np.any(selected < 0) or np.any(selected >= len(ids)) or not tr[selected].all():
            raise ValueError("Endmember selected outside training fold")


def adequacy_status(residuals, threshold) -> np.ndarray:
    """Experimental residual adequacy labels; never certify material membership.

    Args:
        residuals (array-like): Finite nonnegative RMSE values in the same units
            as threshold; arbitrary shape.
        threshold (float): Nonnegative training-only adequacy bound. NaN means
            unassessed; infinity and negative bounds are invalid.

    Returns:
        numpy.ndarray: Same-shape string labels. Low residual is explicitly
            unvalidated membership, even when an unknown material fits exactly.

    Raises:
        ValueError: Invalid residuals or threshold. No data are clipped.
    """
    r = np.asarray(residuals, float)
    if not np.isfinite(r).all() or np.any(r < 0) or threshold < 0 or np.isinf(threshold):
        raise ValueError("Finite nonnegative residuals and a nonnegative threshold required")
    if np.isnan(threshold):
        return np.full(r.shape, "UNASSESSED_MISSING_THRESHOLD")
    return np.where(r > threshold, "NO_ADEQUATE_LIBRARY_MODEL", "LOW_RESIDUAL_NOT_VALIDATED_MEMBERSHIP")


def detection_metrics(truth, estimated, *, threshold=0.1) -> dict:
    """Conditional fraction-detection counts; true presence means truth > 0.

    Args:
        truth (array-like): Finite fractions in [0, 1], shape (N,) or (N, C).
        estimated (array-like): Same-shape finite fractions in [0, 1].
        threshold (float): Detection cutoff in (0, 1], inclusive within 1e-10,
            matching the readiness workflow's detection-curve rule.

    Returns:
        dict: TP, FP, TN, FN, N and false-positive/negative rates across supplied
            entries. A rate with no eligible denominator is NaN. These conditional
            observations do not define population detection limits. Truth >= 0.1
            class-set error in the readiness audit is a separate estimand.

    Raises:
        ValueError: Shape, range or nonfinite inputs are invalid.
    """
    a, b = np.asarray(truth, float), np.asarray(estimated, float)
    if a.shape != b.shape or a.ndim not in (1, 2) or not 0 < threshold <= 1:
        raise ValueError("Aligned fractions and detection threshold in (0, 1] required")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.any((a < 0) | (a > 1) | (b < 0) | (b > 1)):
        raise ValueError("Finite fractions in [0, 1] required")
    present, detected = a > 0, b >= threshold - 1e-10
    tp, fp = int((present & detected).sum()), int((~present & detected).sum())
    tn, fn = int((~present & ~detected).sum()), int((present & ~detected).sum())
    return dict(N=a.size, TP=tp, FP=fp, TN=tn, FN=fn,
                false_positive_rate=fp / (fp + tn) if fp + tn else np.nan,
                false_negative_rate=fn / (fn + tp) if fn + tp else np.nan)
