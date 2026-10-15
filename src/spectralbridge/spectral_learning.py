"""Experimental leakage-safe learning primitives for the library analytics audit.

Requires the optional analytics extra. Nothing here is a stable top-level API or
proof of ecological transfer. All model selection is confined to supplied proper
training rows; outer/calibration memberships are explicit and testable.
"""

from __future__ import annotations
from dataclasses import dataclass
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from scipy.spatial.distance import cdist
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from .mixtures import grouped_identity_split, validate_holdout
from .mesma_readiness import _folds, ReadinessConfig


@dataclass(frozen=True)
class LearningConfig:
    """Fixed experimental budgets; counts are identities, never source pixels."""

    seed: int = 20261014
    plant_folds: int = 3
    minimum_train: int = 10
    minimum_test: int = 3
    calibration_fraction: float = 0.2
    minimum_calibration: int = 25
    bootstraps: int = 499
    conformal_alpha: float = 0.1
    inner_folds: int = 3


def outer_folds(table, config=None):
    """Yield actual plant/site/year/flight masks with entire identities purged.

    table requires label/site/year/GlobalID/flights. The existing readiness fold
    generator defines the seed/stratification. Unsupported folds are not omitted.
    """
    config = config or LearningConfig()
    cfg = ReadinessConfig(seed=config.seed, plant_folds=config.plant_folds)
    for name, kind, mask in _folds(table, "learning", cfg):
        train, test = grouped_identity_split(table.GlobalID, mask)
        if kind == "within_site_year":
            train &= table.site.eq("NIWO").to_numpy()
        validate_holdout(table.GlobalID, train, test)
        yield name, kind, train, test


def calibration_split(identities, fraction=0.2, seed=20261014):
    """Uniformly reserve whole training identities, not stratified pixel rows.

    Returns proper/calibration boolean masks. Caller checks class support before
    fitting. Labels never determine this split, and no outer-test data enter it.
    """
    ids = np.asarray(identities)
    if ids.ndim != 1 or not 0 < fraction < 0.5:
        raise ValueError("Need identity vector and calibration fraction in (0, .5)")
    unique = np.unique(ids)
    count = max(1, int(np.floor(len(unique) * fraction))) if len(unique) > 1 else 0
    selected = np.random.default_rng(seed).permutation(unique)[:count]
    calibration = np.isin(ids, selected)
    proper = ~calibration
    validate_holdout(ids, proper, calibration)
    return proper, calibration


class StableFSelector(TransformerMixin, BaseEstimator):
    """Training-only F-rank coordinate selection with deterministic tie handling.

    F is an exploratory ranking, not confirmatory wavelength significance.
    Selected coordinates retain their input spectral order. k='all' keeps all.
    """

    def __init__(self, k="all"):
        self.k = k

    def fit(self, X, y):
        X = np.asarray(X, float)
        if X.ndim != 2 or not np.isfinite(X).all():
            raise ValueError("Selector needs finite common-support training data")
        self.n_features_in_ = X.shape[1]
        k = self.n_features_in_ if self.k == "all" else int(self.k)
        if not 1 <= k <= self.n_features_in_:
            raise ValueError("Selected count exceeds spectral support")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            scores = f_classif(X, y)[0]
        self.scores_ = np.nan_to_num(scores, nan=-np.inf, posinf=np.finfo(float).max)
        rank = np.lexsort((np.arange(self.n_features_in_), -self.scores_))
        self.selected_ = np.sort(rank[:k])
        return self

    def transform(self, X):
        X = np.asarray(X, float)
        if X.ndim != 2 or X.shape[1] != self.n_features_in_ or not np.isfinite(X).all():
            raise ValueError("Prediction support differs from fitted training grid")
        return X[:, self.selected_]


class PLSDA(ClassifierMixin, BaseEstimator):
    """PLS regression on one-hot labels; argmax classification, raw softmax scores.

    Raw score normalization is not assumed calibrated. No class reweighting is
    implicit in PLS. All preprocessing precedes this estimator in a fitted pipeline.
    """

    def __init__(self, n_components=4):
        self.n_components = n_components

    def fit(self, X, y):
        self.classes_, encoded = np.unique(y, return_inverse=True)
        self.n_features_in_ = np.shape(X)[1]
        count = min(self.n_components, self.n_features_in_, len(X) - 1)
        self.regressor_ = PLSRegression(n_components=count, scale=False, max_iter=1000)
        self.regressor_.fit(X, np.eye(len(self.classes_))[encoded])
        return self

    def predict_proba(self, X):
        return softmax(self.regressor_.predict(X), axis=1)

    def predict(self, X):
        return self.classes_[np.argmax(self.regressor_.predict(X), axis=1)]


class CentroidClassifier(ClassifierMixin, BaseEstimator):
    """Equal-class nearest mean baseline in its training-scaled input space."""

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y)
        self.classes_ = np.unique(y)
        self.n_features_in_ = X.shape[1]
        self.centers_ = np.array([X[y == c].mean(0) for c in self.classes_])
        self.distance_scale_ = max(float(np.std(X)), 1e-12)
        return self

    def predict_proba(self, X):
        return softmax(-cdist(X, self.centers_) / self.distance_scale_, axis=1)

    def predict(self, X):
        return self.classes_[cdist(X, self.centers_).argmin(1)]


def model_pipeline(name, *, k="all", seed=20261014):
    """Return an unfitted training-only pipeline and predeclared small inner grid."""
    if name == "logistic":
        model = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)
        grid = {"model__C": [0.1, 1.0, 10.0]}
    elif name == "PLSDA":
        model, grid = PLSDA(), {"model__n_components": [2, 4, 8]}
    elif name == "SVM":
        model = SVC(
            class_weight="balanced", probability=False, decision_function_shape="ovr"
        )
        grid = {"model__C": [1.0, 10.0]}
    elif name == "forest":
        model = RandomForestClassifier(
            n_estimators=100,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=1,
        )
        grid = {"model__max_depth": [8, None]}
    elif name == "centroid":
        model, grid = CentroidClassifier(), {}
    elif name in {"majority", "stratified"}:
        model = DummyClassifier(
            strategy="most_frequent" if name == "majority" else "stratified",
            random_state=seed,
        )
        grid = {}
    else:
        raise ValueError("Unknown model: " + name)
    return Pipeline(
        [("select", StableFSelector(k)), ("scale", StandardScaler()), ("model", model)]
    ), grid


def fit_training_model(
    values,
    labels,
    identities,
    name,
    *,
    k="all",
    seed=20261014,
    inner_folds=3,
    tune=True,
    allow_repeated_identity_labels=False,
):
    """Fit only supplied proper-training data; inner splits use GlobalID groups.

    Returns estimator plus choices/support/warnings. Caller separately validates
    that these rows exclude outer-test and calibration identities.
    """
    X, y, ids = np.asarray(values, float), np.asarray(labels), np.asarray(identities)
    if (
        X.ndim != 2
        or X.shape[0] != len(y)
        or len(ids) != len(y)
        or not np.isfinite(X).all()
    ):
        raise ValueError("Aligned finite training arrays required")
    if len(np.unique(y)) < 2:
        raise ValueError("Need at least two training classes")
    frame = pd.DataFrame({"identity": ids, "label": y})
    if (
        not allow_repeated_identity_labels
        and frame.groupby("identity").label.nunique().gt(1).any()
    ):
        raise ValueError("One biological identity has conflicting target labels")
    minimum = int(frame.drop_duplicates().groupby("label").size().min())
    splits = min(inner_folds, minimum)
    model, grid = model_pipeline(name, k=k, seed=seed)
    status, params, score = "fixed_predeclared", {}, np.nan
    memberships = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if tune and grid and splits >= 2:
            cv = list(
                StratifiedGroupKFold(
                    n_splits=splits, shuffle=True, random_state=seed
                ).split(X, y, ids)
            )
            usable = []
            for tr, va in cv:
                masktr, maskva = np.zeros(len(y), bool), np.zeros(len(y), bool)
                masktr[tr], maskva[va] = True, True
                validate_holdout(ids, masktr, maskva)
                if set(y[tr]) == set(y) and len(np.unique(y[va])) >= 2:
                    usable.append((tr, va))
                    memberships.append(
                        dict(
                            train_ids=sorted(set(ids[tr])),
                            validation_ids=sorted(set(ids[va])),
                        )
                    )
            if len(usable) >= 2:
                search = GridSearchCV(
                    model,
                    grid,
                    scoring="balanced_accuracy",
                    cv=usable,
                    n_jobs=1,
                    refit=True,
                    error_score="raise",
                )
                search.fit(X, y)
                model, params, score, status = (
                    search.best_estimator_,
                    search.best_params_,
                    float(search.best_score_),
                    "group_nested_tuned",
                )
            else:
                model.fit(X, y)
                status = "fixed_insufficient_inner_support"
        else:
            model.fit(X, y)
    return model, dict(
        status=status,
        parameters=params,
        inner_balanced_accuracy=score,
        inner_memberships=memberships,
        warnings=sorted(set(str(w.message) for w in caught)),
        proper_training_identities=sorted(set(ids)),
    )


def probabilities(model, X):
    """Model-order probabilities or explicitly uncalibrated normalized decisions.

    SVM avoids its row-splitting internal probability calibration entirely.
    """
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(X)
    else:
        score = model.decision_function(X)
        if score.ndim == 1:
            score = np.column_stack([-score / 2, score / 2])
        p = softmax(score, axis=1)
    return check_probabilities(p)


def check_probabilities(p):
    p = np.asarray(p, float)
    if (
        p.ndim != 2
        or p.shape[1] < 2
        or not np.isfinite(p).all()
        or np.any(p < 0)
        or not np.allclose(p.sum(1), 1, atol=1e-8)
    ):
        raise ValueError("Need normalized finite nonnegative probability/score rows")
    return p


def temperature_probabilities(p, temperature=1.0):
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("Positive finite temperature required")
    return softmax(
        np.log(np.clip(check_probabilities(p), 1e-12, 1)) / temperature, axis=1
    )


def fit_temperature(p, encoded_truth):
    """Fit one temperature using ONLY a separately reserved calibration sample."""
    p = check_probabilities(p)
    y = np.asarray(encoded_truth, int)
    if y.shape != (len(p),) or np.any(y < 0) or np.any(y >= p.shape[1]) or not len(y):
        raise ValueError("Aligned known calibration labels required")

    def objective(log_t):
        q = temperature_probabilities(p, np.exp(log_t))
        return -np.mean(np.log(np.clip(q[np.arange(len(y)), y], 1e-12, 1)))

    result = minimize_scalar(
        objective, bounds=(-np.log(4), np.log(4)), method="bounded"
    )
    return float(np.exp(result.x)) if result.success else 1.0


def conformal_threshold(raw_calibration_p, encoded_truth, identities, alpha=0.1):
    """Finite-sample quantile of maximum RAW nonconformity per identity.

    Scores must come from a predictor fitted independently of these labels.
    Do NOT pass temperature scores fitted on the same calibration labels.
    Geographic shift and nonexchangeable sampling do not gain a guarantee.
    """
    p, y, ids = (
        check_probabilities(raw_calibration_p),
        np.asarray(encoded_truth, int),
        np.asarray(identities),
    )
    if not 0 < alpha < 1 or len(y) != len(p) or len(ids) != len(p):
        raise ValueError("Aligned calibration inputs/alpha required")
    if not len(p) or np.any(y < 0) or np.any(y >= p.shape[1]):
        raise ValueError("Known calibration labels required")
    scores = 1 - p[np.arange(len(y)), y]
    unique, ix = np.unique(ids, return_inverse=True)
    maxima = np.full(len(unique), -np.inf)
    np.maximum.at(maxima, ix, scores)
    rank = int(np.ceil((len(unique) + 1) * (1 - alpha)))
    return float(np.sort(maxima)[rank - 1]) if rank <= len(unique) else np.inf


def conformal_metrics(raw_test_p, encoded_truth, identities, threshold):
    """Empirical row/whole-identity prediction-set coverage, not a shift guarantee."""
    p = check_probabilities(raw_test_p)
    y, ids = np.asarray(encoded_truth, int), np.asarray(identities)
    if (
        len(y) != len(p)
        or len(ids) != len(p)
        or np.any(y < 0)
        or np.any(y >= p.shape[1])
    ):
        raise ValueError("Aligned known test labels required")
    sets = 1 - p <= threshold + 1e-12
    covered = sets[np.arange(len(y)), y]
    grouped = pd.DataFrame({"id": ids, "covered": covered}).groupby("id").covered.all()
    return dict(
        row_coverage=float(covered.mean()),
        identity_joint_coverage=float(grouped.mean()),
        mean_set_size=float(sets.sum(1).mean()),
        empty_set_rate=float((sets.sum(1) == 0).mean()),
    )


def classification_metrics(truth, p, classes, *, bins=10):
    """Balanced accuracy/macro F1 and calibration with explicit class order.

    Brier = mean sum-class squared error (range 0–2). ECE is top-label,
    equal-width-bin absolute calibration error. No pixel independence assumed.
    """
    p, classes, truth = check_probabilities(p), np.asarray(classes), np.asarray(truth)
    if (
        p.shape != (len(truth), len(classes))
        or not len(truth)
        or not set(truth).issubset(classes)
    ):
        raise ValueError(
            "Metrics require aligned known classes and nonempty observations"
        )
    encoded = np.array([np.flatnonzero(classes == c)[0] for c in truth])
    pred = p.argmax(1)
    matrix = np.zeros((len(classes), len(classes)), int)
    np.add.at(matrix, (encoded, pred), 1)
    support = matrix.sum(1)
    recall = np.divide(
        np.diag(matrix), support, out=np.zeros(len(classes)), where=support > 0
    )
    precision = np.divide(
        np.diag(matrix),
        matrix.sum(0),
        out=np.zeros(len(classes)),
        where=matrix.sum(0) > 0,
    )
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros(len(classes)),
        where=precision + recall > 0,
    )
    active = support > 0
    confidence, correct = p.max(1), pred == encoded
    bin_ids = np.minimum((confidence * bins).astype(int), bins - 1)
    calibration, ece = [], 0.0
    for b in range(bins):
        selected = bin_ids == b
        if selected.any():
            mean_p, accuracy = (
                float(confidence[selected].mean()),
                float(correct[selected].mean()),
            )
            ece += selected.mean() * abs(mean_p - accuracy)
            calibration.append(
                dict(
                    bin=b,
                    N=int(selected.sum()),
                    mean_confidence=mean_p,
                    accuracy=accuracy,
                )
            )
    summary = dict(
        N=len(truth),
        balanced_accuracy=float(recall[active].mean()),
        macro_F1=float(f1[active].mean()),
        accuracy=float(correct.mean()),
        Brier=float(np.mean(np.sum((p - np.eye(len(classes))[encoded]) ** 2, axis=1))),
        log_loss=float(
            -np.log(np.clip(p[np.arange(len(p)), encoded], 1e-12, 1)).mean()
        ),
        ECE=float(ece),
    )
    per_class = [
        dict(
            label=str(c),
            N=int(support[i]),
            precision=float(precision[i]),
            recall=float(recall[i]),
            F1=float(f1[i]),
        )
        for i, c in enumerate(classes)
    ]
    return summary, per_class, matrix, calibration


def cluster_bootstrap_accuracy(
    truth,
    predicted,
    identities,
    classes,
    *,
    replicates=499,
    seed=20261014,
    stratify=True,
):
    """Stratified whole-identity balanced-accuracy draws for paired comparisons.

    Identical ordered inputs/classes/seed give identical draws across sensors.
    Intervals condition on observed sites/classes, not a site superpopulation.
    """
    truth, predicted, ids, classes = map(
        np.asarray, (truth, predicted, identities, classes)
    )
    if not (truth.shape == predicted.shape == ids.shape) or truth.ndim != 1:
        raise ValueError("Aligned identity-level bootstrap inputs required")
    if not set(truth).issubset(classes) or not set(predicted).issubset(classes):
        raise ValueError("Predictions and truth must share declared classes")
    frame = pd.DataFrame({"id": ids, "label": truth})
    if stratify and frame.groupby("id").label.nunique().gt(1).any():
        raise ValueError("Conflicting class labels within an identity")
    unique, group = np.unique(ids, return_inverse=True)
    class_index = {c: i for i, c in enumerate(classes)}
    y, pred = [np.array([class_index[c] for c in a]) for a in [truth, predicted]]
    cells = np.zeros((len(unique), len(classes), len(classes)))
    np.add.at(cells, (group, y, pred), 1)
    identity_labels = (
        frame.drop_duplicates("id").set_index("id").loc[unique].label.to_numpy()
    )
    rng = np.random.default_rng(seed)
    weights = np.zeros((replicates, len(unique)), int)
    strata = (
        [np.flatnonzero(identity_labels == c) for c in classes]
        if stratify
        else [np.arange(len(unique))]
    )
    for members in strata:
        if len(members):
            draws = rng.choice(members, size=(replicates, len(members)), replace=True)
            for r in range(replicates):
                weights[r] += np.bincount(draws[r], minlength=len(unique))
    matrices = (weights @ cells.reshape(len(unique), -1)).reshape(
        replicates, len(classes), len(classes)
    )
    support = matrices.sum(2)
    recall = np.divide(
        np.diagonal(matrices, axis1=1, axis2=2),
        support,
        out=np.full_like(support, np.nan),
        where=support > 0,
    )
    return np.nanmean(recall, axis=1)


def class_prototypes(
    values, labels, identities, *, method="medoid", count=1, seed=20261014
):
    """Training-only empirical class representatives; never a purity certificate.

    Supply one row per training identity in the chosen spectral metric. Mean and
    median are synthetic prototypes; medoid/diversity/cluster_medoid are observed
    rows. cluster_medoid is a KMeans-nearest-observation adaptation, not global PAM.
    Returns spectra, labels and source row positions (-1 for synthetic centers).
    """
    X, y, ids = np.asarray(values, float), np.asarray(labels), np.asarray(identities)
    if (
        X.ndim != 2
        or len(X) != len(y)
        or len(ids) != len(y)
        or not np.isfinite(X).all()
        or count < 1
    ):
        raise ValueError("Aligned finite prototype data and positive count required")
    if len(np.unique(ids)) != len(ids):
        raise ValueError("Prototype candidates must have distinct identities")
    if method not in {"mean", "median", "medoid", "diversity", "cluster_medoid"}:
        raise ValueError("Unknown prototype method")
    if method in {"mean", "median", "medoid"} and count != 1:
        raise ValueError("Single-center methods require count=1")
    spectra, classes, positions = [], [], []
    for label in np.unique(y):
        ix = np.flatnonzero(y == label)
        if len(ix) < count:
            raise ValueError("Insufficient independent prototype candidates")
        # Source identity ordering determines exact-distance ties, not row order.
        ix = ix[np.argsort(ids[ix])]
        a = X[ix]
        if method in {"mean", "median"}:
            spectra.append(a.mean(0) if method == "mean" else np.median(a, axis=0))
            positions.append(-1)
            classes.append(label)
            continue
        distance = cdist(a, a)
        first = int(np.argmin(distance.mean(1)))
        chosen = [first]
        if method == "diversity":
            while len(chosen) < count:
                score = distance[:, chosen].min(1)
                score[chosen] = -np.inf
                chosen.append(int(np.argmax(score)))
        elif method == "cluster_medoid":
            from sklearn.cluster import KMeans

            model = KMeans(n_clusters=count, n_init=10, random_state=seed).fit(a)
            chosen = []
            for center in model.cluster_centers_:
                order = np.argsort(np.sum((a - center) ** 2, axis=1), kind="stable")
                chosen.append(next(int(v) for v in order if v not in chosen))
        for j in chosen:
            spectra.append(a[j])
            classes.append(label)
            positions.append(int(ix[j]))
    return np.asarray(spectra), np.asarray(classes), np.asarray(positions, int)


def fit_novelty_space(training):
    """Training-only scaled PCA novelty scores; no Gaussian/outlier guarantee."""
    from sklearn.decomposition import PCA

    X = np.asarray(training, float)
    if X.ndim != 2 or len(X) < 3 or not np.isfinite(X).all():
        raise ValueError("Finite proper-training spectra required")
    scaler = StandardScaler().fit(X)
    scaled = scaler.transform(X)
    count = min(20, len(X) - 1, X.shape[1])
    pca = PCA(n_components=count, svd_solver="full").fit(scaled)
    return scaler, pca


def novelty_scores(values, training, space):
    """Nearest angle/distance and PCA radius/reconstruction residual.

    All geometry comes from supplied proper training, not final/unknown targets.
    Distances are exploratory diagnostics calibrated on separate known identities.
    """
    X, T = np.asarray(values, float), np.asarray(training, float)
    if (
        X.ndim != 2
        or T.ndim != 2
        or X.shape[1] != T.shape[1]
        or not np.isfinite(X).all()
        or not np.isfinite(T).all()
    ):
        raise ValueError("Aligned finite novelty spectra required")
    normX, normT = np.linalg.norm(X, axis=1), np.linalg.norm(T, axis=1)
    if np.any(normX <= 0) or np.any(normT <= 0):
        raise ValueError("Zero spectra cannot support spectral angle")
    similarity = (X / normX[:, None]) @ (T / normT[:, None]).T
    angle = np.degrees(np.arccos(np.clip(similarity.max(1), -1, 1)))
    distance = cdist(X, T).min(1) / np.sqrt(X.shape[1])
    scaler, pca = space
    scaled = scaler.transform(X)
    scores = pca.transform(scaled)
    radius = np.sqrt(
        np.sum(scores**2 / np.maximum(pca.explained_variance_, 1e-12), axis=1)
    )
    residual = np.sqrt(np.mean((scaled - pca.inverse_transform(scores)) ** 2, axis=1))
    return dict(
        nearest_angle_deg=angle,
        nearest_RMSE=distance,
        PCA_radius=radius,
        PCA_residual=residual,
    )
