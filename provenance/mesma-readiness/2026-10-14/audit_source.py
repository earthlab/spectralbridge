"""Bounded metadata/native-grid QC, no persistent pixel-scale materialization."""

from pathlib import Path
import json
import logging
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial.distance import cdist
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.mesma_readiness import load_compact_inputs

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
COMPACT = ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
TABLES = OUT / "tables"
TABLES.mkdir(exist_ok=True)
metadata_fields = [
    "GlobalID",
    "species",
    "cover_category",
    "cover_subcategory",
    "dead_subcategory",
    "other_subcategory",
    "shaded",
    "aop_site",
    "field_year",
    "imagery_year",
    "plotID_clean",
    "description_notes",
    "area_m",
    "polygon_geometry_wkb",
]
metadata = pq.read_table(SOURCE, columns=metadata_fields).to_pandas()
conflicts = {
    c: int(metadata.groupby("GlobalID")[c].nunique().gt(1).sum())
    for c in metadata_fields
    if c not in ["GlobalID", "polygon_geometry_wkb", "area_m"]
}
unique = metadata.drop(columns=["polygon_geometry_wkb", "area_m"]).drop_duplicates(
    "GlobalID"
)
unique.to_csv(TABLES / "original_material_metadata.csv", index=False)
for field in [
    "cover_category",
    "cover_subcategory",
    "dead_subcategory",
    "other_subcategory",
    "shaded",
    "species",
]:
    unique.groupby(["aop_site", field], dropna=False).GlobalID.nunique().rename(
        "identities"
    ).reset_index().to_csv(TABLES / (field + "_inventory.csv"), index=False)

# Native pixel variability: center on existing native polygon/flight medians,
# reduce immediately to per-observation vector sufficient statistics, then drop pixels.
native = pd.read_parquet(COMPACT / "corr/plant_flight_native_spectra.parquet")
keys = ["GlobalID", "flight_id", "source_image", "polygon_id"]
lookup = {
    tuple(row): i
    for i, row in enumerate(native[keys].itertuples(index=False, name=None))
}
anchors = np.stack(native["corrected_values"])
N, B = anchors.shape
counts = np.zeros(N, np.int64)
band_counts = np.zeros(N, np.int64)
sums = {k: np.zeros((N, B)) for k in ["raw", "corr"]}
squared = {k: np.zeros(N) for k in sums}
flightgrids = pd.read_csv(COMPACT / "corr/flight_source_grids.csv")
print("grid columns", flightgrids.columns.tolist())
gridmap = {row.flight_id: json.loads(row.columns) for row in flightgrids.itertuples()}
all_columns = sorted(set(c for cols in gridmap.values() for c in cols))
columns = [*keys, *all_columns, *[c.replace("corr_", "raw_", 1) for c in all_columns]]
qc = []
for batch in pq.ParquetFile(SOURCE).iter_batches(batch_size=2048, columns=columns):
    frame = batch.to_pandas()
    for flight, group in frame.groupby("flight_id", sort=False):
        indices = np.array(
            [
                lookup[tuple(row)]
                for row in group[keys].itertuples(index=False, name=None)
            ]
        )
        cols = gridmap[flight]
        w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
        keep = ~(((w >= 1340) & (w <= 1450)) | ((w >= 1790) & (w <= 2000)))
        keep &= (w >= 385) & (w <= 2510)
        band_counts[indices] = keep.sum()
        w = w[keep]
        neighbor = np.diff(w) <= 8
        triples = neighbor[:-1] & neighbor[1:]
        np.add.at(counts, indices, 1)
        for stage in ["raw", "corr"]:
            use = [c.replace("corr_", stage + "_", 1) for c in cols]
            values = group[use].to_numpy(float)
            assert np.isfinite(values).all()
            residual = values - anchors[indices]
            residual[:, ~keep] = 0
            np.add.at(sums[stage], indices, residual)
            np.add.at(squared[stage], indices, np.sum(residual * residual, axis=1))
            supported = values[:, keep]
            rough = np.sqrt(
                np.mean(
                    (supported[:, 2:] - 2 * supported[:, 1:-1] + supported[:, :-2])[
                        :, triples
                    ]
                    ** 2,
                    axis=1,
                )
            )
            qc.append(
                dict(
                    flight_id=flight,
                    stage=stage,
                    pixels=len(group),
                    finite_native_values=int(np.isfinite(values).sum()),
                    negative_native_values=int((values < 0).sum()),
                    zero_native_values=int((values == 0).sum()),
                    possible_nodata_minus9999=int((values == -9999).sum()),
                    minimum=float(values.min()),
                    maximum=float(values.max()),
                    roughness_sum=float(rough.sum()),
                    scale_status="unverified native stored units",
                )
            )
    LOG.info(
        "Reduced %s pixel rows; only per-observation sufficient moments retained",
        len(frame),
    )
records = []
for stage in sums:
    # Centered trace population variance; no subtraction of large raw moments.
    variance = np.maximum(
        0,
        (squared[stage] / counts - np.sum((sums[stage] / counts[:, None]) ** 2, axis=1))
        / band_counts,
    )
    t = native[keys + ["cover_category", "aop_site"]].copy()
    t["stage"] = stage
    t["pixels"] = counts
    t["within_polygon_mean_band_variance"] = variance
    t["within_polygon_RMS_SD"] = np.sqrt(variance)
    records.append(t)
pd.concat(records).to_parquet(
    TABLES / "within_polygon_pixel_variability.parquet", index=False, compression="zstd"
)
q = (
    pd.DataFrame(qc)
    .groupby(["flight_id", "stage"], as_index=False)
    .agg(
        pixels=("pixels", "sum"),
        finite_native_values=("finite_native_values", "sum"),
        negative_native_values=("negative_native_values", "sum"),
        zero_native_values=("zero_native_values", "sum"),
        possible_nodata_minus9999=("possible_nodata_minus9999", "sum"),
        minimum=("minimum", "min"),
        maximum=("maximum", "max"),
        roughness_sum=("roughness_sum", "sum"),
    )
)
q["mean_supported_second_difference_RMS"] = q.roughness_sum / q.pixels
q.to_csv(TABLES / "native_pixel_qc.csv", index=False)

# Descriptive repeated-acquisition versus identity dispersion, not causal components.
obs = pd.read_parquet(COMPACT / "corr/plant_flight_spectra.parquet")
cols = [c for c in obs if c.startswith("corr_wl")]
y = obs[cols].to_numpy(float)
y = y[:, np.isfinite(y).all(0)]
sst = float(np.sum((y - y.mean(0)) ** 2))
components = []
for field in ["GlobalID", "flight_id", "cover_category", "aop_site"]:
    within = 0
    for _, ix in obs.groupby(field).groups.items():
        a = y[list(ix)]
        within += float(np.sum((a - a.mean(0)) ** 2))
    components.append(
        dict(
            grouping=field,
            groups=obs[field].nunique(),
            within_sum_squares=within,
            total_sum_squares=sst,
            within_fraction=within / sst,
            between_fraction=1 - within / sst,
            interpretation="separate_descriptive_partition_not_additive_causal_variance_components",
        )
    )
pd.DataFrame(components).to_csv(TABLES / "hierarchical_dispersion.csv", index=False)

# Coverage accumulation by species/site/year on an identity-disjoint fixed target set.
table, values, waves = load_compact_inputs(SOURCE, COMPACT)
rng = np.random.default_rng(20261014)
ids = rng.permutation(table.GlobalID.unique())
held = ids[: len(ids) // 5]
tr = np.flatnonzero(~table.GlobalID.isin(held))
te = np.flatnonzero(table.GlobalID.isin(held))
curves = []
for sensor, y in values.items():
    d = cdist(y[te], y[tr]) / np.sqrt(y.shape[1])
    for field in ["GlobalID", "species", "site", "year"]:
        groups = table.iloc[tr][field].fillna("Unlabelled").astype(str).to_numpy()
        labels = np.unique(groups)
        for repeat in range(10):
            order = rng.permutation(labels)
            nearest = np.full(len(te), np.inf)
            for step, label in enumerate(order, 1):
                nearest = np.minimum(nearest, d[:, groups == label].min(1))
                if field == "GlobalID" and step not in [
                    1,
                    2,
                    5,
                    10,
                    20,
                    50,
                    100,
                    200,
                    500,
                    1000,
                    2000,
                    len(order),
                ]:
                    continue
                curves.append(
                    dict(
                        sensor=sensor,
                        accumulated_by=field,
                        repeat=repeat,
                        groups=step,
                        last_group=label,
                        median_nearest_RMSE=float(np.median(nearest)),
                        p95_nearest_RMSE=float(np.quantile(nearest, 0.95)),
                        interpretation="held_out_library_not_full_source_imagery",
                    )
                )
pd.DataFrame(curves).to_csv(TABLES / "group_accumulation.csv", index=False)
(OUT / "manifests" / "source_audit.json").write_text(
    json.dumps(
        dict(
            source=str(SOURCE),
            sha256=_file_hash(SOURCE),
            rows=pq.ParquetFile(SOURCE).metadata.num_rows,
            metadata_conflicts=conflicts,
            source_headers_present=False,
            purity_metadata_present=False,
            independent_fraction_truth_present=False,
            source_specific_saturation_known=False,
            physical_background_labels="Existing exact subcategory values only; Bare != verified soil; shaded != measured shade; mixed remains mixed",
        ),
        indent=2,
    )
    + "\n"
)
print("Source audit complete without persistent pixel cache")
