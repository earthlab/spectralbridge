"""Quantify unresolved contributors using actual camera records, never assign rays."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import ROOT, SOURCE, PRIOR, write, dist, sha  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402


def main():
    path = PRIOR / "camera_poses_with_photo_times.csv"
    poses = pd.read_csv(path)
    cameras = poses.drop_duplicates(["X", "Y", "Z"]).copy()
    selection = json.loads(
        (
            ROOT / "provenance/brdf-artifact-anatomy/2026-11-03/selection.json"
        ).read_text()
    )
    terrain = Path(
        "/private/tmp/photogrammetry-metadata-20261102/goldhill_aligned_dem.tif"
    )
    records = []
    rays = []
    with rasterio.open(SOURCE) as src, rasterio.open(terrain) as dem:
        for point in selection["pixels"]:
            x, y = src.xy(point["row"], point["column"])
            z = float(next(dem.sample([(x, y)]))[0])
            dx = cameras.X.to_numpy() - x
            dy = cameras.Y.to_numpy() - y
            dz = cameras.Z.to_numpy() - z
            zen = np.arctan2(np.hypot(dx, dy), dz)
            az = np.mod(np.arctan2(dx, dy), 2 * np.pi)
            # Deliberately approximate cone, not recovered image footprint/contributor.
            choose = (dz > 0) & (zen <= np.deg2rad(28.610459665965216))
            kv = c.calc_volume_kernel(
                np.deg2rad(204.6958),
                np.deg2rad(27.76494),
                az[choose],
                zen[choose],
                kernel_type="RossThick",
            )
            kg = c.calc_geom_kernel(
                np.deg2rad(204.6958),
                np.deg2rad(27.76494),
                az[choose],
                zen[choose],
                kernel_type="LiDenseR",
                b_r=10,
                h_b=2,
            )
            records.append(
                dict(
                    point=point,
                    label=point["label"],
                    x=x,
                    y=y,
                    assumed_ground_z=z,
                    all_positive_height_rays=int((dz > 0).sum()),
                    conditional_nadir_cone_candidates=int(choose.sum()),
                    candidate_zenith_degrees=dist(np.rad2deg(zen[choose])),
                    candidate_azimuth_degrees=dist(np.rad2deg(az[choose])),
                    candidate_height_m=dist(dz[choose]),
                    candidate_RossThick=dist(kv),
                    candidate_LiDenseR=dist(kg),
                    warning="Scenario envelope, not a confidence interval, actual footprint or contributor selection; assumes reported XY are26913 and Z matches delivered elevation datum.",
                )
            )
            for i in np.flatnonzero(choose):
                rays.append(
                    dict(
                        point=point["label"],
                        PhotoID=cameras.PhotoID.iloc[i],
                        X=cameras.X.iloc[i],
                        Y=cameras.Y.iloc[i],
                        candidate_zenith_degrees=np.rad2deg(zen[i]),
                        candidate_azimuth_degrees=np.rad2deg(az[i]),
                    )
                )
    # Algebraic non-identifiability using actual Goldhill nadir design, no model applied.
    config = c.HYTOOLS_BRDF_KERNEL_CONFIG
    x0 = np.array(
        [
            1.0,
            c.calc_volume_kernel(0, np.deg2rad(27.76494), 0, 0, "RossThick").item(),
            c.calc_geom_kernel(
                0, np.deg2rad(27.76494), 0, 0, "LiDenseR", b_r=10, h_b=2
            ).item(),
        ]
    )
    ref = c._reference_design(c.ReferenceGeometry(), config)
    null = ref - x0 * (ref @ x0) / (x0 @ x0)
    beta0 = np.array([0.3, 0, 0])
    examples = []
    for desired in [0.15, 0.3, 0.6]:
        beta = beta0 + (desired - ref @ beta0) / (ref @ null) * null
        examples.append(
            dict(
                synthetic_beta=beta,
                observed_prediction=float(x0 @ beta),
                reference_prediction=float(ref @ beta),
                factor=float((ref @ beta) / (x0 @ beta)),
            )
        )
    matrices = (
        poses[[f"r{i}{j}" for i in range(1, 4) for j in range(1, 4)]]
        .to_numpy()
        .reshape(-1, 3, 3)
    )
    orthogonal = np.linalg.norm(
        matrices @ matrices.transpose(0, 2, 1) - np.eye(3), axis=(1, 2)
    )
    write(
        "geometry_feasibility.json",
        dict(
            camera_records=len(poses),
            positions=len(cameras),
            pose_file=str(path),
            pose_sha256=sha(path),
            terrain_file=str(terrain),
            terrain_sha256=sha(terrain),
            rotation_orthogonality_error=dist(orthogonal),
            rotation_determinant=dist(np.linalg.det(matrices)),
            records=records,
            source_CRS_label="CSV says5070; numbers spatially match26913. Neither silently relabelled as authoritative.",
            contributors="NOT_RECOVERED; no image IDs, seamline decisions, pixel blending weights or visibility per output pixel. Pose matrices do not identify used rays.",
            data_route="Small source-linked Metashape export: contributor IDs/blend weights, camera/reference CRS and vertical/angular conventions, sensor intrinsics and surface/visibility inputs; or independently calibrated repeated same-target multi-angle subset. Full archive not required just to export these records.",
            external_models="Existing independently applicable model not found. New real NEON fits in this experiment are computational controls on2021R10C native bands, not independently validated Goldhill2023MicaSense transfers.",
            constrained_model="One observed design row identifies only its dot product with beta. Two directional degrees of freedom must be supplied externally and independently validated. Isotropic-only shape is identity, not an estimated directional correction.",
            identifiability_examples=dict(
                kind="SYNTHETIC_ALGEBRA_ON_ACTUAL_GEOMETRY_NOT_GOLDHILL_FITS",
                observed_design=x0,
                reference_design=ref,
                null_projection_norm=np.linalg.norm(null),
                examples=examples,
            ),
        ),
    )
    pd.DataFrame(rays).to_csv(HERE / "conditional_camera_envelope.csv", index=False)


if __name__ == "__main__":
    main()
