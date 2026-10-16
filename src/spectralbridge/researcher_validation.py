"""Bounded controls for researcher-category identification, not field validation."""

from __future__ import annotations

import numpy as np
from spectralbridge.researcher_information import identity_weights


def random_feature_path(coordinates, seed):
    """Uniform nested subsets, independent of spectra, labels and target outcomes."""
    if coordinates < 1:
        raise ValueError("At least one coordinate required")
    return np.random.default_rng(seed).permutation(coordinates)


def identity_correctness(truth, predicted, identities):
    """Per-ID correctness; repeated acquisitions cannot inflate biological weight."""
    import pandas as pd

    frame = pd.DataFrame(
        {
            "GlobalID": identities,
            "truth": truth,
            "correct": np.asarray(truth) == np.asarray(predicted),
        }
    )
    if frame.groupby("GlobalID").truth.nunique().gt(1).any():
        raise ValueError("Conflicting identity labels")
    return frame.groupby(["GlobalID", "truth"], as_index=False).correct.mean()


def balanced_accuracy(truth, predicted, identities):
    y, p = np.asarray(truth), np.asarray(predicted)
    w = identity_weights(identities)
    return float(
        np.mean([np.average(p[y == c] == c, weights=w[y == c]) for c in np.unique(y)])
    )


def paired_identity_interval(frame, left="selected", right="random", draws=999, seed=0):
    """Stratified whole-ID bootstrap of paired, fixed-rule balanced-accuracy gain."""
    if frame.GlobalID.duplicated().any():
        raise ValueError("One contribution per independent identity required")
    rng = np.random.default_rng(seed)
    differences = []
    observed = []
    for _, g in frame.groupby("truth", sort=True):
        d = (g[left] - g[right]).to_numpy(float)
        observed.append(d.mean())
        differences.append(rng.choice(d, (draws, len(d)), replace=True).mean(axis=1))
    values = np.mean(differences, axis=0)
    lo, hi = np.quantile(values, [0.025, 0.975])
    return dict(difference=float(np.mean(observed)), low=float(lo), high=float(hi))
