"""Reproduce the prespecified mean-versus-median aggregation sensitivity."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import WORK, write  # noqa: E402
from spectralbridge.library_analysis import evaluate_identifiability  # noqa: E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa: E402


def main():
    cfg = json.loads((HERE / "branches.json").read_text())
    index = pd.read_parquet(cfg["polygon_index"])
    support = np.load(WORK / "common.npy")
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    keep = support[rr, cc]
    predictions = []
    summary = []
    for name, meta in cfg["branches"].items():
        a = np.load(meta["path"], mmap_mode="r")
        v = a[rr, cc]
        rows = []
        for identity, g in index.groupby("GlobalID", sort=True):
            z = g.index.to_numpy()
            z = z[keep[z]]
            if len(z):
                rows.append(
                    dict(
                        identity=identity,
                        label=g.cover_category.iloc[0],
                        spectrum=np.median(v[z].astype(float), axis=0),
                    )
                )
        frame = pd.DataFrame(rows).sort_values("identity")
        x = np.stack(frame.spectrum)
        y = frame.label.to_numpy()
        ids = frame.identity.to_numpy()
        result = evaluate_identifiability(
            x, y, groups=ids, folds=3, regularization=(1,), seed=20261103
        )
        summary.append(
            dict(
                branch=name,
                **result["overall"],
                identities=len(ids),
                class_support=frame.label.value_counts().to_dict(),
            )
        )
        pred = result["predictions"].copy()
        pred["branch"] = name
        predictions.append(pred)
    preds = pd.concat(predictions)
    gains = []
    for name in cfg["branches"]:
        p = preds[preds.branch == "raw"].merge(
            preds[preds.branch == name],
            on=["identity", "truth"],
            suffixes=("_raw", "_other"),
        )
        z = pd.DataFrame(
            dict(
                GlobalID=p.identity,
                truth=p.truth,
                selected=(p.prediction_other == p.truth).astype(float),
                random=(p.prediction_raw == p.truth).astype(float),
            )
        )
        gains.append(
            dict(
                branch=name,
                **paired_identity_interval(z, draws=1999, seed=20261103),
                changed_predictions=int((p.prediction_raw != p.prediction_other).sum()),
            )
        )
    write("median_classification_summary.json", summary)
    write("median_paired_gain.json", gains)


if __name__ == "__main__":
    main()
