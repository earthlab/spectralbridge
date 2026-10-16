"""Focused scientific closure diagnostics; experimental, no production changes.

Paired partitions are descriptive balanced-panel sums of squares, not causal
variance components or random regional effects. GlobalID is a polygon identity.
"""

import re
import numpy as np
import pandas as pd


def spectral_shape(values, weights):
    """Per-observation weighted unit norm and amplitude; never fit on test rows."""
    X, w = np.asarray(values, float), np.asarray(weights, float)
    if (
        X.ndim != 2
        or w.shape != (X.shape[1],)
        or not np.isfinite(X).all()
        or not np.isfinite(w).all()
        or (w <= 0).any()
    ):
        raise ValueError("Finite spectra and positive aligned weights required")
    w = w / w.sum()
    amplitude = np.sqrt(np.sum(X * X * w, axis=1))
    if (amplitude <= 0).any():
        raise ValueError("Zero-norm spectrum has undefined shape")
    return X / amplitude[:, None], amplitude


def closure_labels(table):
    """Explicit partial biological hierarchy; mixed cover is a proxy, not purity."""
    t = table.copy()
    species = t.species.fillna("").astype(str)
    t["species_level"] = species.where(
        species.map(lambda x: bool(re.fullmatch(r"[A-Z][a-z]+ [a-z][a-z-]+", x)))
    )
    t["researcher_level"] = t.cover_category
    t["narrow_pft"] = t.pft_code.where(t.pft_code.ne("UNASSIGNED"))
    mapping = {
        "DBS": "Deciduous woody",
        "DBT": "Deciduous woody",
        "EBS": "Evergreen woody",
        "ECS": "Evergreen woody",
        "ECT": "Evergreen woody",
    }
    t["broad_pft"] = t.pft_code.map(mapping)
    cover = {
        "Deciduous": "Vegetation-labelled",
        "Evergreen": "Vegetation-labelled",
        "Herbaceous": "Vegetation-labelled",
        "Woody shrub": "Vegetation-labelled",
        "Non-vegetated & dead": "Nonvegetated/dead proxy",
    }
    t["coarse_cover"] = t.cover_category.map(cover)
    return t


def paired_partition(first, second, labels, weights):
    """Exact class/polygon/year/interaction/residual SS on a complete two-year panel.

    Labels must be stable per identity. Columns are spectral coordinates with
    explicit positive quadrature weights. Class and polygon are nested; the
    balanced time structure makes this decomposition orthogonal even with
    unequal class sizes. Components describe this panel, not a causal population.
    """
    A, B, y, w = (
        np.asarray(first, float),
        np.asarray(second, float),
        np.asarray(labels),
        np.asarray(weights, float),
    )
    if (
        A.ndim != 2
        or A.shape != B.shape
        or len(y) != len(A)
        or len(A) < 2
        or w.shape != (A.shape[1],)
        or not np.isfinite(A).all()
        or not np.isfinite(B).all()
        or not np.isfinite(w).all()
        or (w <= 0).any()
    ):
        raise ValueError("Aligned finite complete pairs and positive weights required")
    w = w / w.sum()

    def ss(X):
        return float(np.sum(X * X * w))

    mid = (A + B) / 2
    delta = B - A
    grand = mid.mean(0)
    change = delta.mean(0)
    class_mean = np.empty_like(mid)
    class_change = np.empty_like(delta)
    centers0 = []
    centers1 = []
    for c in np.unique(y):
        ix = y == c
        class_mean[ix] = mid[ix].mean(0)
        class_change[ix] = delta[ix].mean(0)
        centers0.append(A[ix].mean(0))
        centers1.append(B[ix].mean(0))
    components = dict(
        class_SS=2 * ss(class_mean - grand),
        polygon_within_class_SS=2 * ss(mid - class_mean),
        year_SS=len(A) / 2 * ss(change),
        class_by_year_SS=0.5 * ss(class_change - change),
        residual_change_SS=0.5 * ss(delta - class_change),
    )
    total = ss(A - grand) + ss(B - grand)
    if not np.isclose(sum(components.values()), total, rtol=1e-10, atol=1e-10):
        raise ArithmeticError("Paired SS decomposition failed")

    def pairwise_rms(X):
        return np.sqrt(2 * ss(X - X.mean(0)) / (len(X) - 1)) if len(X) > 1 else np.nan

    class_rms = float(
        np.sqrt(
            np.nanmean(
                [
                    pairwise_rms(np.asarray(centers0)) ** 2,
                    pairwise_rms(np.asarray(centers1)) ** 2,
                ]
            )
        )
    )
    change_rms = np.sqrt(ss(delta) / len(A))
    result = dict(
        **components,
        total_SS=total,
        identities=len(A),
        classes=len(np.unique(y)),
        paired_change_RMS=change_rms,
        between_polygon_RMS=float(
            np.sqrt((pairwise_rms(A) ** 2 + pairwise_rms(B) ** 2) / 2)
        ),
        between_class_centroid_RMS=class_rms,
        change_to_class_ratio=change_rms / class_rms if class_rms > 0 else np.nan,
        common_year_shift_RMS=np.sqrt(ss(change)),
    )
    result.update(
        {
            k.replace("_SS", "_fraction"): v / total if total > 0 else np.nan
            for k, v in components.items()
        }
    )
    return result


def paired_partition_bootstrap(
    first, second, labels, weights, *, replicates=499, seed=20261015
):
    """Class-stratified identity resampling preserves both years of each pair."""
    y = np.asarray(labels)
    rng = np.random.default_rng(seed)
    members = [np.flatnonzero(y == c) for c in np.unique(y)]
    estimates = []
    keys = [
        "paired_change_RMS",
        "between_class_centroid_RMS",
        "change_to_class_ratio",
        "year_fraction",
        "class_fraction",
        "residual_change_fraction",
    ]
    for _ in range(replicates):
        ix = np.concatenate([rng.choice(g, len(g), replace=True) for g in members])
        result = paired_partition(
            np.asarray(first)[ix], np.asarray(second)[ix], y[ix], weights
        )
        estimates.append([result[k] for k in keys])
    a = np.asarray(estimates)
    return {
        k + suffix: float(np.nanquantile(a[:, j], q))
        for j, k in enumerate(keys)
        for suffix, q in [("_low", 0.025), ("_high", 0.975)]
    }


def one_vs_rest_metrics(truth, predicted, classes):
    """Multiclass one-versus-rest rates; undefined denominators stay NaN."""
    truth, predicted = np.asarray(truth), np.asarray(predicted)
    if (
        truth.shape != predicted.shape
        or truth.ndim != 1
        or not set(truth).issubset(classes)
        or not set(predicted).issubset(classes)
    ):
        raise ValueError("Aligned labels within the declared classes required")
    records = []
    for c in classes:
        a, b = truth == c, predicted == c
        tp, fn, fp, tn = [int(x.sum()) for x in [a & b, a & ~b, ~a & b, ~a & ~b]]

        def divide(n, d):
            return n / d if d else np.nan

        records.append(
            dict(
                label=c,
                N=len(a),
                positive_support=tp + fn,
                TP=tp,
                FN=fn,
                FP=fp,
                TN=tn,
                recall=divide(tp, tp + fn),
                sensitivity=divide(tp, tp + fn),
                specificity=divide(tn, tn + fp),
                FPR=divide(fp, fp + tn),
                FNR=divide(fn, fn + tp),
                precision=divide(tp, tp + fp),
            )
        )
    return pd.DataFrame(records)


def cluster_rate_intervals(
    truth, predicted, identities, classes, *, replicates=499, seed=20261015
):
    """Conditional class-stratified whole-identity intervals for detection rates."""
    truth, predicted, ids = (
        np.asarray(truth),
        np.asarray(predicted),
        np.asarray(identities),
    )
    if truth.shape != predicted.shape or ids.shape != truth.shape:
        raise ValueError("Aligned clustered labels required")
    frame = pd.DataFrame(dict(id=ids, label=truth))
    if frame.groupby("id").label.nunique().gt(1).any():
        raise ValueError("Conflicting biological labels within an identity")
    unique, group = np.unique(ids, return_inverse=True)
    labels = frame.drop_duplicates("id").set_index("id").loc[unique].label.to_numpy()
    rng = np.random.default_rng(seed)
    multiplicity = np.zeros((replicates, len(unique)), int)
    for c in np.unique(truth):
        members = np.flatnonzero(labels == c)
        draws = rng.choice(members, size=(replicates, len(members)), replace=True)
        for r in range(replicates):
            multiplicity[r] += np.bincount(draws[r], minlength=len(unique))
    result = []
    for c in classes:
        a, b = truth == c, predicted == c
        cells = np.zeros((len(unique), 4))
        np.add.at(cells, group, np.column_stack([a & b, a & ~b, ~a & b, ~a & ~b]))
        counts = multiplicity @ cells
        tp, fn, fp, tn = counts.T

        def ratio(n, d):
            return np.divide(n, d, out=np.full(n.shape, np.nan), where=d > 0)

        rates = dict(
            recall=ratio(tp, tp + fn),
            specificity=ratio(tn, tn + fp),
            FPR=ratio(fp, tn + fp),
            FNR=ratio(fn, tp + fn),
            precision=ratio(tp, tp + fp),
        )
        row = dict(label=c)
        for name, v in rates.items():
            finite = v[np.isfinite(v)]
            row[name + "_low"] = (
                float(np.quantile(finite, 0.025)) if len(finite) else np.nan
            )
            row[name + "_high"] = (
                float(np.quantile(finite, 0.975)) if len(finite) else np.nan
            )
        result.append(row)
    return pd.DataFrame(result)
