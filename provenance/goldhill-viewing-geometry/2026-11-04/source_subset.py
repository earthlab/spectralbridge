"""Smallest practical source request selected on fixed-target geometry only."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    rays = pd.read_csv(HERE / "fixed_point_candidate_rays.csv")
    points = list(rays.point.unique())
    common = set.intersection(*[set(g.order) for _, g in rays.groupby("point")])
    ids = np.array(sorted(common))
    rng = np.random.default_rng(20261104)
    best = None
    for _ in range(3000):
        pick = np.sort(rng.choice(ids, 4, replace=False))
        conditions = []
        for point in points:
            r = rays[rays.point == point].set_index("order").loc[pick]
            X = np.c_[np.ones(4), r.RossThick, r.LiDenseR]
            s = np.linalg.svd(X, compute_uv=False)
            conditions.append(s[0] / s[-1])
        score = max(conditions)
        if best is None or score < best[0]:
            best = (score, pick, conditions)
    poses = pd.read_csv(
        ROOT
        / "provenance/goldhill-end-to-end/2026-11-03/camera_poses_with_photo_times.csv"
    )
    path = pd.read_csv(HERE / "acquisition_path.csv")
    frames = path.iloc[best[1]].PhotoID.str.rsplit("_", n=1).str[0]
    subset = poses[poses.PhotoID.str.rsplit("_", n=1).str[0].isin(frames)].copy()
    subset["request"] = (
        "Original calibrated band photos or source-linked target patches + complete pose/intrinsics/calibration/clock metadata; geometry-selected candidate subset, not verified repeated observations"
    )
    subset.to_csv(HERE / "minimum_source_subset.csv", index=False)
    (HERE / "minimum_source_subset.json").write_text(
        json.dumps(
            dict(
                status="CANDIDATE_REQUEST_NOT_RECOVERED_OBSERVATIONS",
                candidate_positions=best[1].tolist(),
                band_images=len(subset),
                fixed_points=points,
                geometry_only_condition_by_point=best[2],
                criterion="Minimum worst four-ray design condition among3000seeded candidate subsets; no reflectance or PFT score used",
                minimum_empirical_requirement="At least four matched, calibrated directional observations per fixed ground target for the existing three-parameter fit, plus independent validation targets;40 band images or corresponding source-linked patches, camera CRS/vertical/pose/intrinsics/time conventions and calibration metadata.",
                source_access="Live package metadata/subcollections inspected; relative RawData/M300/SD1 path not found. No original overlapping Goldhill photos currently accessible in checked locations. No repeated measurements invented.",
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Source request:",
        len(subset),
        "band photos, worst conditional design condition",
        best[0],
    )


if __name__ == "__main__":
    main()
