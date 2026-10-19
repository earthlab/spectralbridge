"""Composable spectral-library methods, independent of the repository study.

Install ``earthlab-spectralbridge[analytics]``. Arrays use observations by features;
units and wavelength support must be common. No routine establishes field cover,
physical calibration or universal ecological transfer. See the scientific API guide.
"""

from itertools import combinations
import numpy as np
import pandas as pd

__all__ = [
    "spectral_separability",
    "evaluate_identifiability",
    "evaluate_feature_budget",
    "compare_representations",
    "generate_mixtures",
    "constrained_unmixing",
    "fit_mesma",
    "candidate_ambiguity",
    "fit_ridge_fractions",
    "project_simplex",
    "fraction_diagnostics",
    "evaluate_library_size",
]


def _matrix(values, name="spectra"):
    x = np.asarray(values, float)
    if x.ndim != 2 or not all(x.shape) or not np.isfinite(x).all():
        raise ValueError(
            f"{name} must be a nonempty finite observations-by-features matrix"
        )
    return x


def _vector(values, n, name):
    v = np.asarray(values)
    if v.shape != (n,) or pd.isna(v).any():
        raise ValueError(f"{name} must be an aligned nonmissing vector")
    return v


def _classes(labels, order=None):
    classes = np.unique(labels) if order is None else np.asarray(order)
    if (
        classes.ndim != 1
        or len(np.unique(classes)) != len(classes)
        or set(classes) != set(labels)
    ):
        raise ValueError("class_order must contain every label exactly once")
    return classes


def _fractions(values, name="fractions"):
    f = _matrix(values, name)
    if np.any(f < 0) or not np.allclose(f.sum(1), 1, atol=1e-10, rtol=0):
        raise ValueError(f"{name} must be nonnegative sum-one fractions")
    return f


def project_simplex(values):
    """Enforce Euclidean nonnegative sum-one fraction geometry.

    Parameters
    ----------
    values : array-like
        Finite vector (C,) or matrix (N, C) of fraction coordinates for row-wise Euclidean projection onto the nonnegative sum-one simplex.

    Returns
    -------
    numpy.ndarray
        Same-shaped array of row-wise projected fractions; nonnegative coordinates sum to one but need not be uniquely physically identifiable.

    Notes
    -----
    Inputs: finite vector (C,) or matrix (N,C); C >= 1. Sampling unit: each row.
    Outputs: same-shaped projected array. Assumptions: Euclidean distance and
    common fraction coordinates. Does not add information or establish uniqueness
    of a physical inversion. Reuses the audited sorting implementation.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> projected = api.project_simplex([-1., 2.])
    >>> assert np.allclose(projected, [0., 1.])
    """
    from .researcher_information import project_simplex as project

    x = np.asarray(values, float)
    vector = x.ndim == 1
    a = _matrix(x[None, :] if vector else x, "values")
    # Projection is invariant to a shared row shift. Coordinates more than one
    # below the maximum cannot be active on a unit simplex. This stabilization
    # avoids losing the unit mass when all raw predictions have a huge offset.
    with np.errstate(over="ignore"):
        centered = np.maximum(a - a.max(axis=1, keepdims=True), -1.0)
    result = np.ones_like(a) if a.shape[1] == 1 else project(centered)
    return result[0] if vector else result


def spectral_separability(
    spectra,
    labels,
    wavelengths,
    groups=None,
    *,
    blocks=None,
    mask=None,
    regions=None,
    permutations=999,
    seed=0,
    max_gap=8,
    missing="raise",
    integration_weights=None,
    maximum_units=5000,
):
    """Test pairwise conditional whole-spectrum differences, not prediction.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    wavelengths : array-like
        Finite wavelength coordinates in nanometers, aligned with spectral columns; numerical analysis routines require strictly increasing unique coordinates.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    blocks : array-like, default=None
        Aligned exchangeability strata for restricted curve permutations; labels must be exchangeable within retained mixed blocks.
    mask : array-like, default=None
        Boolean wavelength vector (B,), True for admitted common support; atmospheric and unsupported gaps should be excluded explicitly.
    regions : dict, default=None
        Optional mapping from region names to (lower, upper) wavelength bounds in nanometers; gaps remain disconnected.
    permutations : int, default=999
        Number of seeded restricted random permutations; spectral_separability requires at least 19.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.
    max_gap : float, default=8
        Maximum wavelength gap in nanometers treated as contiguous during integration; larger gaps are not bridged.
    missing : {'raise', 'drop_columns'}, default='raise'
        Nonfinite-value policy: 'raise' rejects missing support; 'drop_columns' removes incomplete columns globally before aggregation.
    integration_weights : array-like or None, default=None
        Optional positive quadrature weights aligned with wavelengths, expressing the declared support measure rather than sampling density.
    maximum_units : int, default=5000
        Maximum independent mean curves allowed in the quadratic energy-distance calculation; an explicit memory/runtime guard.

    Returns
    -------
    dict
        Pair-test, wavelength and region DataFrames plus retained-coordinate and multiplicity metadata; effect direction is second label minus first.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: spectra (N,B), labels (N,), strictly increasing wavelengths (B,);
    groups are observation identities, blocks are exchangeability strata. Optional
    boolean mask keeps supported coordinates; regions maps names to (low,high).
    Sampling unit: one identity mean curve; repeated identities must have constant
    labels/blocks. Without groups each row is an independent sampling unit.
    Outputs: dict of pair, wavelength and region DataFrames plus support metadata.
    Signed effects are second-minus-first labels; standardized effects divide by
    within-block response scale (not Cohen's d). Synchronized curve permutations
    within each pair preserve covariance across wavelengths. Max-statistic p-values
    control coordinates within pair; Bonferroni then controls all declared pairs.
    Whole-spectrum p-values use Holm across pairs separately for each statistic.
    Assumptions: exchangeable identities within mixed blocks; fixed support/units.
    Energy distances scale quadratically in unit count; maximum_units guards this.
    Missing='drop_columns' removes incomplete columns globally before aggregation;
    default rejects nonfinite values on requested support. Atmospheric gaps must be
    masked explicitly. Region effects use disconnected quadrature, not gap bridges.
    Does not establish classification, abundance, causality or universal difference.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> rng = np.random.default_rng(13)
    >>> labels = np.repeat(["A", "B", "C"], 12)
    >>> spectra = np.repeat(np.eye(3), 12, axis=0) + rng.normal(0, .01, (36, 3))
    >>> identities = np.arange(36)
    >>> result = api.spectral_separability(spectra, labels, [500., 505., 510.], identities, permutations=19)
    >>> assert len(result["pairs"]) == 3
    """
    from .pft_method_audit import method_statistics, AuditConfig, wavelength_weights
    from .plant_pft_statistics import holm

    if not isinstance(permutations, (int, np.integer)) or permutations < 19:
        raise ValueError("permutations must be an integer >=19")
    if not np.isfinite(max_gap) or max_gap <= 0:
        raise ValueError("max_gap must be positive and finite")
    if not isinstance(maximum_units, (int, np.integer)) or maximum_units < 2:
        raise ValueError("maximum_units must be an integer >=2")
    x = np.asarray(spectra, float)
    if x.ndim != 2 or not all(x.shape):
        raise ValueError("spectra must be a nonempty matrix")
    y = _vector(labels, len(x), "labels")
    w = np.asarray(wavelengths, float)
    if w.shape != (x.shape[1],) or not np.isfinite(w).all() or np.any(np.diff(w) <= 0):
        raise ValueError("wavelengths must be finite, unique and strictly increasing")
    keep = np.ones(len(w), bool) if mask is None else np.asarray(mask)
    if keep.shape != w.shape or keep.dtype != bool:
        raise ValueError("mask must be a boolean wavelength vector")
    if missing not in {"raise", "drop_columns"}:
        raise ValueError("missing must be raise or drop_columns")
    if missing == "drop_columns":
        keep = keep & np.isfinite(x).all(0)
    if not np.isfinite(x[:, keep]).all() or keep.sum() < 2:
        raise ValueError("Need at least two finite supported wavelengths")
    ids = np.arange(len(x)) if groups is None else _vector(groups, len(x), "groups")
    b = np.zeros(len(x), int) if blocks is None else _vector(blocks, len(x), "blocks")
    if len(np.unique(ids)) > maximum_units:
        raise ValueError(
            "Independent unit budget exceeded; declare maximum_units explicitly"
        )
    units, yy, bb = [], [], []
    for identity in np.unique(ids):
        use = ids == identity
        if len(np.unique(y[use])) != 1 or len(np.unique(b[use])) != 1:
            raise ValueError("Each identity must have constant label and block")
        units.append(x[use][:, keep].mean(0))
        yy.append(y[use][0])
        bb.append(b[use][0])
    x, y, b = np.asarray(units), np.asarray(yy), np.asarray(bb)
    original = np.flatnonzero(keep)
    w = w[keep]
    iw = None
    if integration_weights is not None:
        iw = np.asarray(integration_weights, float)
        if iw.shape != keep.shape:
            raise ValueError("integration_weights must align with wavelengths")
        iw = iw[keep]
    pairs = list(combinations(np.unique(y), 2))
    if not pairs:
        raise ValueError("Need at least two labelled groups")
    pair_rows, curve_rows, region_rows = [], [], []
    for a, c in pairs:
        use = np.isin(y, [a, c])
        result = method_statistics(
            x[use],
            (y[use] == c).astype(int),
            b[use],
            w,
            config=AuditConfig(
                permutations=permutations, seed=seed, max_gap_nm=max_gap
            ),
            integration_weights=iw,
        )
        col = result["columns"]
        effect = result["curves"][0]
        observed = np.abs(effect / result["se"])
        maxima = result["stats"][1:, 0]
        p = (1 + (maxima[:, None] >= observed[None, :] - 1e-12).sum(0)) / (
            permutations + 1
        )
        z = y[use][result["rows"]]
        row = dict(
            first=a,
            second=c,
            n_first=int((z == a).sum()),
            n_second=int((z == c).sum()),
            max_statistic=result["stats"][0, 0],
            integrated_statistic=result["stats"][0, 1],
        )
        row.update({f"p_{k}": v for k, v in result["p"].items()})
        pair_rows.append(row)
        for j, k in enumerate(col):
            curve_rows.append(
                dict(
                    first=a,
                    second=c,
                    wavelength=w[k],
                    column=int(original[k]),
                    signed_effect=effect[j],
                    standardized_effect=effect[j] / result["scale"][j],
                    p_max=p[j],
                    p_adjusted=min(1, p[j] * len(pairs)),
                )
            )
        for name, limits in (regions or {}).items():
            if len(limits) != 2 or limits[0] > limits[1]:
                raise ValueError("Each region requires ordered lower/upper bounds")
            selected = (w[col] >= limits[0]) & (w[col] <= limits[1])
            if selected.sum() < 2:
                continue
            weights = wavelength_weights(w[col][selected], max_gap)
            region_rows.append(
                dict(
                    first=a,
                    second=c,
                    region=name,
                    signed_effect=float(weights @ effect[selected]),
                    integrated_squared_standardized_effect=float(
                        weights @ (effect[selected] / result["scale"][selected]) ** 2
                    ),
                )
            )
    table = pd.DataFrame(pair_rows)
    for method in ("max", "integrated", "npc", "energy", "fpca"):
        table[f"p_{method}_holm"] = holm(table[f"p_{method}"].to_numpy())
    return dict(
        pairs=table,
        wavelengths=pd.DataFrame(curve_rows),
        regions=pd.DataFrame(region_rows),
        retained_columns=original,
        sampling_unit="identity mean curve",
        multiplicity="coordinate max within pair; Bonferroni pairs; Holm whole-spectrum pairs per method",
    )


def generate_mixtures(
    spectra,
    labels,
    parent_ids,
    *,
    pair_grid=(0, 0.1, 0.5, 0.9, 1),
    triple_grid=((1 / 3, 1 / 3, 1 / 3),),
    replicates=1,
    seed=0,
    class_order=None,
    parent_roles=None,
    maximum_mixtures=100000,
):
    """Generate reproducible pair/triple linear mixtures and exact generating weights.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    parent_ids : array-like
        Unique identifiers for candidate parent spectra; aggregate repeated parents before generating mixtures.
    pair_grid : sequence of float, default=(0, 0.1, 0.5, 0.9, 1)
        Fractions in [0, 1] used for two-parent mixtures; the complementary fraction is one minus the supplied value.
    triple_grid : sequence of 3-element sequences, default=((1 / 3, 1 / 3, 1 / 3),)
        Sequence of three-element nonnegative sum-one fraction vectors; an empty sequence disables three-parent mixtures.
    replicates : int, default=1
        Positive number of seeded repetitions for parent selection or library-size sampling.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.
    parent_roles : array-like or None, default=None
        Optional role labels aligned with candidate parents; retained as provenance alongside generating weights.
    maximum_mixtures : int, default=100000
        Positive upper limit on generated synthetic mixtures; prevents accidental combinatorial expansion.

    Returns
    -------
    dict
        Synthetic spectra, exact class fractions, classes and padded parent indices/IDs/categories/roles/fractions; shared parents imply dependence.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: finite parent spectra (P,B), labels/parent_ids (P,), explicit pair scalar
    fractions and triple simplex vectors; triple_grid=() disables triples.
    Sampling unit: synthetic mixture; shared parent mixtures are dependent.
    Outputs: spectra, truth in classes order, padded parent indices/IDs/categories/roles and
    parent fractions; zero-weight parents remain tracked for conservative holdout.
    Assumptions: one common spectral support/scale and ideal algebraic mixing.
    Does not establish physical mixing, parent purity or independent field truth.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> result = api.generate_mixtures(np.eye(2), ["A", "B"], ["p1", "p2"], pair_grid=(.25,), triple_grid=())
    >>> assert np.allclose(result["truth"].sum(axis=1), 1)
    """
    x = _matrix(spectra)
    y = _vector(labels, len(x), "labels")
    ids = _vector(parent_ids, len(x), "parent_ids")
    classes = _classes(y, class_order)
    if len(np.unique(ids)) != len(ids):
        raise ValueError("Parent IDs must be unique; aggregate repeated parents first")
    roles = (
        np.repeat("unspecified", len(x))
        if parent_roles is None
        else _vector(parent_roles, len(x), "parent_roles")
    )
    if not isinstance(replicates, (int, np.integer)) or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    if not isinstance(maximum_mixtures, (int, np.integer)) or maximum_mixtures < 1:
        raise ValueError("maximum_mixtures must be a positive integer")
    pg = np.asarray(pair_grid, float)
    if pg.ndim != 1 or not np.isfinite(pg).all() or np.any((pg < 0) | (pg > 1)):
        raise ValueError("pair_grid must contain finite fractions in [0,1]")
    tg = np.asarray(triple_grid, float)
    if tg.size:
        _fractions(tg, "triple_grid")
    if tg.size and tg.shape[1] != 3:
        raise ValueError("triple_grid requires three columns")
    rng = np.random.default_rng(seed)
    records = []
    truth = []
    sources = []
    fs = []
    for size, grid in [(2, [(f, 1 - f) for f in pg]), (3, tg)]:
        for comp in combinations(range(len(classes)), size):
            if len(records) + replicates * len(grid) > maximum_mixtures:
                raise ValueError("Mixture budget exceeded")
            for _ in range(replicates):
                ix = np.array(
                    [rng.choice(np.flatnonzero(y == classes[j])) for j in comp]
                )
                for f in grid:
                    t = np.zeros(len(classes))
                    t[list(comp)] = f
                    records.append(np.asarray(f) @ x[ix])
                    truth.append(t)
                    sources.append(np.pad(ix, (0, 3 - size), constant_values=-1))
                    fs.append(np.pad(f, (0, 3 - size)))
    if not records:
        raise ValueError("No mixtures: need two classes and a nonempty grid")
    sources = np.asarray(sources)
    valid = sources >= 0
    pid = np.full(sources.shape, None, object)
    role = pid.copy()
    category = pid.copy()
    category[valid] = y[sources[valid]]
    pid[valid] = ids[sources[valid]]
    role[valid] = roles[sources[valid]]
    return dict(
        spectra=np.asarray(records),
        truth=np.asarray(truth),
        classes=classes,
        parent_indices=sources,
        parent_ids=pid,
        parent_categories=category,
        parent_roles=role,
        parent_fractions=np.asarray(fs),
    )


def constrained_unmixing(targets, endmembers, *, endmember_ids=None):
    """Fit nonnegative sum-one FCLS using the existing small-library face solver.

    Parameters
    ----------
    targets : array-like
        Finite target spectra (N, B) sharing the endmember library wavelength support and reflectance units.
    endmembers : array-like
        Finite reference matrix (M, B), one reference per row; constrained_unmixing admits at most 12 references.
    endmember_ids : array-like or None, default=None
        Optional unique identifiers aligned with reference rows; None uses row indices.

    Returns
    -------
    dict
        Endmember-ordered fractions, reconstruction, RMSE, reference IDs and solver details for each target.

    Raises
    ------
    RuntimeError
        If required processing or artifact validation cannot complete.
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: targets (N,B), ordered endmembers (M,B), M<=12; optional unique IDs.
    Sampling unit: target spectrum. Outputs: fractions in supplied endmember order,
    reconstruction, RMSE, IDs and solver details. Assumptions: common units/support,
    admitted numerical faces/rank thresholds of mixtures.fcls (not exact arithmetic).
    Does not establish unique composition or biological truth from good residuals.

    See Also
    --------
    spectralbridge.library_analysis.fit_mesma : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> result = api.constrained_unmixing([[.25, .75]], np.eye(2))
    >>> assert np.allclose(result["fractions"], [[.25, .75]])
    """
    from .mixtures import fcls

    e = _matrix(endmembers, "endmembers")
    x = _matrix(targets, "targets")
    ids = (
        np.arange(len(e))
        if endmember_ids is None
        else _vector(endmember_ids, len(e), "endmember_ids")
    )
    if len(np.unique(ids)) != len(ids):
        raise ValueError("endmember_ids must be unique")
    if e.shape[1] < 2 or e.shape[1] != x.shape[1]:
        raise ValueError("Need common support of at least two bands")
    result = fcls(x, e)
    result["endmember_ids"] = ids.copy()
    if not np.isfinite(result["RMSE"]).all():
        raise RuntimeError("No finite admitted FCLS solution")
    return result


def candidate_ambiguity(fractions, errors, *, tolerance=0.01, class_order=None):
    """Summarize fraction variation among evaluated near-best candidate solutions.

    Parameters
    ----------
    fractions : array-like
        Nonnegative sum-one fraction coordinates, with classes/endmembers in the declared column order; shape requirements are given in Notes.
    errors : array-like
        Finite nonnegative reconstruction RMSE for each candidate composition, in the same target reflectance units.
    tolerance : float, default=0.01
        Absolute numerical tolerance in the compared quantity: reflectance for chunk checks, additive RMSE for candidate ambiguity.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.

    Returns
    -------
    dict
        Best and near-best candidate indices/compositions, per-class ranges and maximum range; uncertainty covers evaluated candidates only.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: simplex fractions (K,C) and nonnegative reconstruction RMSE (K,);
    tolerance is additive in those RMSE units. Sampling unit: one target's finite
    candidate set. Outputs: best index/fractions, near indices/solutions, per-class
    min/max/range, maximum range (ambiguity_score), near count and alternative count.
    Assumptions: comparable errors, common class order. Stable first-index tie rule.
    Counts refer to evaluated solutions and may include redundant compositions.
    Does not describe exhaustive physical uncertainty or all feasible fractions.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> result = api.candidate_ambiguity([[.2, .8], [.21, .79]], [.01, .015], tolerance=.01)
    >>> assert result["near_count"] == 2
    """
    f = _fractions(fractions)
    e = np.asarray(errors, float)
    if e.shape != (len(f),) or not np.isfinite(e).all() or np.any(e < 0):
        raise ValueError("errors must be finite nonnegative candidate RMSE")
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    classes = np.arange(f.shape[1]) if class_order is None else np.asarray(class_order)
    if classes.shape != (f.shape[1],) or len(np.unique(classes)) != len(classes):
        raise ValueError("class_order must align uniquely with fractions")
    best = int(e.argmin())
    near = np.flatnonzero(e <= e[best] + tolerance)
    low = f[near].min(0)
    high = f[near].max(0)
    return dict(
        best_index=best,
        best_solution=f[best].copy(),
        near_indices=near,
        near_solutions=f[near].copy(),
        ranges=pd.DataFrame(
            {"class": classes, "minimum": low, "maximum": high, "range": high - low}
        ),
        maximum_fraction_range=float((high - low).max()),
        ambiguity_score=float((high - low).max()),
        near_count=len(near),
        alternative_count=len(near) - 1,
        tolerance=tolerance,
    )


def fit_mesma(
    targets,
    endmembers,
    labels,
    *,
    endmember_ids=None,
    max_components=3,
    candidates=None,
    maximum_models=20000,
    tolerance=0.01,
    class_order=None,
):
    """Search explicit candidate models and retain inspectable near-fit compositions.

    Parameters
    ----------
    targets : array-like
        Finite target spectra (N, B) sharing the endmember library wavelength support and reflectance units.
    endmembers : array-like
        Finite reference matrix (M, B), one reference per row; constrained_unmixing admits at most 12 references.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    endmember_ids : array-like or None, default=None
        Optional unique identifiers aligned with reference rows; None uses row indices.
    max_components : int, default=3
        Maximum references per candidate MESMA model, from 1 through 12; zero-weight selected components remain possible.
    candidates : sequence of tuples or None, default=None
        Optional sequence of tuples of zero-based library row indices; None enumerates distinct-category models up to max_components.
    maximum_models : int, default=20000
        Positive upper bound on evaluated candidate models; the search fails explicitly when the requested budget is exceeded.
    tolerance : float, default=0.01
        Absolute numerical tolerance in the compared quantity: reflectance for chunk checks, additive RMSE for candidate ambiguity.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.

    Returns
    -------
    dict
        Class fractions, RMSE/reconstruction, selected references/component fractions, full candidate errors/fractions and ambiguity summaries.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: targets (N,B), library (P,B), category labels/optional IDs (P,);
    candidates is a sequence of tuples of library row indices. Default enumerates
    distinct-category models up to max_components. Sampling unit: target spectrum.
    Outputs: class fractions, selected endmember tuples/fractions, reconstruction,
    RMSE, candidate errors/fractions, ambiguity per target and numerical tolerances.
    Assumptions: finite same-unit library and explicit computational budget; each
    candidate is solved with the existing FCLS face/rank thresholds. Boundaries are
    allowed, so selected tuple can include zero-weight references. Stable first tie.
    Does not establish exhaustive uncertainty, purity or correct biological cover.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> result = api.fit_mesma([[.25, .75]], np.eye(2), ["A", "B"], max_components=2)
    >>> assert np.allclose(result["fractions"], [[.25, .75]])
    """
    from .mixtures import model_indices

    e = _matrix(endmembers, "endmembers")
    x = _matrix(targets, "targets")
    y = _vector(labels, len(e), "labels")
    classes = _classes(y, class_order)
    ids = (
        np.arange(len(e))
        if endmember_ids is None
        else _vector(endmember_ids, len(e), "endmember_ids")
    )
    if len(np.unique(ids)) != len(ids):
        raise ValueError("endmember_ids must be unique")
    if (
        not isinstance(max_components, (int, np.integer))
        or not 1 <= max_components <= 12
    ):
        raise ValueError("max_components must be in [1,12]")
    if not isinstance(maximum_models, (int, np.integer)) or maximum_models < 1:
        raise ValueError("maximum_models must be a positive integer")
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    models = (
        model_indices(y, max_components, maximum_models)
        if candidates is None
        else list(candidates)
    )
    if not models or len(models) > maximum_models:
        raise ValueError("Empty candidate set or model budget exceeded")
    solutions = []
    errors = []
    component_fractions = []
    recon = []
    canonical = []
    for candidate in models:
        ix = np.asarray(candidate)
        if (
            ix.ndim != 1
            or ix.dtype.kind not in "iu"
            or not 1 <= len(ix) <= max_components
            or len(np.unique(ix)) != len(ix)
            or np.any((ix < 0) | (ix >= len(e)))
        ):
            raise ValueError(
                "Each candidate must have unique valid integer indices within max_components"
            )
        ix = np.sort(ix)
        key = tuple(int(i) for i in ix)
        if key in canonical:
            raise ValueError("Duplicate candidate model")
        canonical.append(key)
        fit = constrained_unmixing(x, e[ix])
        f = np.zeros((len(x), len(classes)))
        for j, index in enumerate(ix):
            f[:, np.flatnonzero(classes == y[index])[0]] += fit["fractions"][:, j]
        solutions.append(f)
        errors.append(fit["RMSE"])
        component_fractions.append(fit["fractions"])
        recon.append(fit["reconstruction"])
    fractions = np.stack(solutions, axis=1)
    err = np.column_stack(errors)
    best = err.argmin(1)
    rows = np.arange(len(x))
    return dict(
        classes=classes,
        fractions=fractions[rows, best],
        RMSE=err[rows, best],
        reconstruction=np.stack(recon, axis=1)[rows, best],
        selected_endmembers=[ids[list(canonical[j])].copy() for j in best],
        selected_component_fractions=[
            component_fractions[j][i].copy() for i, j in enumerate(best)
        ],
        candidate_models=canonical,
        candidate_fractions=fractions,
        candidate_RMSE=err,
        ambiguity=[
            candidate_ambiguity(
                fractions[i], err[i], tolerance=tolerance, class_order=classes
            )
            for i in rows
        ],
        tolerances={
            "near_RMSE": tolerance,
            "interior_min_fraction": 1e-9,
            "Gram_absolute": 1e-12,
            "Gram_relative": 1e-10,
            "MSE_update": 1e-14,
        },
    )


# These methods require the declared analytics extra; production imports do not.
from sklearn.base import BaseEstimator, TransformerMixin  # noqa: E402


class _FeaturePath(TransformerMixin, BaseEstimator):
    def __init__(self, count, method="selected", seed=0):
        self.count = count
        self.method = method
        self.seed = seed

    def fit(self, X, y):
        from .researcher_information import orthogonal_feature_path

        path = (
            orthogonal_feature_path(X, y, count=self.count)
            if self.method == "selected"
            else np.random.default_rng(self.seed).permutation(X.shape[1])[: self.count]
        )
        self.indices_ = np.sort(path)
        return self

    def transform(self, X):
        return np.asarray(X)[:, self.indices_]


def _learning_inputs(spectra, labels, groups):
    x = _matrix(spectra)
    y = _vector(labels, len(x), "labels")
    ids = np.arange(len(x)) if groups is None else _vector(groups, len(x), "groups")
    if len(np.unique(y)) < 2:
        raise ValueError("Need at least two classes")
    if pd.DataFrame({"id": ids, "label": y}).groupby("id").label.nunique().gt(1).any():
        raise ValueError("Each observation identity must have one label")
    return x, y, ids


def _splits(x, y, ids, folds, seed, domains=None):
    from sklearn.model_selection import StratifiedGroupKFold
    from .mixtures import validate_holdout

    if domains is None:
        if not isinstance(folds, (int, np.integer)) or folds < 2:
            raise ValueError("folds must be an integer >=2")
        if (
            pd.DataFrame({"id": ids, "y": y})
            .drop_duplicates()
            .groupby("y")
            .size()
            .min()
            < folds
        ):
            raise ValueError(
                "Insufficient independent identities per class for grouped folds"
            )
        raw = [
            (str(i), tr, te)
            for i, (tr, te) in enumerate(
                StratifiedGroupKFold(
                    n_splits=folds, shuffle=True, random_state=seed
                ).split(x, y, ids)
            )
        ]
    else:
        d = _vector(domains, len(x), "domains")
        if len(np.unique(d)) < 2:
            raise ValueError("Need at least two held domains")
        raw = []
        for domain in np.unique(d):
            test = np.flatnonzero(d == domain)
            train = np.flatnonzero(~np.isin(ids, ids[test]))
            raw.append((str(domain), train, test))
    for name, tr, te in raw:
        if not len(tr) or not len(te) or set(y[tr]) != set(y):
            raise ValueError(
                f"Fold {name}: every class must be supported in training after identity purging"
            )
        trmask = np.zeros(len(x), bool)
        temask = trmask.copy()
        trmask[tr] = True
        temask[te] = True
        validate_holdout(ids, trmask, temask)
        yield name, tr, te


def _weights(ids):
    _, inverse, count = np.unique(ids, return_inverse=True, return_counts=True)
    return 1 / count[inverse]


def _classification_fit(
    x,
    y,
    ids,
    *,
    inner_folds,
    regularization,
    seed,
    count=None,
    method="selected",
    pca=None,
):
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.decomposition import PCA

    steps = []
    if count is not None:
        steps.append(("features", _FeaturePath(count, method, seed)))
    steps.append(("scale", StandardScaler()))
    if pca is not None:
        steps.append(("pca", PCA(n_components=pca, svd_solver="full")))
    steps.append(
        (
            "model",
            LogisticRegression(
                class_weight="balanced", max_iter=2000, random_state=seed
            ),
        )
    )
    model = Pipeline(steps)
    grid = np.asarray(regularization, float)
    if (
        grid.ndim != 1
        or not len(grid)
        or not np.isfinite(grid).all()
        or np.any(grid <= 0)
    ):
        raise ValueError("regularization must contain positive finite C values")
    memberships = []
    if len(grid) > 1:
        cv = []
        for name, tr, va in _splits(x, y, ids, inner_folds, seed):
            cv.append((tr, va))
            memberships.append(
                {
                    "fold": name,
                    "train_ids": np.unique(ids[tr]).tolist(),
                    "validation_ids": np.unique(ids[va]).tolist(),
                }
            )
        # Identity-weighted scoring within each inner validation fold.
        # Explicit tuning retains identity-weighted validation metrics.
        from sklearn.base import clone
        from sklearn.metrics import balanced_accuracy_score

        scores = []
        for value in grid:
            fold_scores = []
            for tr, va in cv:
                fitted = (
                    clone(model).set_params(model__C=float(value)).fit(x[tr], y[tr])
                )
                fold_scores.append(
                    balanced_accuracy_score(
                        y[va], fitted.predict(x[va]), sample_weight=_weights(ids[va])
                    )
                )
            scores.append(np.mean(fold_scores))
        selected = float(grid[int(np.argmax(scores))])
    else:
        selected = float(grid[0])
        scores = []
    model.set_params(model__C=selected).fit(x, y)
    return model, dict(C=selected, inner_memberships=memberships, inner_scores=scores)


def evaluate_identifiability(
    spectra,
    labels,
    groups=None,
    *,
    domains=None,
    folds=3,
    inner_folds=3,
    regularization=(0.1, 1, 10),
    seed=0,
    class_order=None,
):
    """Evaluate unseen identities or held domains with nested regularized recognition.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    domains : array-like, default=None
        Optional aligned site/year/domain labels for held-domain evaluation; held identities are purged globally from training.
    folds : int, default=3
        Number of grouped outer evaluation folds, or grouped tuning folds for the ridge fraction estimator; requires enough independent groups.
    inner_folds : int, default=3
        Number of grouped inner training-only folds used for regularization and feature-selection tuning.
    regularization : sequence of positive float, default=(0.1, 1, 10)
        Prespecified positive classifier C values; multiple values trigger grouped inner tuning entirely within training data.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.

    Returns
    -------
    dict
        Grouped fold/overall scores, class recall/confusion, row-aligned predictions/probabilities, tuning memberships and fitted models.

    Notes
    -----
    Inputs: finite spectra (N,B), labels, optional identity groups and site/year
    domains. Sampling unit: identity; repeated histories never cross train/test.
    Outputs: fold/overall balanced accuracy, per-class recall/confusion, predictions,
    class-ordered probabilities, row membership, hyperparameters and fitted models.
    Assumptions: one label per identity, common features; training is row-based,
    metrics identity-weighted. All scale fitting/tuning occurs inside training;
    multi-value regularization requires valid grouped inner folds, else raises.
    Held domains purge target identities globally, even from other training domains.
    Missing values are rejected; probabilities are not calibrated uncertainty.
    Does not establish mixture uniqueness, field fractions or universal transfer.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> rng = np.random.default_rng(13)
    >>> labels = np.repeat(["A", "B", "C"], 12)
    >>> spectra = np.repeat(np.eye(3), 12, axis=0) + rng.normal(0, .01, (36, 3))
    >>> identities = np.arange(36)
    >>> result = api.evaluate_identifiability(spectra, labels, identities, folds=2, regularization=(1,))
    >>> assert "balanced_accuracy" in result["overall"]
    """
    return _evaluate(
        spectra,
        labels,
        groups,
        domains=domains,
        folds=folds,
        inner_folds=inner_folds,
        regularization=regularization,
        seed=seed,
        class_order=class_order,
    )


def _evaluate(
    spectra,
    labels,
    groups,
    *,
    domains,
    folds,
    inner_folds,
    regularization,
    seed,
    class_order=None,
    count=None,
    method="selected",
    pca=None,
):
    from sklearn.metrics import confusion_matrix

    x, y, ids = _learning_inputs(spectra, labels, groups)
    classes = _classes(y, class_order)
    metrics = []
    predictions = []
    members = []
    parameters = []
    models = {}
    conf = []
    selected = []
    for name, tr, te in _splits(x, y, ids, folds, seed, domains):
        model, pars = _classification_fit(
            x[tr],
            y[tr],
            ids[tr],
            inner_folds=inner_folds,
            regularization=regularization,
            seed=seed,
            count=count,
            method=method,
            pca=pca,
        )
        predicted = model.predict(x[te])
        p = model.predict_proba(x[te])
        order = [list(model.classes_).index(c) for c in classes]
        cm = confusion_matrix(
            y[te], predicted, labels=classes, sample_weight=_weights(ids[te])
        )
        conf.append(cm)
        support = cm.sum(1)
        recall = np.divide(
            cm.diagonal(), support, out=np.full(len(classes), np.nan), where=support > 0
        )
        metrics.append(
            dict(
                fold=name,
                balanced_accuracy=float(np.nanmean(recall)),
                n_test_identities=len(np.unique(ids[te])),
                n_classes_test=int((support > 0).sum()),
            )
        )
        for i, row in enumerate(te):
            rec = dict(
                fold=name,
                row=int(row),
                identity=ids[row],
                truth=y[row],
                prediction=predicted[i],
            )
            rec.update({f"score_{j}": p[i, order[j]] for j in range(len(classes))})
            predictions.append(rec)
        for role, ix in [("train", tr), ("test", te)]:
            members.extend(
                dict(fold=name, row=int(j), identity=ids[j], role=role) for j in ix
            )
        parameters.append(dict(fold=name, **pars))
        models[name] = model
        ix = (
            model.named_steps["features"].indices_
            if count is not None
            else np.arange(x.shape[1])
        )
        selected.extend(dict(fold=name, column=int(j)) for j in ix)
    total = np.sum(conf, axis=0)
    support = total.sum(1)
    recall = np.divide(
        total.diagonal(), support, out=np.full(len(classes), np.nan), where=support > 0
    )
    return dict(
        metrics=pd.DataFrame(metrics),
        overall={
            "balanced_accuracy": float(np.nanmean(recall)),
            "mean_fold_balanced_accuracy": float(
                pd.DataFrame(metrics).balanced_accuracy.mean()
            ),
        },
        class_metrics=pd.DataFrame(
            {"class": classes, "recall": recall, "identity_weighted_support": support}
        ),
        confusion=pd.DataFrame(total, index=classes, columns=classes),
        classes=classes,
        predictions=pd.DataFrame(predictions),
        memberships=pd.DataFrame(members),
        hyperparameters=parameters,
        models=models,
        selected_features=pd.DataFrame(selected),
    )


def evaluate_feature_budget(
    spectra,
    labels,
    wavelengths,
    groups=None,
    *,
    budgets=(1, 3, 5),
    random_replicates=3,
    domains=None,
    folds=3,
    inner_folds=3,
    regularization=(0.1, 1, 10),
    seed=0,
    include_full=True,
    pca_components=None,
):
    """Measure predictive information versus feature count with nested selection.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    wavelengths : array-like
        Finite wavelength coordinates in nanometers, aligned with spectral columns; numerical analysis routines require strictly increasing unique coordinates.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    budgets : sequence of int, default=(1, 3, 5)
        Distinct positive feature counts to evaluate, bounded by the available spectral columns.
    random_replicates : int, default=3
        Positive number of seeded label-independent random feature paths; each path is nested across budgets.
    domains : array-like, default=None
        Optional aligned site/year/domain labels for held-domain evaluation; held identities are purged globally from training.
    folds : int, default=3
        Number of grouped outer evaluation folds, or grouped tuning folds for the ridge fraction estimator; requires enough independent groups.
    inner_folds : int, default=3
        Number of grouped inner training-only folds used for regularization and feature-selection tuning.
    regularization : sequence of positive float, default=(0.1, 1, 10)
        Prespecified positive classifier C values; multiple values trigger grouped inner tuning entirely within training data.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.
    include_full : bool, default=True
        Include the full-feature classifier as a reference alongside budget-constrained models.
    pca_components : int or None, default=None
        Optional PCA dimension evaluated using training-only fitted transforms; None omits this comparison.

    Returns
    -------
    dict
        Curve and selected-feature DataFrames plus detailed fold evaluations; selection is refitted within each training fold.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: finite spectra, labels, wavelengths, identities and optional held domains;
    explicit integer budgets, fixed seeded random paths and optional PCA size.
    Sampling unit: held-out identity. Outputs: curve DataFrame, detailed evaluation
    dicts and selected coordinates per outer fold. Selection refits inside every
    inner fold; each random path is label-independent and nested across budgets.
    Assumptions: valid group splits; PCA/scale fitting is training-only. Budgets
    are experimental settings, not chosen from outer scores for final evaluation.
    Does not establish globally optimal bands, a sensor design or field accuracy.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> rng = np.random.default_rng(13)
    >>> labels = np.repeat(["A", "B", "C"], 12)
    >>> spectra = np.repeat(np.eye(3), 12, axis=0) + rng.normal(0, .01, (36, 3))
    >>> identities = np.arange(36)
    >>> result = api.evaluate_feature_budget(spectra, labels, [500., 505., 510.], identities, budgets=(1,), folds=2, regularization=(1,), random_replicates=1)
    >>> assert not result["curve"].empty
    """
    x, y, ids = _learning_inputs(spectra, labels, groups)
    w = np.asarray(wavelengths, float)
    if (
        w.shape != (x.shape[1],)
        or not np.isfinite(w).all()
        or len(np.unique(w)) != len(w)
    ):
        raise ValueError("Unique finite wavelength per column required")
    budgets = list(budgets)
    if len(set(budgets)) != len(budgets):
        raise ValueError("budgets must be unique")
    if not budgets or any(
        not isinstance(k, (int, np.integer)) or not 1 <= k <= x.shape[1]
        for k in budgets
    ):
        raise ValueError("budgets must be integer counts within available features")
    if not isinstance(random_replicates, (int, np.integer)) or random_replicates < 1:
        raise ValueError("random_replicates must be positive")
    details = {}
    curve = []
    features = []
    specs = [("selected", 0, k) for k in budgets] + [
        ("random", j, k) for j in range(random_replicates) for k in budgets
    ]
    if include_full:
        specs.append(("full", 0, x.shape[1]))
    if pca_components is not None:
        specs.append(("PCA", 0, pca_components))
    for method, rep, k in specs:
        control_seed = seed + 1009 * (rep + 1)
        # Separate feature random state from identical outer/inner membership seeds.
        # Each replicate uses one label-independent path across all budgets.
        if method == "random":
            path = np.random.default_rng(control_seed).permutation(x.shape[1])[:k]
            values = x[:, path]
            count = None
        else:
            values = x
            count = k if method == "selected" else None
        result = _evaluate(
            values,
            y,
            ids,
            domains=domains,
            folds=folds,
            inner_folds=inner_folds,
            regularization=regularization,
            seed=seed,
            count=count,
            pca=k if method == "PCA" else None,
        )
        key = f"{method}:{rep}:{k}"
        details[key] = result
        for rec in result["metrics"].to_dict("records"):
            curve.append(dict(method=method, replicate=rep, budget=k, **rec))
        for rec in result["selected_features"].to_dict("records"):
            j = int(path[rec["column"]]) if method == "random" else rec["column"]
            features.append(
                dict(
                    method=method,
                    replicate=rep,
                    budget=k,
                    fold=rec["fold"],
                    column=j,
                    wavelength=w[j],
                    kind="input_support" if method == "PCA" else "selected_coordinate",
                )
            )
    return dict(
        curve=pd.DataFrame(curve),
        selected_features=pd.DataFrame(features),
        evaluations=details,
    )


def compare_representations(
    representations,
    labels,
    groups=None,
    *,
    domains=None,
    reference=None,
    **evaluation_options,
):
    """Compare paired same-row representations under identical grouped splits.

    Parameters
    ----------
    representations : dict
        Mapping of names to finite (N, B) arrays with identical row identity/order; feature counts may differ.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    domains : array-like, default=None
        Optional aligned site/year/domain labels for held-domain evaluation; held identities are purged globally from training.
    reference : str or None, default=None
        Optional representation name used for paired differences; None selects the first supplied representation.
    evaluation_options : keyword arguments
        Additional keyword options forwarded to evaluate_identifiability for each representation; domains must use the explicit argument.

    Returns
    -------
    dict
        Paired score summary, class metrics, detailed evaluations and reference name; synthetic representations remain diagnostic evidence.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: name->(N,B) finite arrays in identical observation order; labels/groups
    and optional held domains. Sampling unit: same held-out identity for every
    representation. Outputs: within and optional held-domain results, recall,
    dimensions, balanced accuracy and transfer penalties; differences vs reference.
    Assumptions: caller guarantees row alignment and paired preprocessing lineage;
    each classifier is separately nested and scaled using training rows only.
    Does not turn synthetic products into independent native-sensor validation.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> rng = np.random.default_rng(13)
    >>> labels = np.repeat(["A", "B", "C"], 12)
    >>> spectra = np.repeat(np.eye(3), 12, axis=0) + rng.normal(0, .01, (36, 3))
    >>> identities = np.arange(36)
    >>> result = api.compare_representations({"full": spectra, "subset": spectra[:, :2]}, labels, identities, folds=2, regularization=(1,))
    >>> assert len(result["summary"]) == 2
    """
    if not representations:
        raise ValueError("Need at least one representation")
    if "domains" in evaluation_options:
        raise ValueError("Pass domains explicitly")
    names = list(representations)
    reference = names[0] if reference is None else reference
    if reference not in representations:
        raise ValueError("Unknown reference representation")
    results = {}
    rows = []
    recalls = []
    for name, values in representations.items():
        x = _matrix(values)
        within = evaluate_identifiability(x, labels, groups, **evaluation_options)
        held = (
            None
            if domains is None
            else evaluate_identifiability(
                x, labels, groups, domains=domains, **evaluation_options
            )
        )
        results[name] = {"unseen_identity": within, "held_domain": held}
        score = within["overall"]["mean_fold_balanced_accuracy"]
        hs = np.nan if held is None else held["overall"]["mean_fold_balanced_accuracy"]
        rows.append(
            dict(
                representation=name,
                dimensions=x.shape[1],
                unseen_identity_BA=score,
                held_domain_BA=hs,
                transfer_penalty=score - hs,
            )
        )
        for kind, result in [("unseen_identity", within), ("held_domain", held)]:
            if result is not None:
                recalls.extend(
                    dict(representation=name, evaluation=kind, **r)
                    for r in result["class_metrics"].to_dict("records")
                )
    summary = pd.DataFrame(rows)
    ref = summary.loc[summary.representation == reference].iloc[0]
    summary["unseen_difference_from_reference"] = (
        summary.unseen_identity_BA - ref.unseen_identity_BA
    )
    summary["held_difference_from_reference"] = (
        summary.held_domain_BA - ref.held_domain_BA
    )
    return dict(
        summary=summary,
        class_metrics=pd.DataFrame(recalls),
        evaluations=results,
        reference=reference,
    )


class _RidgeFractionModel:
    """Fitted numerical state; predict exposes raw and geometrically valid fractions."""

    def __init__(self, pipeline, classes, tuning):
        self.pipeline = pipeline
        self.classes = classes
        self.tuning = tuning
        scale = pipeline.named_steps["scale"]
        ridge = pipeline.named_steps["model"]
        self.preprocessing = {
            "mean": scale.mean_.copy(),
            "scale": scale.scale_.copy(),
            "coefficient": ridge.coef_.copy(),
            "intercept": ridge.intercept_.copy(),
            "alpha": float(ridge.alpha),
            "classes": classes.copy(),
        }

    def predict(self, spectra):
        """Predict raw and simplex-projected fraction coordinates for new spectra.

        Parameters
        ----------
        spectra : array-like
            Finite matrix (N, B) on the training support and scale; fitted training
            preprocessing is reused, rather than refitted on these targets.

        Returns
        -------
        dict
            raw_prediction and projected_prediction arrays (N, C), plus the
            corresponding classes vector (C,). Projection enforces geometry,
            not physical uniqueness or calibrated uncertainty.
        """
        raw = self.pipeline.predict(_matrix(spectra))
        return dict(
            raw_prediction=raw,
            projected_prediction=project_simplex(raw),
            classes=self.classes.copy(),
        )


def fit_ridge_fractions(
    spectra, fractions, groups=None, *, alphas=(1,), folds=3, seed=0, class_order=None
):
    """Fit supervised multi-output ridge with explicit raw/projected predictions.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    fractions : array-like
        Nonnegative sum-one fraction coordinates, with classes/endmembers in the declared column order; shape requirements are given in Notes.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    alphas : sequence of positive float, default=(1,)
        Prespecified positive ridge penalties; multiple penalties require explicit independent parent-connected tuning groups.
    folds : int, default=3
        Number of grouped outer evaluation folds, or grouped tuning folds for the ridge fraction estimator; requires enough independent groups.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.

    Returns
    -------
    object
        Fitted fraction model exposing predict(spectra), raw and simplex-projected predictions, fitted preprocessing/coefficients and tuning metadata.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: spectra (N,B), exact known simplex targets (N,C), positive alpha grid;
    groups are independent parent-connected bundles for synthetic training mixtures.
    Sampling unit: training mixture, with group-disjoint tuning if grid has >1 alpha.
    Outputs: fitted model with predict(), saved preprocessing/coefficient/intercept
    parameters and tuning memberships/scores. StandardScaler is refitted inside
    every tuning fold. Selection minimizes mean raw fraction MSE. Multiple alphas
    require explicit groups and grouped folds; a single alpha is prespecified.
    Assumptions: common units/support and no shared generating parent across groups;
    caller must form connected parent groups, not arbitrary mixture-row IDs.
    Does not establish unique physical inversion, calibrated uncertainty or field
    cover. Prediction returns both raw_prediction and projected_prediction.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> model = api.fit_ridge_fractions(np.eye(2), np.eye(2), alphas=(1,))
    >>> prediction = model.predict([[.25, .75]])
    >>> assert np.allclose(prediction["projected_prediction"].sum(axis=1), 1)
    """
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GroupKFold

    x = _matrix(spectra)
    f = _fractions(fractions)
    if len(f) != len(x):
        raise ValueError("fractions must align with spectra")
    classes = np.arange(f.shape[1]) if class_order is None else np.asarray(class_order)
    if classes.shape != (f.shape[1],) or len(np.unique(classes)) != len(classes):
        raise ValueError("class_order must align uniquely with fraction columns")
    alpha = np.asarray(alphas, float)
    if (
        alpha.ndim != 1
        or not len(alpha)
        or not np.isfinite(alpha).all()
        or np.any(alpha <= 0)
    ):
        raise ValueError("alphas must be positive finite values")

    def pipeline(a):
        return Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=float(a)))])

    records = []
    scores = []
    ids = None if groups is None else _vector(groups, len(x), "groups")
    if len(alpha) > 1:
        if groups is None:
            raise ValueError(
                "Grouped tuning requires explicit independent parent-connected groups"
            )
        if (
            not isinstance(folds, (int, np.integer))
            or folds < 2
            or len(np.unique(ids)) < folds
        ):
            raise ValueError("Insufficient independent groups for ridge tuning")
        cv = list(GroupKFold(n_splits=folds).split(x, f, ids))
        records = [
            dict(
                train_ids=np.unique(ids[tr]).tolist(),
                validation_ids=np.unique(ids[va]).tolist(),
            )
            for tr, va in cv
        ]
        for a in alpha:
            score = []
            for tr, va in cv:
                prediction = pipeline(a).fit(x[tr], f[tr]).predict(x[va])
                score.append(
                    np.average(
                        np.mean((prediction - f[va]) ** 2, axis=1),
                        weights=_weights(ids[va]),
                    )
                )
            scores.append(float(np.mean(score)))
        chosen = float(alpha[int(np.argmin(scores))])
    else:
        chosen = float(alpha[0])
    return _RidgeFractionModel(
        pipeline(chosen).fit(x, f),
        classes,
        dict(alphas=alpha.tolist(), MSE=scores, memberships=records, seed=seed),
    )


def fraction_diagnostics(
    truth,
    predictions,
    *,
    class_order=None,
    detection_threshold=0.1,
    low_fraction=0.2,
    bins=(0, 0.1, 0.25, 0.5, 0.75, 1),
    groups=None,
    bootstraps=0,
    seed=0,
):
    """Separate known-fraction quantification from thresholded detection errors.

    Parameters
    ----------
    truth : array-like
        Known nonnegative sum-one mixture fractions (N, C); these are synthetic targets, not independently measured field cover.
    predictions : array-like
        Finite predicted fraction matrix (N, C), in the same class order as truth; raw unconstrained predictions are accepted.
    class_order : sequence or None, default=None
        Explicit unique class-column order; None uses the function-specific canonical ordering. Preserve this order when comparing fraction arrays.
    detection_threshold : float, default=0.1
        Fraction in (0, 1] at or above which the predicted class is declared detected.
    low_fraction : float, default=0.2
        Upper positive truth-fraction bound in (0, 1] for low-abundance miss-rate summaries.
    bins : sequence of float, default=(0, 0.1, 0.25, 0.5, 0.75, 1)
        Strictly increasing calibration-bin edges spanning zero to one.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    bootstraps : int, default=0
        Nonnegative number of whole-group bootstrap resamples; positive values require at least two explicitly independent groups.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.

    Returns
    -------
    dict
        Overall/per-class fraction errors, calibration bins, absent/low-positive detection summaries and optional whole-group intervals.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: truth (N,C) simplex and finite predictions (N,C), possibly raw;
    class ordering, detection/low-fraction thresholds and calibration bin edges.
    Sampling unit: mixture; supplied independent groups receive equal total weight
    and are resampled whole for percentile intervals on RMSE/bias. Shared parents
    require connected groups. Outputs: macro/per-class RMSE/bias, calibration bins,
    absent false-positive and low-positive miss rates, positive-only RMSE and CIs.
    Assumptions: synthetic truth is known; absent means exactly zero; detection is
    prediction >= threshold. Empty conditional denominators yield NaN. Bootstraps
    require explicit groups. Does not establish biological absence or field accuracy.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> result = api.fraction_diagnostics(np.eye(2), np.eye(2))
    >>> assert result["overall"]["RMSE"] == 0
    """
    t = _fractions(truth, "truth")
    p = _matrix(predictions, "predictions")
    if p.shape != t.shape:
        raise ValueError("truth and predictions must have identical shape")
    classes = np.arange(t.shape[1]) if class_order is None else np.asarray(class_order)
    if classes.shape != (t.shape[1],) or len(np.unique(classes)) != len(classes):
        raise ValueError("class_order must match fraction columns uniquely")
    if not 0 < detection_threshold <= 1 or not 0 < low_fraction <= 1:
        raise ValueError("Fraction thresholds must be in (0,1]")
    edges = np.asarray(bins, float)
    if (
        edges.ndim != 1
        or len(edges) < 2
        or edges[0] != 0
        or edges[-1] != 1
        or np.any(np.diff(edges) <= 0)
    ):
        raise ValueError("bins must increase from zero to one")
    if not isinstance(bootstraps, (int, np.integer)) or bootstraps < 0:
        raise ValueError("bootstraps must be a nonnegative integer")
    if bootstraps and groups is None:
        raise ValueError("Bootstrap uncertainty requires explicit independent groups")
    ids = np.arange(len(t)) if groups is None else _vector(groups, len(t), "groups")
    w = _weights(ids)
    error = p - t
    rows = []
    cal = []

    def avg(v, use):
        return float(np.average(v[use], weights=w[use])) if use.any() else np.nan

    for j, c in enumerate(classes):
        absent = t[:, j] == 0
        positive = t[:, j] > 0
        low = positive & (t[:, j] <= low_fraction)
        rows.append(
            dict(
                class_label=c,
                RMSE=np.sqrt(avg(error[:, j] ** 2, np.ones(len(t), bool))),
                bias=avg(error[:, j], np.ones(len(t), bool)),
                absent_false_positive_rate=avg(
                    (p[:, j] >= detection_threshold).astype(float), absent
                ),
                low_fraction_miss_rate=avg(
                    (p[:, j] < detection_threshold).astype(float), low
                ),
                positive_only_RMSE=np.sqrt(avg(error[:, j] ** 2, positive)),
                n_absent=int(absent.sum()),
                n_low_positive=int(low.sum()),
                n_positive=int(positive.sum()),
            )
        )
        for k, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
            use = (t[:, j] >= left) & (
                (t[:, j] <= right) if k == len(edges) - 2 else (t[:, j] < right)
            )
            cal.append(
                dict(
                    class_label=c,
                    lower=left,
                    upper=right,
                    n=int(use.sum()),
                    mean_truth=avg(t[:, j], use),
                    mean_prediction=avg(p[:, j], use),
                )
            )
    rmse = float(np.sqrt(np.average(np.mean(error**2, axis=1), weights=w)))
    bias = float(np.average(error.mean(1), weights=w))
    intervals = []
    if bootstraps:
        unique = np.unique(ids)
        if len(unique) < 2:
            raise ValueError("Bootstrap needs at least two independent groups")
        rng = np.random.default_rng(seed)
        values = []
        for _ in range(bootstraps):
            sampled = rng.choice(unique, len(unique), replace=True)
            # First reduce each sampled cluster so multiplicity is preserved exactly.
            mse = np.mean([np.mean(error[ids == i] ** 2) for i in sampled])
            b = np.mean([np.mean(error[ids == i]) for i in sampled])
            values.append((np.sqrt(mse), b))
        for j, name in enumerate(["RMSE", "bias"]):
            lower, upper = np.quantile(np.asarray(values)[:, j], [0.025, 0.975])
            intervals.append(dict(metric=name, lower=lower, upper=upper))
    return dict(
        overall={
            "RMSE": rmse,
            "bias": bias,
            "macro_class_RMSE": float(pd.DataFrame(rows).RMSE.mean()),
        },
        per_class=pd.DataFrame(rows),
        calibration=pd.DataFrame(cal),
        intervals=pd.DataFrame(intervals),
        detection_threshold=detection_threshold,
        low_fraction=low_fraction,
    )


def evaluate_library_size(
    spectra,
    labels,
    groups=None,
    *,
    sizes=(10, 20),
    strategies=("balanced_random", "farthest"),
    replicates=3,
    domains=None,
    folds=3,
    seed=0,
):
    """Evaluate retained identity-library capacity with fixed classifier/prior.

    Parameters
    ----------
    spectra : array-like
        Finite observations-by-features matrix (N, B) on a common spectral support and scale; rows must align with labels and identity metadata.
    labels : array-like
        Nonmissing class/category labels with one value per spectrum; repeated identities must have a consistent label.
    groups : array-like, default=None
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.
    sizes : sequence of int, default=(10, 20)
        Positive total counts of retained training identities; each must fit within every evaluated training fold.
    strategies : sequence of str, default=('balanced_random', 'farthest')
        Library selection strategies drawn from 'random', 'balanced_random', and 'farthest'; selection uses training identities only.
    replicates : int, default=3
        Positive number of seeded repetitions for parent selection or library-size sampling.
    domains : array-like, default=None
        Optional aligned site/year/domain labels for held-domain evaluation; held identities are purged globally from training.
    folds : int, default=3
        Number of grouped outer evaluation folds, or grouped tuning folds for the ridge fraction estimator; requires enough independent groups.
    seed : int, default=0
        Random-number seed for reproducible sampling, splits or resampling; it does not create independent observations.

    Returns
    -------
    dict
        Metrics and selected-identity DataFrames plus fixed-classifier description; unsupported classes are explicit rather than scored as valid.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    Inputs: finite spectra/labels/identities; total library sizes, strategies
    random, balanced_random or farthest; optional held-domain metadata.
    Sampling unit: held-out identity; training histories collapse to identity means.
    Outputs: fold/size/strategy/replicate scores, selected IDs and coverage distances.
    Farthest uses training-standardized Euclidean distance, seeded one per class;
    balanced_random cycles classes uniformly. Random is unconditional; missing a
    class produces explicit unsupported status rather than a misleading score.
    Assumptions: fixed C=1 regularized classifier; sizes are predeclared, selection
    and coverage use training rows only. Coverage distances use full-training scale.
    Does not isolate every model/prior confound or establish universal best size.

    See Also
    --------
    spectralbridge.library_analysis.constrained_unmixing : Related source-derived API contract.

    Examples
    --------
    All spectra below are invented teaching data, not empirical validation.

    >>> import numpy as np
    >>> from spectralbridge import library_analysis as api
    >>> rng = np.random.default_rng(13)
    >>> labels = np.repeat(["A", "B", "C"], 12)
    >>> spectra = np.repeat(np.eye(3), 12, axis=0) + rng.normal(0, .01, (36, 3))
    >>> identities = np.arange(36)
    >>> result = api.evaluate_library_size(spectra, labels, identities, sizes=(6,), strategies=("balanced_random",), replicates=1, folds=2)
    >>> assert not result["metrics"].empty
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import balanced_accuracy_score
    from scipy.spatial.distance import cdist

    x, y, ids = _learning_inputs(spectra, labels, groups)
    sizes = list(sizes)
    if not sizes or any(not isinstance(k, (int, np.integer)) or k < 1 for k in sizes):
        raise ValueError("sizes must be positive integers")
    if not strategies or set(strategies) - {"random", "balanced_random", "farthest"}:
        raise ValueError("Unknown library selection strategy")
    if not isinstance(replicates, (int, np.integer)) or replicates < 1:
        raise ValueError("replicates must be positive")
    rows = []
    membership = []
    for name, tr, te in _splits(x, y, ids, folds, seed, domains):
        unique = np.unique(ids[tr])
        xx = np.array([x[tr][ids[tr] == i].mean(0) for i in unique])
        yy = np.array([y[tr][ids[tr] == i][0] for i in unique])
        if max(sizes) > len(unique):
            raise ValueError(f"Library size exceeds training identities in fold {name}")
        z = StandardScaler().fit_transform(xx)
        for strategy in strategies:
            for rep in range(replicates):
                rng = np.random.default_rng(seed + rep)
                chosen = []
                if strategy == "random":
                    path = rng.permutation(len(xx)).tolist()
                elif strategy == "balanced_random":
                    buckets = [
                        rng.permutation(np.flatnonzero(yy == c)).tolist()
                        for c in np.unique(yy)
                    ]
                    path = []
                    while any(buckets):
                        for bucket in buckets:
                            if bucket:
                                path.append(bucket.pop())
                else:
                    chosen = [
                        int(rng.choice(np.flatnonzero(yy == c))) for c in np.unique(yy)
                    ]
                    while len(chosen) < max(sizes):
                        distances = cdist(z, z[chosen]).min(1)
                        distances[chosen] = -np.inf
                        chosen.append(int(distances.argmax()))
                    path = chosen
                for size in sizes:
                    ix = np.asarray(path[:size])
                    distance = cdist(z, z[ix]).min(1)
                    row = dict(
                        fold=name,
                        size=size,
                        strategy=strategy,
                        replicate=rep,
                        mean_coverage_distance=float(distance.mean()),
                        maximum_coverage_distance=float(distance.max()),
                    )
                    if set(yy[ix]) != set(y):
                        row.update(
                            status="unsupported_missing_training_class",
                            balanced_accuracy=np.nan,
                        )
                    else:
                        model, _ = _classification_fit(
                            xx[ix],
                            yy[ix],
                            unique[ix],
                            inner_folds=2,
                            regularization=(1,),
                            seed=seed,
                        )
                        score = balanced_accuracy_score(
                            y[te], model.predict(x[te]), sample_weight=_weights(ids[te])
                        )
                        row.update(status="tested", balanced_accuracy=float(score))
                    rows.append(row)
                    membership.extend(
                        dict(
                            fold=name,
                            size=size,
                            strategy=strategy,
                            replicate=rep,
                            identity=i,
                        )
                        for i in unique[ix]
                    )
    return dict(
        metrics=pd.DataFrame(rows),
        selected_identities=pd.DataFrame(membership),
        model="StandardScaler + balanced logistic, fixed C=1",
    )
