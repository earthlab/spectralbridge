"""Stream the existing AOP library in place into matched compact stage summaries.

Raw versus archived BRDF+topography is a PIPELINE contrast, not BRDF-only. Uses
existing Gaussian OLI diagnostic response projection before polygon medians.
No ordinary pixel-scale cache is created. Repeat-view rows remain in memory only
until pandas' stable grouped variance reduces them to polygon/day statistics.
"""

import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from threadpoolctl import threadpool_limits

from spectralbridge.sensor_pft_transfer import project_neon_to_oli

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
REPORT = ROOT / "provenance/brdf-benefit-audit/2026-11-19/aop"
BANDS = [f"B{i}" for i in range(1, 8)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flight_summary(frame, rawcols, point_frames):
    if frame.duplicated(["GlobalID", "flight_id", "x", "y", "epsg"]).any():
        raise ValueError("Duplicate same-flight ground observations")
    fid = str(frame.flight_id.iloc[0])
    date = re.search(r"_(20\d{6})", fid).group(1)
    raw = frame[rawcols].to_numpy(float, copy=True)
    corr = frame[[c.replace("raw_", "corr_", 1) for c in rawcols]].to_numpy(
        float, copy=True
    )
    raw[np.isclose(raw, -9999, rtol=0, atol=1e-6)] = np.nan
    corr[np.isclose(corr, -9999, rtol=0, atol=1e-6)] = np.nan
    # Common native channels observed in both arms, then complete paired rows.
    channels = np.isfinite(raw).any(axis=0) & np.isfinite(corr).any(axis=0)
    raw = raw[:, channels]
    corr = corr[:, channels]
    wave = np.array(
        [
            float(re.search(r"wl(\d+)nm", c).group(1))
            for c in np.array(rawcols)[channels]
        ]
    )
    order = np.argsort(wave)
    wave = wave[order]
    raw = raw[:, order]
    corr = corr[:, order]
    keep = np.isfinite(raw).all(axis=1) & np.isfinite(corr).all(axis=1)
    info = dict(
        flight_id=fid,
        input_rows=len(frame),
        paired_rows=int(keep.sum()),
        native_common_channels=len(wave),
        date=date,
    )
    if len(wave) < 2 or not keep.any():
        return pd.DataFrame(), info
    if np.any(np.diff(wave) <= 0):
        raise ValueError("Ambiguous native source grid")
    projected, mass = project_neon_to_oli(
        np.vstack([raw[keep], corr[keep]]) * 0.0001, wave
    )
    n = int(keep.sum())
    before = projected[:n]
    after = projected[n:]
    selected = (
        frame.loc[keep, ["GlobalID", "cover_category", "aop_site", "x", "y", "epsg"]]
        .copy()
        .reset_index(drop=True)
    )
    selected["GlobalID"] = selected.GlobalID.astype(str).str.strip("{}").str.lower()
    if selected.groupby("GlobalID").cover_category.nunique().gt(1).any():
        raise ValueError("Conflicting plant label")
    summaries = []
    for arm, values in [("no_brdf", before), ("brdf", after)]:
        rows = pd.concat(
            [
                selected[["GlobalID", "cover_category", "aop_site"]],
                pd.DataFrame(values, columns=BANDS),
            ],
            axis=1,
        )
        g = rows.groupby(["GlobalID", "cover_category", "aop_site"], as_index=False)[
            BANDS
        ].median()
        g = g.rename(
            columns={
                "GlobalID": "identity",
                "cover_category": "category",
                "aop_site": "site",
            }
        )
        summaries.append(
            g.assign(arm=arm, flight_id=fid, date=date, year=int(date[:4]))
        )
    points = selected.rename(
        columns={
            "GlobalID": "identity",
            "cover_category": "category",
            "aop_site": "site",
        }
    )
    points["date"] = date
    # Exact nominal ground centres, not polygon means or neighbours.
    points["x"] = points.x.round(3)
    points["y"] = points.y.round(3)
    for i, b in enumerate(BANDS):
        points["raw_" + b] = before[:, i]
        points["corr_" + b] = after[:, i]
    point_frames.append(points)
    info.update(
        {f"Gaussian_response_mass_{b}": float(mass[i]) for i, b in enumerate(BANDS)}
    )
    return pd.concat(summaries, ignore_index=True), info


def run():
    started = time.monotonic()
    REPORT.mkdir(parents=True, exist_ok=True)
    identity = dict(
        source_sha256=sha(SOURCE),
        code_sha256=sha(Path(__file__)),
        projection_code_sha256=sha(
            Path(
                __import__(
                    "spectralbridge.sensor_pft_transfer", fromlist=["x"]
                ).__file__
            )
        ),
    )
    checkpoint = REPORT / "completed.json"
    if checkpoint.exists():
        old = json.loads(checkpoint.read_text())
        if old["identity"] == identity and all(
            sha(REPORT / name) == digest for name, digest in old["outputs"].items()
        ):
            print("AOP compact stage comparison reused", flush=True)
            return
    parquet = pq.ParquetFile(SOURCE)
    names = parquet.schema_arrow.names
    rawcols = [n for n in names if re.fullmatch(r"raw_b\d+_wl\d+nm", n)]
    cols = [
        "flight_id",
        "GlobalID",
        "cover_category",
        "aop_site",
        "x",
        "y",
        "epsg",
        *rawcols,
        *[c.replace("raw_", "corr_", 1) for c in rawcols],
    ]
    summaries = []
    audits = []
    points = []
    current = None
    pending = []
    seen = set()

    def flush():
        if not pending:
            return
        fid = str(pending[0].flight_id.iloc[0])
        if fid in seen:
            raise ValueError(
                "Noncontiguous source flights require different bounded strategy"
            )
        seen.add(fid)
        frame = pd.concat(pending, ignore_index=True)
        with threadpool_limits(limits=1):
            compact, audit = flight_summary(frame, rawcols, points)
        summaries.append(compact)
        audits.append(audit)
        print(
            f"AOP {len(seen)}/122 {fid}: {audit['paired_rows']}/{len(frame)} paired pixels -> {len(compact) // 2} plant-flight spectra",
            flush=True,
        )

    for batch in parquet.iter_batches(batch_size=8192, columns=cols):
        frame = batch.to_pandas()
        for fid, group in frame.groupby("flight_id", sort=False):
            if current is not None and fid != current:
                flush()
                pending = []
            current = fid
            pending.append(group.copy())
    flush()
    native = pd.concat(summaries, ignore_index=True)
    native.to_csv(REPORT / "plant_flight_spectra.csv", index=False)
    # Equal flightline weight within an identity-year; identities are grouped in CV.
    annual = native.groupby(
        ["identity", "category", "site", "year", "arm"], as_index=False
    )[BANDS].mean()
    annual.to_csv(REPORT / "polygon_spectra.csv", index=False)
    pd.DataFrame(audits).to_csv(REPORT / "flight_support_audit.csv", index=False)
    point = pd.concat(points, ignore_index=True)
    keys = ["identity", "category", "site", "date", "epsg", "x", "y"]
    features = ["raw_" + b for b in BANDS] + ["corr_" + b for b in BANDS]
    # pandas group variance uses stable Welford-style grouped accumulation.
    group = point.groupby(keys, dropna=False)
    count = group.size()
    variance = group[features].var(ddof=1)
    variance = variance.loc[count >= 2].copy()
    variance["repeat_pixels"] = 1
    for label, prefix in [("no_brdf", "raw_"), ("brdf", "corr_")]:
        variance["rms_" + label + "_5"] = np.sqrt(
            variance[[prefix + b for b in BANDS[:5]]].mean(axis=1)
        )
        variance["rms_" + label + "_7"] = np.sqrt(
            variance[[prefix + b for b in BANDS]].mean(axis=1)
        )
    repeated = (
        variance.reset_index()
        .groupby(["identity", "category", "site", "date"], as_index=False)
        .agg(
            repeated_ground_pixels=("repeat_pixels", "sum"),
            rms_no_brdf_5=("rms_no_brdf_5", "median"),
            rms_brdf_5=("rms_brdf_5", "median"),
            rms_no_brdf_7=("rms_no_brdf_7", "median"),
            rms_brdf_7=("rms_brdf_7", "median"),
        )
    )
    repeated.to_csv(REPORT / "repeat_view_consistency.csv", index=False)
    outputs = {p.name: sha(p) for p in REPORT.glob("*.csv")}
    checkpoint.write_text(
        json.dumps(
            dict(
                identity=identity,
                outputs=outputs,
                elapsed_seconds=time.monotonic() - started,
                flights=len(audits),
                polygon_year_rows=len(annual) // 2,
                unique_plants=annual.identity.nunique(),
                overlap_polygon_days=len(repeated),
                source_pixel_rows=parquet.metadata.num_rows,
                units="NEON historical10000 count convention decoded by0.0001; archive-level legacy metadata limits remain, no absolute accuracy claim",
                attribution="Archived correction package (BRDF plus topography), not BRDF-only",
                pixel_cache_created=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "AOP matched library complete:",
        annual.identity.nunique(),
        "plants,",
        len(repeated),
        "repeat-view plant-days",
        flush=True,
    )


if __name__ == "__main__":
    run()
