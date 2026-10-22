"""Retain the numerical witnesses behind the compact ambiguity/oracle summaries."""

import numpy as np
import pandas as pd
from run_comparison import OUT, SCHEMES, label_codes, legacy, fcls
import json


def main():
    audit = json.loads((OUT / "input_audit.json").read_text())
    raw = np.load(audit["inputs"]["old_spectra"]["path"], allow_pickle=False).T
    previous = pd.read_csv(OUT / "tables/convex_ambiguity.csv").set_index(
        ["library", "scheme", "array_index"]
    )
    witnesses = []
    for name in ["old", "new"]:
        refs = pd.read_csv(OUT / "tables" / f"{name}_selected_identity.csv")
        e = raw[refs.array_index.to_numpy()]
        for scheme in SCHEMES:
            labels = label_codes(refs.atom.to_numpy(str), scheme)
            for i, target in enumerate(e):
                cert = legacy.cross_class_certificate(target, int(labels[i]), e, labels)
                assert (
                    cert["feasible"]
                    == previous.loc[
                        (name, scheme, int(refs.array_index.iloc[i])), "feasible"
                    ]
                )
                if not cert["feasible"]:
                    continue
                for ix, weight in zip(cert["local_indices"], cert["weights"]):
                    witnesses.append(
                        dict(
                            library=name,
                            scheme=scheme,
                            target_array_index=int(refs.array_index.iloc[i]),
                            alternative_array_index=int(refs.array_index.iloc[ix]),
                            weight=float(weight),
                        )
                    )
    pd.DataFrame(witnesses).to_csv(
        OUT / "tables/convex_certificate_weights.csv", index=False
    )
    meta = pd.read_csv(OUT / "tables/target_membership.csv")
    with np.load(OUT / "synthetic_targets.npz", allow_pickle=False) as z:
        x = z["spectra"]
        truth = z["atomic_truth"]
        parents = z["bundle_parents"]
    fractions = np.zeros_like(truth)
    recon = np.zeros_like(x)
    for bid, reference in enumerate(parents):
        use = meta.bundle.eq(bid).to_numpy()
        fit = fcls(x[use], reference)
        fractions[use] = fit["fractions"]
        recon[use] = fractions[use] @ reference
    np.savez_compressed(
        OUT / "models/known_parent_oracle.npz",
        prediction=fractions,
        reconstruction=recon,
    )
    expected = json.loads((OUT / "oracle.json").read_text())["atomic_fraction_RMSE"]
    assert np.isclose(
        np.sqrt(np.mean((fractions - truth) ** 2)), expected, rtol=1e-9, atol=1e-15
    )
    print(
        f"Saved {len(witnesses)} certificate weights and {len(fractions)} known-parent positive-control predictions; original summaries reproduced."
    )


if __name__ == "__main__":
    main()
