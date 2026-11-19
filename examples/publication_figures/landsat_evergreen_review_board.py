"""Render the dated imagery/lidar review board for the frozen shortlist.

Single-interpreter visual triage remains provisional and never promotes labels.
Run from repository root after point-cloud and Landsat candidate extraction.
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from landsat_evergreen_pointcloud import DEST
from landsat_spatial_expansion import CACHE
from landsat_evergreen_epochs import CACHE as EPOCH_CACHE

f = pd.read_csv(DEST / "landsat_evergreen_structural_candidate_observations.csv")
fig, axes = plt.subplots(3, 3, figsize=(12, 12))
notes = []
for row, (key, g) in enumerate(f.groupby("context_patch_id")):
    m = json.loads((CACHE / f"{key}.json").read_text())
    old = json.loads((EPOCH_CACHE / f"{key}-2019.json").read_text())
    project = g.structural_project.iloc[0]
    grid = np.load(DEST / f"{key}-{project}.npy")
    for col, (array, date) in enumerate(
        [
            (np.load(EPOCH_CACHE / f"{key}-2019.npy"), old["naip_datetime"][:10]),
            (np.load(CACHE / f"{key}.npy"), m["naip_datetime"][:10]),
        ]
    ):
        axes[row, col].imshow(np.moveaxis(array, 0, -1), extent=(-120, 120, -120, 120))
        axes[row, col].set_title(f"{key}\nAerial {date}", fontsize=9)
    axes[row, 2].imshow(
        grid,
        origin="lower",
        extent=(-120, 120, -120, 120),
        vmin=0,
        vmax=50,
        cmap="viridis",
    )
    axes[row, 2].set_title(
        f"{project}\nFirst-return height; white = missing", fontsize=8
    )
    for ax in axes[row]:
        for _, cell in g.iterrows():
            robust = cell.shift_5m_min_above_5m_fraction >= 0.95
            ax.add_patch(
                Rectangle(
                    (cell.offset_east_m - 15, cell.offset_north_m - 15),
                    30,
                    30,
                    fill=False,
                    edgecolor="#39ff8a" if robust else "#ffba47",
                    lw=0.7,
                )
            )
        ax.set_xticks([])
        ax.set_yticks([])
    notes.append(
        dict(
            context_patch_id=key,
            aerial_dates=[old["naip_datetime"], m["naip_datetime"]],
            source_image_sha256=[
                old["image_sha256"],
                g.structural_array_sha256.iloc[0],
            ],
            review="Single-Codex visual triage: conifer-form crowns and forest persist; no obvious stand-replacing clearing in these views. Shaded understory and small crown changes remain unresolved.",
            current_evergreen_purity_quantified=False,
            independent_review=False,
        )
    )
fig.suptitle(
    "Evergreen reference shortlist: 88 Landsat cells in three patches\nGreen: structural screen retained under 5 m shifts (60 cells); orange: nominal screen only\nOlder lidar supports canopy structure; current evergreen purity remains unverified",
    fontsize=12,
)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(DEST / "evergreen_candidate_review_board.png", dpi=170)
plt.close(fig)
# Use exact image hashes (the structural array hash is stored separately).
for note in notes:
    key = note["context_patch_id"]
    note["source_image_sha256"][1] = json.loads((CACHE / f"{key}.json").read_text())[
        "image_sha256"
    ]
(DEST / "dated_visual_triage.json").write_text(json.dumps(notes, indent=2) + "\n")
print(
    f.groupby("context_patch_id")
    .agg(
        cells=("candidate_id", "size"),
        preferred_aerosol=("preferred_aerosol", "sum"),
        min_photo_gap=("aerial_gap_days", "min"),
        max_photo_gap=("aerial_gap_days", "max"),
    )
    .to_string()
)
print(
    "Platforms",
    f.platform.value_counts().to_dict(),
    "scenes",
    f.scene_id.nunique(),
    "grid",
    f.grid_match.all(),
    "finite",
    np.isfinite(f[[f"B{i}" for i in range(1, 8)]]).all().all(),
)
