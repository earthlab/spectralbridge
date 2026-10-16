"""Combine machine-precision-equivalent truth-grid bins with their actual counts."""

import numpy as np
import pandas as pd
from run_controls import BASE, PRIOR


def collapse_fraction_grid(frame):
    """Count-weighted moments preserve equivalent groups and RMS errors."""
    f = frame.copy()
    f["nominal_fraction"] = f.true_fraction.round(10)
    assert np.max(abs(f.nominal_fraction - f.true_fraction)) < 1e-9
    keys = [
        "fold",
        "kind",
        "target",
        "method",
        "representation",
        "researcher_category",
        "nominal_fraction",
    ]
    rows = []
    for key, g in f.groupby(keys, sort=True):
        row = dict(zip(keys, key))
        row["true_fraction"] = row.pop("nominal_fraction")
        row["N"] = int(g.N.sum())
        for col in ["prediction_mean", "bias", "MAE", "detection_probability"]:
            row[col] = np.average(g[col], weights=g.N)
        row["RMSE"] = np.sqrt(np.average(g.RMSE**2, weights=g.N))
        rows.append(row)
    result = pd.DataFrame(rows)
    assert int(result.N.sum()) == int(f.N.sum())
    return result


def main():
    result = collapse_fraction_grid(
        pd.read_csv(PRIOR / "tables/abundance_by_true_fraction.csv")
    )
    result.to_csv(BASE / "tables/fraction_grid_calibration.csv", index=False)
    print(
        "Count-weighted nominal-grid calibration:",
        len(result),
        "rows; all original observations retained.",
    )


if __name__ == "__main__":
    main()
