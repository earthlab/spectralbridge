"""Small offline lesson: difference -> identity -> synthetic quantity -> ambiguity.

Run: python examples/spectral_library_methods.py
Requires earthlab-spectralbridge[analytics]. All spectra below are invented.
"""

import numpy as np
from spectralbridge.library_analysis import (
    spectral_separability,
    evaluate_identifiability,
    evaluate_feature_budget,
    compare_representations,
    generate_mixtures,
    constrained_unmixing,
    fit_mesma,
    fit_ridge_fractions,
    fraction_diagnostics,
    evaluate_library_size,
)


def main():
    rng = np.random.default_rng(13)
    endmembers = np.array(
        [
            [0.8, 0.1, 0.1, 0.2, 0.3, 0.4],
            [0.1, 0.8, 0.1, 0.4, 0.2, 0.3],
            [0.1, 0.1, 0.8, 0.3, 0.4, 0.2],
        ]
    )
    labels = np.repeat(["A", "B", "C"], 12)
    spectra = np.repeat(endmembers, 12, axis=0) + rng.normal(0, 0.02, (36, 6))
    identities = np.arange(36)
    wavelengths = np.arange(500.0, 506.0)
    sites = np.tile(np.repeat(["north", "south"], 6), 3)
    difference = spectral_separability(
        spectra, labels, wavelengths, identities, permutations=39
    )
    recognition = evaluate_identifiability(
        spectra, labels, identities, folds=2, inner_folds=2
    )
    information = evaluate_feature_budget(
        spectra,
        labels,
        wavelengths,
        identities,
        budgets=(1, 3),
        random_replicates=1,
        folds=2,
        inner_folds=2,
    )
    retention = compare_representations(
        {"full": spectra, "two_channels": spectra[:, :2]},
        labels,
        identities,
        domains=sites,
        folds=2,
        inner_folds=2,
    )
    # Disjoint parent bundles: related mixture rows remain together during tuning.
    mixtures = []
    truth = []
    bundles = []
    for bundle in range(10):
        parents = endmembers + rng.normal(0, 0.015, endmembers.shape)
        result = generate_mixtures(
            parents,
            ["A", "B", "C"],
            [f"{bundle}:{c}" for c in "ABC"],
            parent_roles=["proper_training"] * 3,
            seed=bundle,
        )
        mixtures.extend(result["spectra"])
        truth.extend(result["truth"])
        bundles.extend([bundle] * len(result["truth"]))
    ridge = fit_ridge_fractions(
        mixtures, truth, bundles, alphas=(0.01, 1), folds=2, class_order=["A", "B", "C"]
    )
    # New parent spectra never entered training or tuning.
    target = generate_mixtures(
        endmembers,
        ["A", "B", "C"],
        ["testA", "testB", "testC"],
        parent_roles=["test"] * 3,
    )
    fcls = constrained_unmixing(
        target["spectra"], endmembers, endmember_ids=["testA", "testB", "testC"]
    )
    mesma = fit_mesma(target["spectra"], endmembers, ["A", "B", "C"])
    prediction = ridge.predict(target["spectra"])
    diagnostics = fraction_diagnostics(
        target["truth"], prediction["projected_prediction"]
    )
    capacity = evaluate_library_size(
        spectra, labels, identities, sizes=(6, 12), replicates=1, folds=2
    )
    assert np.max(np.abs(fcls["fractions"] - target["truth"])) < 1e-7
    assert {"raw_prediction", "projected_prediction"} <= prediction.keys()
    print(
        "Difference is not recognition, and synthetic fraction skill is not field cover."
    )
    print("Whole-spectrum pairs:", len(difference["pairs"]))
    print("Recognition BA:", recognition["overall"]["balanced_accuracy"])
    print(retention["summary"].to_string(index=False))
    print("Feature-curve rows:", len(information["curve"]))
    print("Synthetic ridge RMSE:", diagnostics["overall"]["RMSE"])
    print(
        "MESMA evaluated-candidate ambiguity:", mesma["ambiguity"][0]["ambiguity_score"]
    )
    print("Library-size evaluations:", len(capacity["metrics"]))


if __name__ == "__main__":
    main()
