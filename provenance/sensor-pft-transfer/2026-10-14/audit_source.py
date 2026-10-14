import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

root = Path("provenance/sensor-pft-transfer/2026-10-14")
pf = pq.ParquetFile("Aug_2026_all_polygons_merged_pixel_extraction.parquet")
families = {}
for c in pf.schema_arrow.names:
    if "_wl" in c:
        families.setdefault(c.split("_b")[0], []).append(c)
rows = []
for stage, cols in families.items():
    if len(cols) > 20:
        continue
    f = pf.read(columns=["GlobalID", "flight_id"] + cols).to_pandas()
    a = np.isfinite(f[cols].to_numpy(float))
    rows.append(
        dict(
            stage=stage,
            bands=len(cols),
            pixels=len(f),
            complete_pixels=int(a.all(1).sum()),
            partial_pixels=int((a.any(1) & ~a.all(1)).sum()),
            identities=f.GlobalID.nunique(),
            complete_identities=f.loc[a.all(1), "GlobalID"].nunique(),
        )
    )
    for col in cols:
        rows[-1]["missing_" + col] = int(f[col].isna().sum())
pd.DataFrame(rows).to_csv(root / "source_family_support.csv", index=False)
(root / "source_columns.json").write_text(json.dumps(families, indent=2) + "\n")
# Whole table projected once per compact family; no pixel cache is written.
ratios = []
for stage in ["olioli", "micasense"]:
    a = pf.read(columns=families[stage]).to_pandas().to_numpy(float)
    b = pf.read(columns=families[stage + "_undarkened"]).to_pandas().to_numpy(float)
    for j in range(a.shape[1]):
        good = np.isfinite(a[:, j]) & np.isfinite(b[:, j]) & (abs(b[:, j]) > 1e-6)
        q = a[good, j] / b[good, j]
        ratios.append(
            dict(
                stage=stage,
                band=j + 1,
                n=int(good.sum()),
                median_ratio=float(np.median(q)),
                minimum_ratio=float(np.min(q)),
                maximum_ratio=float(np.max(q)),
            )
        )
pd.DataFrame(ratios).to_csv(root / "brightness_audit.csv", index=False)
# Sample up to two complete pixels per source without retaining the table.
columns = (
    ["source_parquet"]
    + families["corr"]
    + families["raw"]
    + families["olioli_undarkened"]
)
samples = {}
native_counts = {
    stage: dict(minimum=10**9, maximum=0, blank_pixels=0, finite_values=0)
    for stage in ["corr", "raw"]
}
for batch in pf.iter_batches(batch_size=512, columns=columns):
    f = batch.to_pandas()
    for stage in ["corr", "raw"]:
        counts = np.isfinite(f[families[stage]].to_numpy(float)).sum(axis=1)
        native_counts[stage]["minimum"] = min(
            native_counts[stage]["minimum"], int(counts.min())
        )
        native_counts[stage]["maximum"] = max(
            native_counts[stage]["maximum"], int(counts.max())
        )
        native_counts[stage]["blank_pixels"] += int((counts == 0).sum())
        native_counts[stage]["finite_values"] += int(counts.sum())
    for source, ix in f.groupby("source_parquet").indices.items():
        if len(samples.get(source, [])) >= 2:
            continue
        for i in ix[: 2 - len(samples.get(source, []))]:
            samples.setdefault(source, []).append(f.iloc[i])
pd.DataFrame(
    [
        dict(stage=k, union_columns=len(families[k]), **v)
        for k, v in native_counts.items()
    ]
).to_csv(root / "native_family_support.csv", index=False)
params = json.loads(
    Path("src/spectralbridge/data/landsat_band_parameters.json").read_text()
)["Landsat 8 OLI"]
diag = []
for source, sample in samples.items():
    for i, row in enumerate(sample):
        observed = row[families["olioli_undarkened"]].to_numpy(float)
        for stage in ["corr", "raw"]:
            vals = row[families[stage]].to_numpy(float)
            valid = np.isfinite(vals)
            w = np.array([float(c.split("_wl")[1][:-2]) for c in families[stage]])[
                valid
            ]
            vals = vals[valid]
            order = np.argsort(w)
            w = w[order]
            vals = vals[order]
            for method in ["gaussian", "straight"]:
                predicted = []
                for center, width in zip(params["wavelengths"], params["fwhms"]):
                    weights = (
                        np.exp(-0.5 * ((w - center) / (width / 2.354820045)) ** 2)
                        if method == "gaussian"
                        else (np.arange(len(w)) == np.argmin(abs(w - center))).astype(
                            float
                        )
                    )
                    predicted.append(vals @ weights / weights.sum())
                error = np.asarray(predicted) - observed
                diag.append(
                    dict(
                        source_parquet=source,
                        sample=i,
                        input=stage,
                        method=method,
                        relative_rmse=float(
                            np.sqrt(np.mean(error**2)) / np.sqrt(np.mean(observed**2))
                        ),
                        rmse=float(np.sqrt(np.mean(error**2))),
                    )
                )
pd.DataFrame(diag).to_csv(root / "generation_consistency.csv", index=False)
print(
    pd.DataFrame(rows)[
        ["stage", "bands", "complete_pixels", "partial_pixels", "complete_identities"]
    ].to_string(index=False)
)
print(
    pd.DataFrame(diag)
    .groupby(["input", "method"])
    .relative_rmse.agg(["median", "max"])
    .to_string()
)
