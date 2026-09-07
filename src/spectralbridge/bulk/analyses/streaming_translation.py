"""Translation models derived from compact streaming sufficient statistics."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ..models import BulkAnalysisPaths, FlightlineRecord
from ..provenance import write_json_atomic
from ..registry import TranslationPair
from ..streaming import (
    BivariateStatistics,
    iter_aligned_pair_chunks,
)
from .leave_one_site_out import LeaveOneSiteOutPaths
from .sensor_translation import SensorTranslationPaths


_TRANSLATION_SCHEMA = pa.schema(
    [
        ("analysis_run_id", pa.string()),
        ("analysis_level", pa.string()),
        ("weighting", pa.string()),
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("micasense_sensor", pa.string()),
        ("landsat_sensor", pa.string()),
        ("band_index", pa.int32()),
        ("x_column", pa.string()),
        ("y_column", pa.string()),
        ("flightline_id", pa.string()),
        ("site", pa.string()),
        ("equation", pa.string()),
        ("status", pa.string()),
        ("slope", pa.float64()),
        ("intercept", pa.float64()),
        ("correlation", pa.float64()),
        ("r2", pa.float64()),
        ("bias", pa.float64()),
        ("rmse", pa.float64()),
        ("mae", pa.float64()),
        ("sample_count", pa.int64()),
        ("source_count", pa.int64()),
        ("flightline_count", pa.int64()),
        ("site_count", pa.int64()),
        ("replicate_count", pa.int64()),
        ("x_min", pa.float64()),
        ("x_max", pa.float64()),
        ("x_mean", pa.float64()),
        ("y_min", pa.float64()),
        ("y_max", pa.float64()),
        ("y_mean", pa.float64()),
    ]
)

_LOSO_SCHEMA = pa.schema(
    [
        ("analysis_run_id", pa.string()),
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("micasense_sensor", pa.string()),
        ("landsat_sensor", pa.string()),
        ("band_index", pa.int32()),
        ("x_column", pa.string()),
        ("y_column", pa.string()),
        ("held_out_site", pa.string()),
        ("status", pa.string()),
        ("training_slope", pa.float64()),
        ("training_intercept", pa.float64()),
        ("training_correlation", pa.float64()),
        ("held_out_rmse", pa.float64()),
        ("held_out_mae", pa.float64()),
        ("held_out_bias", pa.float64()),
        ("held_out_r2", pa.float64()),
        ("held_out_correlation", pa.float64()),
        ("observed_vs_predicted_slope", pa.float64()),
        ("observed_vs_predicted_intercept", pa.float64()),
        ("training_sample_count", pa.int64()),
        ("training_site_count", pa.int64()),
        ("training_flightline_count", pa.int64()),
        ("held_out_sample_count", pa.int64()),
        ("held_out_flightline_count", pa.int64()),
    ]
)


def _write_parquet(path: Path, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), temporary, compression="zstd")
    pq.read_schema(temporary)
    temporary.replace(path)


def _merge(rows: Iterable[dict[str, Any]]) -> BivariateStatistics:
    result = BivariateStatistics()
    for row in rows:
        result.merge(BivariateStatistics.from_row(row))
    return result


def _normalized(stats: BivariateStatistics) -> BivariateStatistics:
    if stats.n == 0:
        return BivariateStatistics()
    return BivariateStatistics(
        n=1,
        mean_x=stats.mean_x,
        mean_y=stats.mean_y,
        m2_x=stats.m2_x / stats.n,
        m2_y=stats.m2_y / stats.n,
        c_xy=stats.c_xy / stats.n,
        x_min=stats.x_min,
        x_max=stats.x_max,
        y_min=stats.y_min,
        y_max=stats.y_max,
    )


def _fit(stats: BivariateStatistics) -> tuple[float | None, float | None, float | None]:
    if stats.n < 2 or not math.isfinite(stats.m2_x) or stats.m2_x <= 0:
        return None, None, None
    slope = stats.c_xy / stats.m2_x
    intercept = stats.mean_y - slope * stats.mean_x
    correlation = (
        stats.c_xy / math.sqrt(stats.m2_x * stats.m2_y)
        if stats.m2_y > 0
        else None
    )
    return (
        slope if math.isfinite(slope) else None,
        intercept if math.isfinite(intercept) else None,
        correlation if correlation is not None and math.isfinite(correlation) else None,
    )


def _pair_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "translation_pair": row["translation_pair"],
        "source_sensor": row["source_sensor"],
        "target_sensor": row["target_sensor"],
        "source_band_index": int(row["source_band_index"]),
        "target_band_index": int(row["target_band_index"]),
        "micasense_sensor": row["source_sensor"],
        "landsat_sensor": row["target_sensor"],
        "band_index": int(row["band_index"]),
        "x_column": row["x_column"],
        "y_column": row["y_column"],
    }


def _translation_record(
    template: dict[str, Any],
    stats: BivariateStatistics,
    *,
    analysis_run_id: str,
    analysis_level: str,
    weighting: str,
    flightline_id: str | None,
    site: str | None,
    sample_count: int,
    source_count: int,
    flightline_count: int,
    site_count: int,
    replicate_count: int | None,
    bounds: BivariateStatistics | None = None,
) -> dict[str, Any]:
    slope, intercept, correlation = _fit(stats)
    ok = slope is not None and intercept is not None
    residual_ss = (
        max(0.0, stats.m2_y + slope * slope * stats.m2_x - 2 * slope * stats.c_xy)
        if ok
        else None
    )
    denominator = stats.n
    return {
        "analysis_run_id": analysis_run_id,
        "analysis_level": analysis_level,
        "weighting": weighting,
        **_pair_fields(template),
        "flightline_id": flightline_id,
        "site": site,
        "equation": "target = slope * source + intercept",
        "status": "ok" if ok else "insufficient_data",
        "slope": slope,
        "intercept": intercept,
        "correlation": correlation,
        "r2": correlation * correlation if correlation is not None else None,
        "bias": stats.mean_y - (slope * stats.mean_x + intercept) if ok else None,
        "rmse": math.sqrt(residual_ss / denominator) if ok and denominator else None,
        "mae": None,
        "sample_count": sample_count,
        "source_count": source_count,
        "flightline_count": flightline_count,
        "site_count": site_count,
        "replicate_count": replicate_count,
        "x_min": (bounds or stats).x_min if sample_count else None,
        "x_max": (bounds or stats).x_max if sample_count else None,
        "x_mean": stats.mean_x if stats.n else None,
        "y_min": (bounds or stats).y_min if sample_count else None,
        "y_max": (bounds or stats).y_max if sample_count else None,
        "y_mean": stats.mean_y if stats.n else None,
    }


def _spec_key(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["translation_pair"]), int(row["band_index"])


def _loso_record(
    template: dict[str, Any],
    global_stats: BivariateStatistics,
    held_stats: BivariateStatistics,
    *,
    analysis_run_id: str,
    site: str,
    total_sites: int,
    total_flightlines: int,
    held_flightlines: int,
) -> dict[str, Any]:
    training = global_stats.subtract(held_stats)
    slope, intercept, training_correlation = _fit(training)
    if total_sites - 1 < 1:
        status = "insufficient_sites"
    elif slope is None or intercept is None:
        status = "insufficient_training_data"
    elif held_stats.n < 2:
        status = "insufficient_holdout_data"
    else:
        status = "ok"
    bias = (
        held_stats.mean_y - (slope * held_stats.mean_x + intercept)
        if slope is not None and intercept is not None and held_stats.n
        else None
    )
    residual_ss = (
        held_stats.m2_y
        + slope * slope * held_stats.m2_x
        - 2 * slope * held_stats.c_xy
        + held_stats.n * bias * bias
        if slope is not None and bias is not None
        else None
    )
    held_corr = None
    observed_slope = None
    observed_intercept = None
    if slope not in (None, 0.0) and held_stats.m2_x > 0:
        raw_corr = (
            held_stats.c_xy / math.sqrt(held_stats.m2_x * held_stats.m2_y)
            if held_stats.m2_y > 0
            else None
        )
        held_corr = (
            raw_corr * (1.0 if slope > 0 else -1.0)
            if raw_corr is not None
            else None
        )
        observed_slope = held_stats.c_xy / (slope * held_stats.m2_x)
        prediction_mean = slope * held_stats.mean_x + intercept
        observed_intercept = held_stats.mean_y - observed_slope * prediction_mean
    return {
        "analysis_run_id": analysis_run_id,
        **_pair_fields(template),
        "held_out_site": site,
        "status": status,
        "training_slope": slope,
        "training_intercept": intercept,
        "training_correlation": training_correlation,
        "held_out_rmse": (
            math.sqrt(max(0.0, residual_ss) / held_stats.n)
            if residual_ss is not None and held_stats.n
            else None
        ),
        "held_out_mae": None,
        "held_out_bias": bias,
        "held_out_r2": (
            1.0 - residual_ss / held_stats.m2_y
            if residual_ss is not None and held_stats.m2_y > 0
            else None
        ),
        "held_out_correlation": held_corr,
        "observed_vs_predicted_slope": observed_slope,
        "observed_vs_predicted_intercept": observed_intercept,
        "training_sample_count": training.n,
        "training_site_count": max(0, total_sites - 1),
        "training_flightline_count": max(0, total_flightlines - held_flightlines),
        "held_out_sample_count": held_stats.n,
        "held_out_flightline_count": held_flightlines,
    }


def _add_mae(
    accumulator: dict[tuple[Any, ...], list[float]],
    key: tuple[Any, ...],
    x: np.ndarray,
    y: np.ndarray,
    slope: float | None,
    intercept: float | None,
    weight: float,
) -> None:
    if slope is None or intercept is None or x.size == 0:
        return
    x64 = np.asarray(x, dtype=np.float64)
    y64 = np.asarray(y, dtype=np.float64)
    absolute = np.abs(y64 - (slope * x64 + intercept))
    state = accumulator.setdefault(key, [0.0, 0.0])
    state[0] += float(np.sum(absolute, dtype=np.float64)) * weight
    state[1] += int(x.size) * weight


def _evaluate_mae(
    flightlines: Sequence[FlightlineRecord],
    translation_pairs: Sequence[TranslationPair],
    translation_rows: list[dict[str, Any]],
    loso_rows: list[dict[str, Any]],
    stats_rows: list[dict[str, Any]],
    *,
    chunk_size: int,
    minimum_reflectance: float,
) -> None:
    models: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in translation_rows:
        identity = (
            row["flightline_id"]
            if row["analysis_level"] == "per_flightline"
            else row["site"]
            if row["analysis_level"] == "per_site"
            else None
        )
        models[(row["analysis_level"], *_spec_key(row), identity)] = row
    loso_models = {
        ("loso", *_spec_key(row), row["held_out_site"]): row for row in loso_rows
    }
    accumulator: dict[tuple[Any, ...], list[float]] = {}
    n_by_flightline = {
        (row["flightline_id"], *_spec_key(row)): int(row["n"]) for row in stats_rows
    }
    site_stats: dict[tuple[str, str, int], int] = {}
    for row in stats_rows:
        if row["site"] is not None:
            key = (row["site"], *_spec_key(row))
            site_stats[key] = site_stats.get(key, 0) + int(row["n"])
    for flightline in flightlines:
        if flightline.status != "accepted" or not flightline.canonical_flightline_id:
            continue
        for _, chunks in iter_aligned_pair_chunks(
            flightline,
            translation_pairs,
            chunk_size=chunk_size,
            minimum_reflectance=minimum_reflectance,
        ):
            for spec, (_, x, y) in chunks.items():
                pair_key = (spec.translation_pair, spec.band_index)
                candidates = [
                    ("pixel_pooled", None, 1.0),
                    ("per_flightline", flightline.canonical_flightline_id, 1.0),
                    (
                        "flightline_balanced",
                        None,
                        1.0
                        / max(
                            1,
                            n_by_flightline[
                                (flightline.canonical_flightline_id, *pair_key)
                            ],
                        ),
                    ),
                ]
                if flightline.site is not None:
                    candidates.extend(
                        [
                            ("per_site", flightline.site, 1.0),
                            (
                                "site_balanced",
                                None,
                                1.0
                                / max(
                                    1,
                                    site_stats[(flightline.site, *pair_key)],
                                ),
                            ),
                        ]
                    )
                for level, identity, weight in candidates:
                    key = (level, *pair_key, identity)
                    model = models.get(key)
                    if model:
                        _add_mae(
                            accumulator,
                            key,
                            x,
                            y,
                            model["slope"],
                            model["intercept"],
                            weight,
                        )
                loso_key = ("loso", *pair_key, flightline.site)
                loso = loso_models.get(loso_key)
                if loso:
                    _add_mae(
                        accumulator,
                        loso_key,
                        x,
                        y,
                        loso["training_slope"],
                        loso["training_intercept"],
                        1.0,
                    )
    for key, row in models.items():
        total, weight = accumulator.get(key, (0.0, 0.0))
        row["mae"] = total / weight if weight else None
    for key, row in loso_models.items():
        total, weight = accumulator.get(key, (0.0, 0.0))
        row["held_out_mae"] = total / weight if weight else None


def run_streaming_translation_analyses(
    con: duckdb.DuckDBPyConnection,
    paths: BulkAnalysisPaths,
    *,
    analysis_run_id: str,
    statistics_rows: list[dict[str, Any]],
    flightlines: Sequence[FlightlineRecord],
    minimum_reflectance: float,
    chunk_size: int,
    translation_pairs: Sequence[TranslationPair],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive all model levels and LOSO, using one bounded MAE evaluation pass."""

    by_spec: dict[tuple[str, int], list[dict[str, Any]]] = {}
    by_flightline: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in statistics_rows:
        by_spec.setdefault(_spec_key(row), []).append(row)
        by_flightline[(*_spec_key(row), row["flightline_id"])] = row

    translation_rows: list[dict[str, Any]] = []
    loso_rows: list[dict[str, Any]] = []
    for spec_key, rows in sorted(by_spec.items()):
        template = rows[0]
        active_rows = [row for row in rows if int(row["n"]) > 0]
        global_stats = _merge(active_rows)
        sites = sorted(
            {str(row["site"]) for row in active_rows if row["site"] is not None}
        )
        flightline_count = len({row["flightline_id"] for row in active_rows})
        site_groups = {
            site: [row for row in active_rows if row["site"] == site] for site in sites
        }
        site_moments = {site: _merge(group) for site, group in site_groups.items()}
        translation_rows.append(
            _translation_record(
                template,
                global_stats,
                analysis_run_id=analysis_run_id,
                analysis_level="pixel_pooled",
                weighting="each valid pixel has equal weight",
                flightline_id=None,
                site=None,
                sample_count=global_stats.n,
                source_count=flightline_count,
                flightline_count=flightline_count,
                site_count=len(sites),
                replicate_count=None,
            )
        )
        for row in sorted(active_rows, key=lambda item: item["flightline_id"]):
            stats = BivariateStatistics.from_row(row)
            translation_rows.append(
                _translation_record(
                    row,
                    stats,
                    analysis_run_id=analysis_run_id,
                    analysis_level="per_flightline",
                    weighting="each valid pixel within one flightline has equal weight",
                    flightline_id=row["flightline_id"],
                    site=row["site"],
                    sample_count=stats.n,
                    source_count=1,
                    flightline_count=1,
                    site_count=1 if row["site"] is not None else 0,
                    replicate_count=1,
                )
            )
        for site, stats in site_moments.items():
            translation_rows.append(
                _translation_record(
                    template,
                    stats,
                    analysis_run_id=analysis_run_id,
                    analysis_level="per_site",
                    weighting="each valid pixel within one site has equal weight",
                    flightline_id=None,
                    site=site,
                    sample_count=stats.n,
                    source_count=len(site_groups[site]),
                    flightline_count=len(site_groups[site]),
                    site_count=1,
                    replicate_count=1,
                )
            )
        flightline_balanced = _merge_normalized(
            BivariateStatistics.from_row(row) for row in active_rows
        )
        translation_rows.append(
            _translation_record(
                template,
                flightline_balanced,
                analysis_run_id=analysis_run_id,
                analysis_level="flightline_balanced",
                weighting="each flightline has equal total weight",
                flightline_id=None,
                site=None,
                sample_count=global_stats.n,
                source_count=flightline_count,
                flightline_count=flightline_count,
                site_count=len(sites),
                replicate_count=flightline_count,
                bounds=global_stats,
            )
        )
        if site_moments:
            site_balanced = _merge_normalized(site_moments.values())
            translation_rows.append(
                _translation_record(
                    template,
                    site_balanced,
                    analysis_run_id=analysis_run_id,
                    analysis_level="site_balanced",
                    weighting="each site has equal total weight",
                    flightline_id=None,
                    site=None,
                    sample_count=global_stats.n,
                    source_count=flightline_count,
                    flightline_count=flightline_count,
                    site_count=len(sites),
                    replicate_count=len(sites),
                    bounds=global_stats,
                )
            )
        for site, held_stats in site_moments.items():
            loso_rows.append(
                _loso_record(
                    template,
                    global_stats,
                    held_stats,
                    analysis_run_id=analysis_run_id,
                    site=site,
                    total_sites=len(sites),
                    total_flightlines=flightline_count,
                    held_flightlines=len(site_groups[site]),
                )
            )

    _evaluate_mae(
        flightlines,
        translation_pairs,
        translation_rows,
        loso_rows,
        statistics_rows,
        chunk_size=chunk_size,
        minimum_reflectance=minimum_reflectance,
    )
    translation_rows.sort(
        key=lambda row: (
            row["landsat_sensor"],
            row["band_index"],
            row["analysis_level"],
            row["flightline_id"] or "",
            row["site"] or "",
        )
    )
    loso_rows.sort(
        key=lambda row: (row["landsat_sensor"], row["band_index"], row["held_out_site"])
    )
    output = SensorTranslationPaths(paths.analyses_dir / "sensor_translation")
    loso_output = LeaveOneSiteOutPaths(paths.analyses_dir / "leave_one_site_out")
    output.directory.mkdir(parents=True, exist_ok=True)
    loso_output.directory.mkdir(parents=True, exist_ok=True)
    table_outputs = {
        "translation_pixel_pooled": (
            output.pixel_pooled,
            [row for row in translation_rows if row["analysis_level"] == "pixel_pooled"],
        ),
        "translation_per_flightline": (
            output.per_flightline,
            [row for row in translation_rows if row["analysis_level"] == "per_flightline"],
        ),
        "translation_per_site": (
            output.per_site,
            [row for row in translation_rows if row["analysis_level"] == "per_site"],
        ),
        "translation_flightline_balanced": (
            output.flightline_balanced,
            [row for row in translation_rows if row["analysis_level"] == "flightline_balanced"],
        ),
        "translation_site_balanced": (
            output.site_balanced,
            [row for row in translation_rows if row["analysis_level"] == "site_balanced"],
        ),
    }
    for table_name, (path, records) in table_outputs.items():
        _write_parquet(path, records, _TRANSLATION_SCHEMA)
        con.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet(?)",
            [path.as_posix()],
        )
    candidates = [
        row
        for row in translation_rows
        if row["analysis_level"]
        in {"pixel_pooled", "flightline_balanced", "site_balanced"}
    ]
    _write_parquet(paths.coefficients_parquet, candidates, _TRANSLATION_SCHEMA)
    con.execute(
        "CREATE OR REPLACE TABLE candidate_translation_coefficients AS "
        "SELECT * FROM read_parquet(?)",
        [paths.coefficients_parquet.as_posix()],
    )
    _write_parquet(loso_output.results, loso_rows, _LOSO_SCHEMA)
    con.execute(
        "CREATE OR REPLACE TABLE translation_leave_one_site_out AS "
        "SELECT * FROM read_parquet(?)",
        [loso_output.results.as_posix()],
    )
    pair_count = len(by_spec)
    translation_metadata = {
        "schema_version": 3,
        "analysis": "synthetic_sensor_translation",
        "analysis_engine": "streaming_mergeable_sufficient_statistics",
        "analysis_run_id": analysis_run_id,
        "equation": "target = slope * source + intercept",
        "minimum_reflectance": minimum_reflectance,
        "source_data_policy": "read_only_in_place",
        "pixel_materialization": False,
        "passes_over_source_pixels": 2,
        "second_pass_reason": "exact mean absolute error and held-out evaluation",
        "pair_count": pair_count,
        "candidate_coefficients": candidates,
    }
    loso_metadata = {
        "schema_version": 2,
        "analysis": "leave_one_site_out_synthetic_translation",
        "analysis_engine": "global_minus_held_out_site_sufficient_statistics",
        "analysis_run_id": analysis_run_id,
        "training_fit": "algebraic subtraction of mergeable site moments",
        "held_out_evaluation": "bounded direct second pass for exact MAE",
        "result_count": len(loso_rows),
        "results": loso_rows,
    }
    write_json_atomic(paths.coefficients_json, translation_metadata)
    write_json_atomic(output.metadata, translation_metadata)
    write_json_atomic(loso_output.metadata, loso_metadata)
    return (
        {
            "status": "created",
            "pair_count": pair_count,
            "candidate_count": len(candidates),
            "coefficients_parquet": str(paths.coefficients_parquet),
            "coefficients_json": str(paths.coefficients_json),
        },
        {
            "status": "created",
            "result_count": len(loso_rows),
            "results": str(loso_output.results),
            "metadata": str(loso_output.metadata),
        },
    )


def _merge_normalized(
    values: Iterable[BivariateStatistics],
) -> BivariateStatistics:
    result = BivariateStatistics()
    for value in values:
        result.merge(_normalized(value))
    return result


__all__ = ["run_streaming_translation_analyses"]
