#!/usr/bin/env python3
"""Refresh both panels' HLS identity from the local primary reference CSV.

Run `python update_hls_spectral_inputs.py` in this folder or from anywhere.
No repository imports, GIS packages, network calls or statistical refitting.
This updates spectral summaries and the sensor name, never statistical estimates.
For new cohorts, rerun external tests and update B's numeric evidence separately.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import plot_figure_4 as figure

HERE = Path(__file__).resolve().parent
SENSOR = "HLS L30 NBAR"
LEGACY = "Landsat 9 OLI-2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update():
    source = HERE / "evidence/landsat_hls_primary_reference_observations.csv"
    analysis = json.loads(
        (HERE / "evidence/landsat_hls_analysis_manifest.json").read_text()
    )
    if (
        digest(source)
        != analysis["input_sha256"]["hls_l30_nominal_95pct_observations.csv"]
    ):
        raise ValueError(
            "HLS source changed: rerun table analysis and update its evidence before rebuilding curves"
        )
    hls = pd.read_csv(source)
    if (
        hls.candidate_id.duplicated().any()
        or not hls.brdf_normalized.all()
        or not hls.hls_collection.eq("hls2-l30").all()
    ):
        raise ValueError("Require distinct, BRDF-normalized HLS L30 cells")
    if not np.isfinite(hls[figure.BANDS]).all().all() or not hls.nominal_95pct.all():
        raise ValueError("Require complete, nominal95% reference spectra")
    if not (hls.core_qa_clear & hls.context_150m_clear & hls.photo_date_match).all():
        raise ValueError("HLS reference quality/date contract failed")
    observations = HERE / "data/spectral_observations_by_footprint.csv"
    summary = HERE / "data/spectral_medians_and_interquartile_ranges.csv"
    table_path = HERE / "data/pft_separability_and_identifiability.csv"
    old = pd.read_csv(observations)
    # Preserve earlier C2 rows as history; they are never selected for rendering.
    previous = old.loc[old.sensor.eq(LEGACY)]
    if len(previous):
        history = HERE / "evidence/historical_c2_spectral_observations.csv"
        if not history.exists():
            previous.to_csv(history, index=False)
        history = HERE / "evidence/historical_c2_spectral_summary.csv"
        if not history.exists():
            prior = pd.read_csv(summary)
            prior.loc[prior.sensor.eq(LEGACY)].to_csv(history, index=False)
    current = pd.DataFrame(
        dict(
            sensor=SENSOR,
            category=hls.researcher_category,
            footprint_id=hls.candidate_id,
            site=hls.region,
            calculation_dtype="float64",
            source_product="HLS L30 v2 NBAR",
            source_item_id=hls.hls_item_id,
            patch_group_id=hls.patch_group_id,
            reference_basis=hls.reference_basis,
            brdf_normalized=hls.brdf_normalized,
            **{band: hls[band] for band in figure.BANDS},
        )
    )
    combined = pd.concat(
        [current, old.loc[~old.sensor.isin([LEGACY, SENSOR])]], ignore_index=True
    )
    combined.to_csv(observations, index=False)
    calculated = figure.recalculate_spectra(observations)
    calculated.to_csv(summary, index=False)
    table = pd.read_csv(table_path)
    table["sensor"] = table.sensor.replace({LEGACY: SENSOR})
    table.to_csv(table_path, index=False)
    figure.load_summary(summary)
    figure.load_table(table_path)
    counts = hls.groupby("researcher_category").size().to_dict()
    manifest = dict(
        sensor=SENSOR,
        source_file=str(source.relative_to(HERE)),
        source_sha256=digest(source),
        update_script_sha256=digest(Path(__file__)),
        cells=len(hls),
        patch_groups=int(hls.patch_group_id.nunique()),
        class_counts={k: int(v) for k, v in counts.items()},
        normalization="each footprint divided by its own B1-B5 sum",
        ribbon="25th-75th footprint percentiles; same color/alpha as before",
        panels_share_primary_hls_cohort=True,
        legacy_c2_plotted=False,
        output_sha256={
            str(p.relative_to(HERE)): digest(p)
            for p in [observations, summary, table_path]
        },
    )
    (HERE / "hls_spectral_update_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(
        f"Rebuilt HLS curves/quartiles/counts for {len(hls)} cells; class counts {counts}"
    )


if __name__ == "__main__":
    update()
