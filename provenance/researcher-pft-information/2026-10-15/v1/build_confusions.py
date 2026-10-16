"""Readable supplementary five-category confusion matrices, PNG/SVG only."""

import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import BASE, save
from spectralbridge.researcher_information import RESEARCHER_CATEGORIES

plt.rcParams.update({"svg.hashsalt": "researcher-confusion-v1", "svg.fonttype": "none"})


def main():
    C = list(RESEARCHER_CATEGORIES)
    current = pd.read_csv(BASE / "tables/confusion_matrices.csv")
    old = pd.read_csv(BASE / "tables/reused_researcher_year_confusion.csv")
    rows = []
    fig, axes = plt.subplots(2, 3, figsize=(14, 10))
    labels = [
        "Deciduous",
        "Evergreen",
        "Herbaceous",
        "Non-vegetated\n& dead",
        "Woody shrub",
    ]
    for row, rep in enumerate(["NEON", "OLI"]):
        for col, kind in enumerate(["plant", "site", "year"]):
            if kind == "year":
                f = old[
                    old.representation.eq("NEON_full" if rep == "NEON" else "OLI")
                ].rename(
                    columns={
                        "true_label": "truth",
                        "predicted_label": "predicted",
                        "N": "count",
                    }
                )
            else:
                f = current[
                    current.kind.eq(kind)
                    & current.budget.eq("360" if rep == "NEON" else "OLI")
                ].rename(columns={"identity_weighted_count": "count"})
            values = []
            for fold, g in f.groupby("fold"):
                m = (
                    g.pivot(index="truth", columns="predicted", values="count")
                    .reindex(index=C, columns=C)
                    .to_numpy()
                )
                values.append(m / np.maximum(m.sum(1, keepdims=True), 1e-15))
            matrix = np.mean(values, axis=0)
            ax = axes[row, col]
            ax.imshow(matrix, vmin=0, vmax=1, cmap="YlGnBu", interpolation="nearest")
            ax.set_title(
                rep
                + " | "
                + {
                    "plant": "new polygon",
                    "site": "held site",
                    "year": "held year (reused)",
                }[kind],
                fontsize=12,
            )
            ax.set_xticks(range(5), labels, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(5), labels if col == 0 else [""] * 5, fontsize=10)
            if col == 0:
                ax.set_ylabel("True researcher category")
            for i, c in enumerate(C):
                for j, d in enumerate(C):
                    ax.text(
                        j,
                        i,
                        f"{matrix[i, j]:.2f}",
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="white" if matrix[i, j] > 0.6 else "black",
                    )
                    rows.append(
                        dict(
                            representation=rep,
                            kind=kind,
                            truth=c,
                            predicted=d,
                            mean_fold_row_fraction=matrix[i, j],
                            source="new_nested_identity_weighted"
                            if kind != "year"
                            else "reused_researcher_logistic_annual_row",
                        )
                    )
    fig.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(
            BASE / "figures" / ("S1_researcher_confusion_matrices." + ext),
            dpi=300,
            bbox_inches="tight",
            metadata={"Date": None} if ext == "svg" else {"Software": "SpectralBridge"},
        )
    plt.close(fig)
    save(pd.DataFrame(rows), "confusion_plot_values.csv")
    info = dict(
        number="S1",
        name="S1_researcher_confusion_matrices",
        caption="Rows are true classes; columns are predictions. Cells are fold-mean row fractions. The year panels reuse the earlier validated researcher-only logistic baseline and annual-row target weighting; new polygon/site panels use the new nested identity-weighted model. These are conditional observed-domain tests.",
        sources=["confusion_matrices.csv", "reused_researcher_year_confusion.csv"],
        hashes={
            ext: hashlib.sha256(
                (
                    BASE / "figures" / ("S1_researcher_confusion_matrices." + ext)
                ).read_bytes()
            ).hexdigest()
            for ext in ["png", "svg"]
        },
    )
    (BASE / "supplementary_figure_manifest.json").write_text(
        json.dumps(info, indent=2) + "\n"
    )
    print("Built six class-specific confusion panels.")


if __name__ == "__main__":
    main()
