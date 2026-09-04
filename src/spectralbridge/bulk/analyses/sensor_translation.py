"""Hierarchical synthetic MicaSense-to-Landsat translation analysis."""

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
    "bulk_source_id",
    "bulk_flightline_id",
    "bulk_site",
)


@dataclass(frozen=True)
class SensorTranslationPaths:
    directory: Path

    @property
    def pixel_pooled(self) -> Path:
        return self.directory / "pixel_pooled.parquet"

    @property
    def per_flightline(self) -> Path:
        return self.directory / "per_flightline.parquet"

    @property
    def per_site(self) -> Path:
        return self.directory / "per_site.parquet"

    @property
    def flightline_balanced(self) -> Path:
        return self.directory / "flightline_balanced.parquet"

    @property
    def site_balanced(self) -> Path:
        return self.directory / "site_balanced.parquet"

    @property
    def metadata(self) -> Path:
        return self.directory / "analysis_metadata.json"


_TRANSLATION_COLUMNS = """
    analysis_run_id VARCHAR,
    analysis_level VARCHAR,
    weighting VARCHAR,
    micasense_sensor VARCHAR,
    landsat_sensor VARCHAR,
    band_index INTEGER,
    x_column VARCHAR,
    y_column VARCHAR,
    flightline_id VARCHAR,
    site VARCHAR,
    equation VARCHAR,
    status VARCHAR,
    slope DOUBLE,
    intercept DOUBLE,
    correlation DOUBLE,
    r2 DOUBLE,
    bias DOUBLE,
    rmse DOUBLE,
    mae DOUBLE,
    sample_count BIGINT,
    source_count BIGINT,
    flightline_count BIGINT,
    site_count BIGINT,
    replicate_count BIGINT,
    x_min DOUBLE,
    x_max DOUBLE,
    x_mean DOUBLE,
    y_min DOUBLE,
    y_max DOUBLE,
    y_mean DOUBLE
"""


def _grouped_query(
    spec: PairSpec,
    *,
    analysis_run_id: str,
    analysis_level: str,
    minimum_reflectance: float,
) -> str:
    if analysis_level == "pixel_pooled":
        fit_groups = "NULL::VARCHAR AS flightline_id, NULL::VARCHAR AS site,"
        fit_group_by = ""
        join = "CROSS JOIN fit"
        final_group = ""
        identity_final = "NULL::VARCHAR AS flightline_id, NULL::VARCHAR AS site,"
        replicate = "NULL::BIGINT AS replicate_count"
        weighting = "each valid pixel has equal weight"
    elif analysis_level == "per_flightline":
        fit_groups = "bulk_flightline_id AS flightline_id, bulk_site AS site,"
        fit_group_by = "GROUP BY bulk_flightline_id, bulk_site"
        join = (
            "JOIN fit ON valid.bulk_flightline_id = fit.flightline_id "
            "AND valid.bulk_site IS NOT DISTINCT FROM fit.site"
        )
        final_group = "GROUP BY bulk_flightline_id, bulk_site, slope, intercept"
        identity_final = "bulk_flightline_id AS flightline_id, bulk_site AS site,"
        replicate = "1::BIGINT AS replicate_count"
        weighting = "each valid pixel within one flightline has equal weight"
    elif analysis_level == "per_site":
        fit_groups = "NULL::VARCHAR AS flightline_id, bulk_site AS site,"
        fit_group_by = "WHERE bulk_site IS NOT NULL GROUP BY bulk_site"
        join = "JOIN fit ON valid.bulk_site = fit.site"
        final_group = "GROUP BY bulk_site, slope, intercept"
        identity_final = "NULL::VARCHAR AS flightline_id, bulk_site AS site,"
        replicate = "1::BIGINT AS replicate_count"
        weighting = "each valid pixel within one site has equal weight"
    else:  # pragma: no cover - internal contract
        raise ValueError(analysis_level)

    return f"""
        WITH {valid_pair_cte(spec, minimum_reflectance)},
        fit AS (
            SELECT {fit_groups}
                COUNT(*)::BIGINT AS sample_count,
                COUNT(DISTINCT bulk_source_id)::BIGINT AS source_count,
                COUNT(DISTINCT bulk_flightline_id)::BIGINT AS flightline_count,
                COUNT(DISTINCT bulk_site)::BIGINT AS site_count,
                regr_slope(y, x) AS slope,
                regr_intercept(y, x) AS intercept,
                corr(x, y) AS correlation
            FROM valid {fit_group_by}
        ),
        scored AS (
            SELECT valid.*, fit.slope, fit.intercept
            FROM valid {join}
        ),
        errors AS (
            SELECT {identity_final}
                AVG(y - (slope * x + intercept)) AS bias,
                SQRT(AVG(POWER(y - (slope * x + intercept), 2))) AS rmse,
                AVG(ABS(y - (slope * x + intercept))) AS mae,
                MIN(x) AS x_min, MAX(x) AS x_max, AVG(x) AS x_mean,
                MIN(y) AS y_min, MAX(y) AS y_max, AVG(y) AS y_mean
            FROM scored {final_group}
        )
        SELECT
            {sql_literal(analysis_run_id)} AS analysis_run_id,
            {sql_literal(analysis_level)} AS analysis_level,
            {sql_literal(weighting)} AS weighting,
            {pair_literals(spec)},
            fit.flightline_id, fit.site,
            'landsat = slope * micasense + intercept' AS equation,
            CASE WHEN fit.sample_count >= 2 AND isfinite(fit.slope)
                 AND isfinite(fit.intercept) THEN 'ok'
                 ELSE 'insufficient_data' END AS status,
            CASE WHEN isfinite(fit.slope) THEN fit.slope END AS slope,
            CASE WHEN isfinite(fit.intercept) THEN fit.intercept END AS intercept,
            CASE WHEN isfinite(fit.correlation) THEN fit.correlation END AS correlation,
            CASE WHEN isfinite(fit.correlation) THEN fit.correlation * fit.correlation END AS r2,
            CASE WHEN isfinite(errors.bias) THEN errors.bias END AS bias,
            CASE WHEN isfinite(errors.rmse) THEN errors.rmse END AS rmse,
            CASE WHEN isfinite(errors.mae) THEN errors.mae END AS mae,
            fit.sample_count, fit.source_count, fit.flightline_count, fit.site_count,
            {replicate},
            errors.x_min, errors.x_max, errors.x_mean,
            errors.y_min, errors.y_max, errors.y_mean
        FROM fit
        LEFT JOIN errors
          ON fit.flightline_id IS NOT DISTINCT FROM errors.flightline_id
         AND fit.site IS NOT DISTINCT FROM errors.site
    """


def _balanced_query(
    spec: PairSpec,
    *,
    analysis_run_id: str,
    balance_level: str,
    minimum_reflectance: float,
) -> str:
    if balance_level == "flightline":
        group_column = "bulk_flightline_id"
        analysis_level = "flightline_balanced"
        weighting = "each flightline has equal total weight"
    elif balance_level == "site":
        group_column = "bulk_site"
        analysis_level = "site_balanced"
        weighting = "each site has equal total weight"
    else:  # pragma: no cover - internal contract
        raise ValueError(balance_level)
    return f"""
        WITH {valid_pair_cte(spec, minimum_reflectance)},
        group_counts AS (
            SELECT {group_column} AS replicate_id, COUNT(*)::DOUBLE AS group_n
            FROM valid WHERE {group_column} IS NOT NULL
            GROUP BY {group_column}
        ),
        weighted AS (
            SELECT valid.*, 1.0 / group_counts.group_n AS weight
            FROM valid JOIN group_counts ON {group_column} = replicate_id
        ),
        moments AS (
            SELECT
                SUM(weight) AS sw,
                SUM(weight * x) AS sx,
                SUM(weight * y) AS sy,
                SUM(weight * x * x) AS sxx,
                SUM(weight * y * y) AS syy,
                SUM(weight * x * y) AS sxy,
                COUNT(*)::BIGINT AS sample_count,
                COUNT(DISTINCT bulk_source_id)::BIGINT AS source_count,
                COUNT(DISTINCT bulk_flightline_id)::BIGINT AS flightline_count,
                COUNT(DISTINCT bulk_site)::BIGINT AS site_count,
                COUNT(DISTINCT {group_column})::BIGINT AS replicate_count,
                MIN(x) AS x_min, MAX(x) AS x_max,
                MIN(y) AS y_min, MAX(y) AS y_max
            FROM weighted
        ),
        fit AS (
            SELECT *,
                (sxy - sx * sy / sw) / NULLIF(sxx - sx * sx / sw, 0) AS slope,
                sx / sw AS x_mean,
                sy / sw AS y_mean,
                (sxy - sx * sy / sw) /
                    NULLIF(SQRT((sxx - sx * sx / sw) * (syy - sy * sy / sw)), 0)
                    AS correlation
            FROM moments WHERE sw > 0
        ),
        parameters AS (
            SELECT *, y_mean - slope * x_mean AS intercept FROM fit
        ),
        errors AS (
            SELECT
                SUM(weight * (y - (slope * x + intercept))) / SUM(weight) AS bias,
                SQRT(SUM(weight * POWER(y - (slope * x + intercept), 2)) / SUM(weight)) AS rmse,
                SUM(weight * ABS(y - (slope * x + intercept))) / SUM(weight) AS mae
            FROM weighted CROSS JOIN parameters
        )
        SELECT
            {sql_literal(analysis_run_id)} AS analysis_run_id,
            {sql_literal(analysis_level)} AS analysis_level,
            {sql_literal(weighting)} AS weighting,
            {pair_literals(spec)},
            NULL::VARCHAR AS flightline_id, NULL::VARCHAR AS site,
            'landsat = slope * micasense + intercept' AS equation,
            CASE WHEN sample_count >= 2 AND isfinite(slope) AND isfinite(intercept)
                 THEN 'ok' ELSE 'insufficient_data' END AS status,
            CASE WHEN isfinite(slope) THEN slope END AS slope,
            CASE WHEN isfinite(intercept) THEN intercept END AS intercept,
            CASE WHEN isfinite(correlation) THEN correlation END AS correlation,
            CASE WHEN isfinite(correlation) THEN correlation * correlation END AS r2,
            CASE WHEN isfinite(errors.bias) THEN errors.bias END AS bias,
            CASE WHEN isfinite(errors.rmse) THEN errors.rmse END AS rmse,
            CASE WHEN isfinite(errors.mae) THEN errors.mae END AS mae,
            sample_count, source_count, flightline_count, site_count, replicate_count,
            x_min, x_max, x_mean, y_min, y_max, y_mean
        FROM parameters CROSS JOIN errors
    """


def _create_table_from_queries(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    queries: list[str],
) -> None:
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    if not queries:
        con.execute(f"CREATE TABLE {table_name} ({_TRANSLATION_COLUMNS})")
        return
    con.execute(f"CREATE TABLE {table_name} AS " + " UNION ALL ".join(queries))


def _records(con: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    cursor = con.execute(query)
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def run_sensor_translation(
    con: duckdb.DuckDBPyConnection,
    paths: BulkAnalysisPaths,
    *,
    analysis_run_id: str,
    minimum_reflectance: float,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Run pooled, grouped, and equal-replicate synthetic regressions."""

    output = SensorTranslationPaths(paths.analyses_dir / "sensor_translation")
    output.directory.mkdir(parents=True, exist_ok=True)
    reusable_tables = (
        ("translation_pixel_pooled", output.pixel_pooled),
        ("translation_per_flightline", output.per_flightline),
        ("translation_per_site", output.per_site),
        ("translation_flightline_balanced", output.flightline_balanced),
        ("translation_site_balanced", output.site_balanced),
        ("candidate_translation_coefficients", paths.coefficients_parquet),
    )
    try:
        previous = json.loads(output.metadata.read_text(encoding="utf-8"))
        reusable = reuse_existing and (
            previous.get("analysis_run_id") == analysis_run_id
            and paths.coefficients_json.is_file()
            and all(path.is_file() and path.stat().st_size > 0 for _, path in reusable_tables)
        )
        if reusable:
            for _, path in reusable_tables:
                pq.read_schema(path)
            for table_name, path in reusable_tables:
                con.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS "
                    f"SELECT * FROM read_parquet('{path.as_posix().replace("'", "''")}')"
                )
            return {
                "status": "reused",
                "pair_count": int(previous["pair_count"]),
                "candidate_count": len(previous["candidate_coefficients"]),
                "pixel_pooled": str(output.pixel_pooled),
                "per_flightline": str(output.per_flightline),
                "per_site": str(output.per_site),
                "flightline_balanced": str(output.flightline_balanced),
                "site_balanced": str(output.site_balanced),
                "coefficients_parquet": str(paths.coefficients_parquet),
                "coefficients_json": str(paths.coefficients_json),
            }
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    specs = available_pair_specs(con)
    table_specs = (
        (
            "translation_pixel_pooled",
            output.pixel_pooled,
            [
                _grouped_query(
                    spec,
                    analysis_run_id=analysis_run_id,
                    analysis_level="pixel_pooled",
                    minimum_reflectance=minimum_reflectance,
                )
                for spec in specs
            ],
        ),
        (
            "translation_per_flightline",
            output.per_flightline,
            [
                _grouped_query(
                    spec,
                    analysis_run_id=analysis_run_id,
                    analysis_level="per_flightline",
                    minimum_reflectance=minimum_reflectance,
                )
                for spec in specs
            ],
        ),
        (
            "translation_per_site",
            output.per_site,
            [
                _grouped_query(
                    spec,
                    analysis_run_id=analysis_run_id,
                    analysis_level="per_site",
                    minimum_reflectance=minimum_reflectance,
                )
                for spec in specs
            ],
        ),
        (
            "translation_flightline_balanced",
            output.flightline_balanced,
            [
                _balanced_query(
                    spec,
                    analysis_run_id=analysis_run_id,
                    balance_level="flightline",
                    minimum_reflectance=minimum_reflectance,
                )
                for spec in specs
            ],
        ),
        (
            "translation_site_balanced",
            output.site_balanced,
            [
                _balanced_query(
                    spec,
                    analysis_run_id=analysis_run_id,
                    balance_level="site",
                    minimum_reflectance=minimum_reflectance,
                )
                for spec in specs
            ],
        ),
    )
    for table_name, target, queries in table_specs:
        _create_table_from_queries(con, table_name, queries)
        copy_table_atomic(con, f"SELECT * FROM {table_name}", target)

    con.execute("DROP TABLE IF EXISTS candidate_translation_coefficients")
    con.execute(
        """
        CREATE TABLE candidate_translation_coefficients AS
        SELECT * FROM translation_pixel_pooled
        UNION ALL SELECT * FROM translation_flightline_balanced
        UNION ALL SELECT * FROM translation_site_balanced
        """
    )
    copy_table_atomic(
        con,
        "SELECT * FROM candidate_translation_coefficients",
        paths.coefficients_parquet,
    )
    candidates = _records(
        con,
        "SELECT * FROM candidate_translation_coefficients "
        "ORDER BY landsat_sensor, band_index, analysis_level",
    )
    metadata = {
        "schema_version": 2,
        "analysis": "synthetic_sensor_translation",
        "analysis_run_id": analysis_run_id,
        "equation": "landsat = slope * micasense + intercept",
        "minimum_reflectance": minimum_reflectance,
        "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
        "statistical_independence_note": (
            "Pixels are observations nested within flightlines and sites. "
            "Flightline- and site-balanced estimates give each replicate equal "
            "total weight; pixel-pooled estimates do not imply pixel-level "
            "landscape replication."
        ),
        "candidate_status": "not_approved_for_empirical_calibration",
        "pair_count": len(specs),
        "candidate_coefficients": candidates,
    }
    write_json_atomic(paths.coefficients_json, metadata)
    write_json_atomic(output.metadata, metadata)
    return {
        "status": "created",
        "pair_count": len(specs),
        "candidate_count": len(candidates),
        "pixel_pooled": str(output.pixel_pooled),
        "per_flightline": str(output.per_flightline),
        "per_site": str(output.per_site),
        "flightline_balanced": str(output.flightline_balanced),
        "site_balanced": str(output.site_balanced),
        "coefficients_parquet": str(paths.coefficients_parquet),
        "coefficients_json": str(paths.coefficients_json),
    }


__all__ = [
    "REQUIRED_INPUT_TABLES",
    "REQUIRED_PROVENANCE_COLUMNS",
    "SensorTranslationPaths",
    "run_sensor_translation",
]
