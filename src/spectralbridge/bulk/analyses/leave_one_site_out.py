"""Leave-one-site-out validation for synthetic sensor translation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from spectralbridge.sensor_pairs import SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY

from ..dataset import copy_table_atomic
from ..models import BulkAnalysisPaths
from ..provenance import write_json_atomic
from .common import PairSpec, available_pair_specs, pair_literals, sql_literal, valid_pair_cte


REQUIRED_INPUT_TABLES = ("bulk_observations",)
REQUIRED_PROVENANCE_COLUMNS = (
    "bulk_flightline_id",
    "bulk_site",
)


@dataclass(frozen=True)
class LeaveOneSiteOutPaths:
    directory: Path

    @property
    def results(self) -> Path:
        return self.directory / "leave_one_site_out.parquet"

    @property
    def metadata(self) -> Path:
        return self.directory / "analysis_metadata.json"


_LOSO_COLUMNS = """
    analysis_run_id VARCHAR,
    micasense_sensor VARCHAR,
    landsat_sensor VARCHAR,
    band_index INTEGER,
    x_column VARCHAR,
    y_column VARCHAR,
    held_out_site VARCHAR,
    status VARCHAR,
    training_slope DOUBLE,
    training_intercept DOUBLE,
    training_correlation DOUBLE,
    held_out_rmse DOUBLE,
    held_out_mae DOUBLE,
    held_out_bias DOUBLE,
    held_out_r2 DOUBLE,
    held_out_correlation DOUBLE,
    observed_vs_predicted_slope DOUBLE,
    observed_vs_predicted_intercept DOUBLE,
    training_sample_count BIGINT,
    training_site_count BIGINT,
    training_flightline_count BIGINT,
    held_out_sample_count BIGINT,
    held_out_flightline_count BIGINT
"""


def _loso_query(
    spec: PairSpec,
    *,
    analysis_run_id: str,
    minimum_reflectance: float,
) -> str:
    return f"""
        WITH {valid_pair_cte(spec, minimum_reflectance)},
        site_stats AS (
            SELECT
                bulk_site AS held_out_site,
                COUNT(*)::BIGINT AS n,
                SUM(x) AS sx, SUM(y) AS sy,
                SUM(x * x) AS sxx, SUM(y * y) AS syy, SUM(x * y) AS sxy,
                COUNT(DISTINCT bulk_flightline_id)::BIGINT AS flightline_count
            FROM valid WHERE bulk_site IS NOT NULL
            GROUP BY bulk_site
        ),
        totals AS (
            SELECT
                SUM(n)::BIGINT AS n,
                SUM(sx) AS sx, SUM(sy) AS sy,
                SUM(sxx) AS sxx, SUM(syy) AS syy, SUM(sxy) AS sxy,
                COUNT(*)::BIGINT AS site_count,
                SUM(flightline_count)::BIGINT AS flightline_count
            FROM site_stats
        ),
        training_moments AS (
            SELECT
                held_out_site,
                totals.n - site_stats.n AS training_n,
                totals.sx - site_stats.sx AS sx,
                totals.sy - site_stats.sy AS sy,
                totals.sxx - site_stats.sxx AS sxx,
                totals.syy - site_stats.syy AS syy,
                totals.sxy - site_stats.sxy AS sxy,
                totals.site_count - 1 AS training_site_count,
                totals.flightline_count - site_stats.flightline_count
                    AS training_flightline_count
            FROM site_stats CROSS JOIN totals
        ),
        models_base AS (
            SELECT *,
                (sxy - sx * sy / NULLIF(training_n, 0)) /
                    NULLIF(sxx - sx * sx / NULLIF(training_n, 0), 0) AS slope,
                (sxy - sx * sy / NULLIF(training_n, 0)) /
                    NULLIF(SQRT(
                        (sxx - sx * sx / NULLIF(training_n, 0)) *
                        (syy - sy * sy / NULLIF(training_n, 0))
                    ), 0) AS training_correlation
            FROM training_moments
        ),
        models AS (
            SELECT *, sy / NULLIF(training_n, 0) -
                slope * sx / NULLIF(training_n, 0) AS intercept
            FROM models_base
        ),
        scored AS (
            SELECT
                valid.x, valid.y, valid.bulk_flightline_id,
                models.held_out_site, models.training_n,
                models.training_site_count, models.training_flightline_count,
                models.slope, models.intercept, models.training_correlation,
                models.slope * valid.x + models.intercept AS prediction
            FROM valid JOIN models ON valid.bulk_site = models.held_out_site
        )
        SELECT
            {sql_literal(analysis_run_id)} AS analysis_run_id,
            {pair_literals(spec)},
            held_out_site,
            CASE
                WHEN training_site_count < 1 THEN 'insufficient_sites'
                WHEN training_n < 2 OR NOT COALESCE(isfinite(slope), FALSE)
                    OR NOT COALESCE(isfinite(intercept), FALSE)
                    THEN 'insufficient_training_data'
                WHEN COUNT(*) < 2 THEN 'insufficient_holdout_data'
                ELSE 'ok'
            END AS status,
            CASE WHEN isfinite(slope) THEN slope END AS training_slope,
            CASE WHEN isfinite(intercept) THEN intercept END AS training_intercept,
            CASE WHEN isfinite(training_correlation) THEN training_correlation END
                AS training_correlation,
            CASE WHEN isfinite(SQRT(AVG(POWER(y - prediction, 2))))
                 THEN SQRT(AVG(POWER(y - prediction, 2))) END AS held_out_rmse,
            CASE WHEN isfinite(AVG(ABS(y - prediction)))
                 THEN AVG(ABS(y - prediction)) END AS held_out_mae,
            CASE WHEN isfinite(AVG(y - prediction))
                 THEN AVG(y - prediction) END AS held_out_bias,
            CASE WHEN isfinite(
                1.0 - AVG(POWER(y - prediction, 2)) / NULLIF(VAR_POP(y), 0)
            ) THEN 1.0 - AVG(POWER(y - prediction, 2)) / NULLIF(VAR_POP(y), 0)
            END AS held_out_r2,
            CASE WHEN isfinite(corr(y, prediction)) THEN corr(y, prediction) END
                AS held_out_correlation,
            CASE WHEN isfinite(regr_slope(y, prediction))
                 THEN regr_slope(y, prediction) END AS observed_vs_predicted_slope,
            CASE WHEN isfinite(regr_intercept(y, prediction))
                 THEN regr_intercept(y, prediction) END
                AS observed_vs_predicted_intercept,
            training_n AS training_sample_count,
            training_site_count,
            training_flightline_count,
            COUNT(*)::BIGINT AS held_out_sample_count,
            COUNT(DISTINCT bulk_flightline_id)::BIGINT AS held_out_flightline_count
        FROM scored
        GROUP BY held_out_site, training_n, training_site_count,
                 training_flightline_count, slope, intercept, training_correlation
    """


def _records(con: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    cursor = con.execute(query)
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def run_leave_one_site_out(
    con: duckdb.DuckDBPyConnection,
    paths: BulkAnalysisPaths,
    *,
    analysis_run_id: str,
    minimum_reflectance: float,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Fit on all other sites and score every held-out site."""

    output = LeaveOneSiteOutPaths(paths.analyses_dir / "leave_one_site_out")
    output.directory.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads(output.metadata.read_text(encoding="utf-8"))
        reusable = reuse_existing and (
            previous.get("analysis_run_id") == analysis_run_id
            and output.results.is_file()
            and output.results.stat().st_size > 0
        )
        if reusable:
            pq.read_schema(output.results)
            con.execute(
                "CREATE OR REPLACE TABLE translation_leave_one_site_out AS "
                f"SELECT * FROM read_parquet({sql_literal(output.results.as_posix())})"
            )
            return {
                "status": "reused",
                "result_count": int(previous["result_count"]),
                "results": str(output.results),
                "metadata": str(output.metadata),
            }
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    specs = available_pair_specs(con)
    queries = [
        _loso_query(
            spec,
            analysis_run_id=analysis_run_id,
            minimum_reflectance=minimum_reflectance,
        )
        for spec in specs
    ]
    con.execute("DROP TABLE IF EXISTS translation_leave_one_site_out")
    if queries:
        con.execute(
            "CREATE TABLE translation_leave_one_site_out AS "
            + " UNION ALL ".join(queries)
        )
    else:
        con.execute(
            f"CREATE TABLE translation_leave_one_site_out ({_LOSO_COLUMNS})"
        )
    copy_table_atomic(
        con,
        "SELECT * FROM translation_leave_one_site_out",
        output.results,
    )
    records = _records(
        con,
        "SELECT * FROM translation_leave_one_site_out "
        "ORDER BY landsat_sensor, band_index, held_out_site",
    )
    metadata = {
        "schema_version": 1,
        "analysis": "leave_one_site_out_synthetic_translation",
        "analysis_run_id": analysis_run_id,
        "minimum_reflectance": minimum_reflectance,
        "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
        "interpretation": (
            "For each held-out site, the linear relationship is fitted using "
            "valid pixels from all other sites and evaluated only on the held-out "
            "site. Sites remain the validation units; pixels are nested observations."
        ),
        "result_count": len(records),
        "results": records,
    }
    write_json_atomic(output.metadata, metadata)
    return {
        "status": "created",
        "result_count": len(records),
        "results": str(output.results),
        "metadata": str(output.metadata),
    }


__all__ = [
    "LeaveOneSiteOutPaths",
    "REQUIRED_INPUT_TABLES",
    "REQUIRED_PROVENANCE_COLUMNS",
    "run_leave_one_site_out",
]
