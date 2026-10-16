"""Experimental researcher-cover spectral information and synthetic fractions.

Only recorded cover categories define biological groups. Utilities do not infer
physical purity, recover missing labels or validate field abundance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

RESEARCHER_CATEGORIES = (
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Non-vegetated & dead",
    "Woody shrub",
)


def validate_researcher_labels(values):
    labels = np.asarray(values, str)
    if set(labels) - set(RESEARCHER_CATEGORIES):
        raise ValueError(
            "Only the five recorded researcher cover categories are allowed"
        )
    return labels


def identity_weights(identities, labels=None):
    """Each identity has total weight one; optionally balance class totals."""
    ids = np.asarray(identities)
    unique, inverse, counts = np.unique(ids, return_inverse=True, return_counts=True)
    w = 1.0 / counts[inverse]
    if labels is not None:
        y = np.asarray(labels)
        if len(y) != len(ids):
            raise ValueError("Misaligned labels")
        if (
            pd.DataFrame({"id": ids, "label": y})
            .groupby("id")
            .label.nunique()
            .gt(1)
            .any()
        ):
            raise ValueError("An identity cannot have conflicting labels")
        for c in np.unique(y):
            use = y == c
            w[use] /= w[use].sum()
        w *= len(unique) / len(np.unique(y))
    return w


def project_simplex(values):
    """Euclidean projection onto nonnegative sum-one fractions (sorting rule)."""
    x = np.asarray(values, float)
    if x.ndim != 2 or x.shape[1] < 2 or not np.isfinite(x).all():
        raise ValueError("Need finite matrix with at least two fractions")
    u = np.sort(x, axis=1)[:, ::-1]
    css = np.cumsum(u, axis=1) - 1
    good = u - css / np.arange(1, x.shape[1] + 1) > 0
    rho = good.sum(axis=1) - 1
    theta = css[np.arange(len(x)), rho] / (rho + 1)
    return np.maximum(x - theta[:, None], 0)


def weighted_auc(truth, scores, weights=None):
    """Weighted binary ROC AUC per column, with half credit for tied values."""
    z = np.asarray(truth, bool)
    x = np.asarray(scores, float)
    if x.ndim == 1:
        x = x[:, None]
    w = np.ones(len(z)) if weights is None else np.asarray(weights, float)
    if not z.any() or z.all():
        return np.full(x.shape[1], np.nan)
    result = []
    for j in range(x.shape[1]):
        order = np.argsort(x[:, j], kind="stable")
        v, zz, ww = x[order, j], z[order], w[order]
        starts = np.r_[0, np.flatnonzero(np.diff(v) != 0) + 1]
        neg = np.add.reduceat(ww * (~zz), starts)
        pos = np.add.reduceat(ww * zz, starts)
        result.append(
            np.sum(pos * (np.cumsum(neg) - 0.5 * neg)) / (pos.sum() * neg.sum())
        )
    return np.asarray(result)


def univariate_discrimination(
    train, train_labels, train_ids, test, test_labels, test_ids
):
    """Balanced-prior single-coordinate LDA; threshold learned on training only."""
    X, T = np.asarray(train, float), np.asarray(test, float)
    y, z = np.asarray(train_labels, bool), np.asarray(test_labels, bool)
    if (
        X.ndim != 2
        or T.shape[1] != X.shape[1]
        or not np.isfinite(X).all()
        or not np.isfinite(T).all()
    ):
        raise ValueError("Finite aligned spectra required")
    if len(np.unique(y)) != 2 or len(np.unique(z)) != 2:
        raise ValueError("Both classes required in training and target")
    tw = identity_weights(train_ids)
    ew = identity_weights(test_ids)
    means = np.array(
        [np.average(X[y == c], axis=0, weights=tw[y == c]) for c in [False, True]]
    )
    var = np.array(
        [
            np.average((X[y == c] - means[i]) ** 2, axis=0, weights=tw[y == c])
            for i, c in enumerate([False, True])
        ]
    ).mean(axis=0)
    sd = np.sqrt(np.maximum(var, np.finfo(float).eps))
    delta = means[1] - means[0]
    direction = np.sign(delta)
    score = (T - (means[0] + means[1]) / 2) * direction
    pred = score > 0
    recall = np.average(pred[z], axis=0, weights=ew[z])
    specificity = np.average(~pred[~z], axis=0, weights=ew[~z])
    precision = np.sum(ew[:, None] * (pred & z[:, None]), axis=0) / np.maximum(
        np.sum(ew[:, None] * pred, axis=0), 1e-15
    )
    # Whole-ID variance of per-observation correctness, conditional on the rule.
    squared_se = np.zeros(X.shape[1])
    for c in [False, True]:
        use = z == c
        frame = pd.DataFrame(pred[use] == z[use, None])
        frame["identity"] = np.asarray(test_ids)[use]
        rates = frame.groupby("identity").mean().to_numpy()
        if len(rates) > 1:
            squared_se += rates.var(axis=0, ddof=1) / len(rates) / 4
    ba = (recall + specificity) / 2
    result = dict(
        effect=delta / sd,
        sensitivity=recall,
        specificity=specificity,
        precision=precision,
        balanced_accuracy=ba,
        BA_low=np.clip(ba - 1.96 * np.sqrt(squared_se), 0, 1),
        BA_high=np.clip(ba + 1.96 * np.sqrt(squared_se), 0, 1),
        AUC=weighted_auc(z, score, ew),
        direction=direction,
    )
    med = np.array([np.median(X[y == c], axis=0) for c in [False, True]])
    iqr = (
        np.array(
            [
                np.subtract(*np.percentile(X[y == c], [75, 25], axis=0))
                for c in [False, True]
            ]
        ).mean(axis=0)
        / 1.349
    )
    result["robust_effect"] = (med[1] - med[0]) / np.maximum(iqr, 1e-12)
    return result


def orthogonal_feature_path(X, labels, count=100, weights=None):
    """Greedy complementary coordinates via balanced one-hot residual gains.

    Every input must belong to caller's training fold. Does not examine targets
    or claim globally optimal sensor design. Orthogonalizes duplicate channels.
    """
    X = np.asarray(X, float)
    y = np.asarray(labels)
    w = np.ones(len(X)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    V = (X - np.average(X, axis=0, weights=w)) * np.sqrt(w[:, None])
    norms = np.linalg.norm(V, axis=0)
    V = V / np.maximum(norms, 1e-12)
    classes = np.unique(y)
    Y = (y[:, None] == classes).astype(float)
    R = (Y - np.average(Y, axis=0, weights=w)) * np.sqrt(w[:, None])
    chosen = []
    for _ in range(min(count, X.shape[1])):
        denom = np.sum(V * V, axis=0)
        gains = np.sum((V.T @ R) ** 2, axis=1) / np.maximum(denom, 1e-15)
        gains[denom < 1e-10] = -np.inf
        gains[chosen] = -np.inf
        j = int(np.argmax(gains))
        if not np.isfinite(gains[j]):
            # Preserve requested budgets; remaining redundant channels add no gain.
            chosen += [k for k in range(X.shape[1]) if k not in chosen][
                : count - len(chosen)
            ]
            break
        chosen.append(j)
        q = V[:, j] / np.sqrt(denom[j])
        V -= np.outer(q, q @ V)
        R -= np.outer(q, q @ R)
    return np.asarray(chosen, int)


def disconnected_derivative(X, wavelengths, order=1, max_gap=8):
    """Derivatives within supported segments, with no atmospheric-gap bridges."""
    w = np.asarray(wavelengths, float)
    out = np.asarray(X, float).copy()
    if order not in {1, 2} or np.any(np.diff(w) <= 0):
        raise ValueError("Ordered coordinates and derivative order 1 or 2 required")
    for a, b in zip(
        np.r_[0, np.flatnonzero(np.diff(w) > max_gap) + 1],
        np.r_[np.flatnonzero(np.diff(w) > max_gap) + 1, len(w)],
    ):
        if b - a < 3:
            raise ValueError("Derivative segment too short")
        segment = out[:, a:b]
        for _ in range(order):
            segment = np.gradient(segment, w[a:b], axis=1, edge_order=2)
        out[:, a:b] = segment
    return out


def disjoint_parent_bundles(table, count, seed):
    """Sample one observation per class/ID, never reuse an ID across bundles."""
    validate_researcher_labels(table.cover_category)
    if table.groupby("GlobalID").cover_category.nunique().gt(1).any():
        raise ValueError("Conflicting identity labels")
    pool = table.sort_values(["year", "GlobalID"]).drop_duplicates("GlobalID")
    rng = np.random.default_rng(seed)
    groups = [
        rng.permutation(pool.index[pool.cover_category.eq(c)])
        for c in RESEARCHER_CATEGORIES
    ]
    n = min(count, min(map(len, groups)))
    if n < 2:
        raise ValueError("Insufficient independent parents for bundles")
    return np.column_stack([g[:n] for g in groups])


def fraction_metrics(truth, pred):
    """Per-class fraction errors and presence metrics at a fixed .10 cutoff."""
    t, p = np.asarray(truth, float), np.asarray(pred, float)
    if t.shape != p.shape or not np.isfinite(p).all():
        raise ValueError("Aligned finite fractions required")
    if np.any(p < -1e-9) or not np.allclose(p.sum(axis=1), 1, atol=1e-8):
        raise ValueError("Predictions must be compositions")
    out = []
    for j in range(t.shape[1]):
        e = p[:, j] - t[:, j]
        present = t[:, j] > 0
        zero = ~present
        low = present & (t[:, j] <= 0.10)
        slope = np.polyfit(t[:, j], p[:, j], 1)[0] if np.ptp(t[:, j]) > 0 else np.nan
        out.append(
            dict(
                bias=e.mean(),
                MAE=np.mean(abs(e)),
                RMSE=np.sqrt(np.mean(e * e)),
                positive_RMSE=np.sqrt(np.mean(e[present] ** 2))
                if present.any()
                else np.nan,
                low_RMSE=np.sqrt(np.mean(e[low] ** 2)) if low.any() else np.nan,
                FPR=np.mean(p[zero, j] > 0.10) if zero.any() else np.nan,
                low_FNR=np.mean(p[low, j] <= 0.10) if low.any() else np.nan,
                calibration_slope=slope,
                N=len(t),
                N_zero=int(zero.sum()),
                N_positive=int(present.sum()),
            )
        )
    return out


class TrainingTransform:
    """Fit-only training scalers/PCA; observation-local shape and derivatives."""

    def __init__(self, kind, waves, positions=None):
        self.kind, self.waves, self.positions = kind, np.asarray(waves), positions

    def local(self, X):
        X = np.asarray(X, float)
        if self.kind == "shape":
            from .pft_method_audit import wavelength_weights

            w = wavelength_weights(self.waves)
            return X / np.maximum(np.sqrt(np.sum(X * X * w, axis=1)), 1e-12)[:, None]
        if self.kind in {"derivative1", "derivative2"}:
            return disconnected_derivative(X, self.waves, int(self.kind[-1]))
        if self.kind.startswith("selected"):
            return X[:, self.positions]
        return X

    def fit(self, X):
        from sklearn.decomposition import PCA

        V = self.local(X)
        self.scaler = StandardScaler().fit(V)
        V = self.scaler.transform(V)
        self.pca = (
            PCA(n_components=min(20, V.shape[1], len(V) - 1), svd_solver="full").fit(V)
            if self.kind == "PCA20"
            else None
        )
        return self

    def transform(self, X):
        V = self.scaler.transform(self.local(X))
        return self.pca.transform(V) if self.pca is not None else V
