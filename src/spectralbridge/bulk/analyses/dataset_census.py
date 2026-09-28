"""Fast catalog-only preflight census for a bulk collection."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from ..dataset import copy_table_atomic
from ..models import BulkAnalysisPaths
from ..provenance import write_json_atomic, write_text_atomic
from .common import sql_literal


REQUIRED_INPUT_TABLES = ("flightlines", "source_files")


@dataclass(frozen=True)
class DatasetCensusPaths:
    directory: Path

    @property
    def summary_parquet(self) -> Path:
        return self.directory / "dataset_census.parquet"

    @property
    def summary_json(self) -> Path:
        return self.directory / "dataset_census.json"

    @property
    def report(self) -> Path:
        return self.directory / "dataset_census.md"

    @property
    def by_site(self) -> Path:
        return self.directory / "by_site.parquet"

    @property
    def by_year(self) -> Path:
        return self.directory / "by_year.parquet"

    @property
    def by_sensor(self) -> Path:
        return self.directory / "by_sensor.parquet"

    @property
    def by_schema(self) -> Path:
        return self.directory / "by_schema.parquet"

    @property
    def by_product(self) -> Path:
        return self.directory / "by_product.parquet"

    @property
    def missing_products(self) -> Path:
        return self.directory / "missing_products.parquet"

    @property
    def inconsistencies(self) -> Path:
        return self.directory / "inconsistencies.parquet"

    @property
    def by_exclusion_reason(self) -> Path:
        return self.directory / "by_exclusion_reason.parquet"


def _scalar(con: duckdb.DuckDBPyConnection, query: str) -> int:
    row = con.execute(query).fetchone()
    return int((row or (0,))[0] or 0)


def _list_values(con: duckdb.DuckDBPyConnection, query: str) -> list[str]:
    return [str(row[0]) for row in con.execute(query).fetchall() if row[0] is not None]


def run_dataset_census(
    con: duckdb.DuckDBPyConnection,
    paths: BulkAnalysisPaths,
    *,
    analysis_run_id: str,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Write metadata-only census tables without scanning observation values."""

    output = DatasetCensusPaths(paths.analyses_dir / "dataset_census")
    output.directory.mkdir(parents=True, exist_ok=True)
    table_outputs = (
        ("dataset_census_summary", output.summary_parquet),
        ("dataset_census_by_site", output.by_site),
        ("dataset_census_by_year", output.by_year),
        ("dataset_census_by_sensor", output.by_sensor),
        ("dataset_census_by_schema", output.by_schema),
        ("dataset_census_by_product", output.by_product),
        ("dataset_census_missing_products", output.missing_products),
        ("dataset_census_inconsistencies", output.inconsistencies),
        ("dataset_census_by_exclusion_reason", output.by_exclusion_reason),
    )
    try:
        previous = json.loads(output.summary_json.read_text(encoding="utf-8"))
        reusable = reuse_existing and (
            previous.get("analysis_run_id") == analysis_run_id
            and output.report.is_file()
            and all(path.is_file() and path.stat().st_size > 0 for _, path in table_outputs)
        )
        if reusable:
            for _, path in table_outputs:
                pq.read_schema(path)
            for table, path in table_outputs:
                con.execute(
                    f"CREATE OR REPLACE TABLE {table} AS "
                    f"SELECT * FROM read_parquet({sql_literal(path.as_posix())})"
                )
            summary = {
                key: value
                for key, value in previous.items()
                if key not in {"schema_version", "analysis", "observation_scan_performed"}
            }
            return {
                "status": "reused",
                "summary": summary,
                "summary_parquet": str(output.summary_parquet),
                "summary_json": str(output.summary_json),
                "report": str(output.report),
                "missing_products": str(output.missing_products),
            }
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_missing_products AS
        WITH expected_products AS (
            SELECT source.product_key,
                   ANY_VALUE(source.product_role) AS product_role,
                   ANY_VALUE(source.sensor_name) AS sensor_name,
                   ANY_VALUE(source.product_semantics) AS product_semantics
            FROM source_files source
            JOIN flightlines flight USING (candidate_id)
            WHERE flight.status = 'accepted'
              AND source.status = 'available'
              AND source.storage_format = 'parquet'
              AND source.product_key IS NOT NULL
              AND NOT starts_with(source.product_key, 'unregistered_tabular::')
            GROUP BY source.product_key
        ), accepted_flights AS (
            SELECT candidate_id, canonical_flightline_id, source_directory
            FROM flightlines WHERE status = 'accepted'
        )
        SELECT flight.canonical_flightline_id, flight.source_directory,
               product.product_key, product.product_role, product.sensor_name,
               product.product_semantics,
               'missing_tabular_product' AS reason_code,
               'Canonical tabular product is present elsewhere in the accepted '
               || 'campaign but absent from this flight.' AS detail
        FROM accepted_flights flight
        CROSS JOIN expected_products product
        LEFT JOIN source_files source
          ON source.candidate_id = flight.candidate_id
         AND source.product_key = product.product_key
         AND source.status = 'available'
        WHERE source.source_id IS NULL
        ORDER BY flight.canonical_flightline_id, product.product_key
        """
    )
    summary = {
        "analysis_run_id": analysis_run_id,
        "candidate_source_directories": _scalar(
            con, "SELECT COUNT(DISTINCT source_directory) FROM flightlines"
        ),
        "candidate_outer_batch_folders": _scalar(
            con,
            "SELECT COUNT(DISTINCT COALESCE("
            "json_extract_string(source_provenance_json, '$.outer_storage_path'), "
            "source_directory)) FROM flightlines",
        ),
        "candidate_flightline_records": _scalar(con, "SELECT COUNT(*) FROM flightlines"),
        "accepted_canonical_flightlines": _scalar(
            con, "SELECT COUNT(*) FROM flightlines WHERE status = 'accepted'"
        ),
        "unique_canonical_flightlines": _scalar(
            con,
            "SELECT COUNT(DISTINCT canonical_flightline_id) FROM flightlines "
            "WHERE status = 'accepted'",
        ),
        "duplicate_candidates": _scalar(con, "SELECT COUNT(*) FROM duplicates"),
        "duplicate_canonical_ids": _scalar(
            con, "SELECT COUNT(DISTINCT canonical_flightline_id) FROM duplicates"
        ),
        "rejected_flightline_records": _scalar(
            con, "SELECT COUNT(*) FROM rejected_sources"
        ),
        "total_source_tree_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(source_directory_size_bytes), 0) FROM ("
            "SELECT source_directory, MAX(source_directory_size_bytes) "
            "AS source_directory_size_bytes FROM flightlines "
            "GROUP BY source_directory)",
        ),
        "candidate_merged_parquet_bytes": _scalar(
            con, "SELECT COALESCE(SUM(size_bytes), 0) FROM source_files"
        ),
        "accepted_merged_parquet_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(size_bytes), 0) FROM source_files "
            "WHERE status IN ('accepted', 'available')",
        ),
        "accepted_observation_rows": _scalar(
            con, "SELECT COALESCE(SUM(row_count), 0) FROM flightlines WHERE status = 'accepted'"
        ),
        "selected_source_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(source.size_bytes), 0) FROM source_files source "
            "JOIN flightlines flight USING (candidate_id) "
            "WHERE flight.status = 'accepted' AND EXISTS ("
            "SELECT 1 FROM json_each(flight.selected_source_ids_json) selected "
            "WHERE json_extract_string(selected.value, '$') = source.source_id)",
        ),
        "translation_eligible_flightlines": _scalar(
            con,
            "SELECT COUNT(*) FROM flightlines "
            "WHERE status = 'accepted' AND translation_eligible",
        ),
        "translation_available_flightlines": _scalar(
            con,
            "SELECT COUNT(*) FROM flightlines "
            "WHERE status = 'accepted' AND translation_available",
        ),
        "scientifically_blocked_flightlines": _scalar(
            con,
            "SELECT COUNT(*) FROM flightlines WHERE status = 'accepted' "
            "AND scientific_status = 'translation_available_descriptive_only'",
        ),
        "estimated_analysis_cache_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(estimated_analysis_output_bytes), 0) FROM flightlines "
            "WHERE status = 'accepted'",
        ),
        "estimated_materialized_pixel_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(estimated_materialized_pixel_bytes), 0) "
            "FROM flightlines WHERE status = 'accepted'",
        ),
        "qa_available_flightlines": _scalar(
            con,
            "SELECT COUNT(*) FROM flightlines WHERE status = 'accepted' "
            "AND qa_status <> 'missing'",
        ),
        "corrected_products_found": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files "
            "WHERE product_role = 'corrected_hyperspectral' "
            "AND status NOT IN ('rejected', 'duplicate_excluded')",
        ),
        "raw_products_found": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files "
            "WHERE product_role = 'raw_hyperspectral' "
            "AND status NOT IN ('rejected', 'duplicate_excluded')",
        ),
        "target_sensor_products_found": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files WHERE product_role = 'target_sensor' "
            "AND status NOT IN ('rejected', 'duplicate_excluded')",
        ),
        "tabular_products_found": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files source JOIN flightlines flight "
            "USING (candidate_id) WHERE flight.status = 'accepted' "
            "AND source.storage_format = 'parquet' "
            "AND source.status = 'available'",
        ),
        "tabular_product_rows": _scalar(
            con,
            "SELECT COALESCE(SUM(source.row_count), 0) FROM source_files source "
            "JOIN flightlines flight USING (candidate_id) "
            "WHERE flight.status = 'accepted' AND source.storage_format = 'parquet' "
            "AND source.status = 'available'",
        ),
        "tabular_product_bytes": _scalar(
            con,
            "SELECT COALESCE(SUM(source.size_bytes), 0) FROM source_files source "
            "JOIN flightlines flight USING (candidate_id) "
            "WHERE flight.status = 'accepted' AND source.storage_format = 'parquet' "
            "AND source.status = 'available'",
        ),
        "unregistered_tabular_products": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files source JOIN flightlines flight "
            "USING (candidate_id) WHERE flight.status = 'accepted' "
            "AND source.storage_format = 'parquet' "
            "AND source.product_role = 'unregistered_tabular'",
        ),
        "duplicate_product_candidates": _scalar(
            con,
            "SELECT COUNT(*) FROM source_files WHERE reason_code = 'duplicate_product'",
        ),
        "missing_tabular_product_instances": _scalar(
            con, "SELECT COUNT(*) FROM dataset_census_missing_products"
        ),
        "sites": _list_values(
            con,
            "SELECT DISTINCT site FROM flightlines WHERE status = 'accepted' "
            "AND site IS NOT NULL ORDER BY site",
        ),
        "acquisition_dates": _list_values(
            con,
            "SELECT DISTINCT acquisition_date FROM flightlines WHERE status = 'accepted' "
            "AND acquisition_date IS NOT NULL ORDER BY acquisition_date",
        ),
        "acquisition_years": [
            int(value)
            for value in _list_values(
                con,
                "SELECT DISTINCT acquisition_year FROM flightlines WHERE status = 'accepted' "
                "AND acquisition_year IS NOT NULL ORDER BY acquisition_year",
            )
        ],
        "sensors": _list_values(
            con,
            "SELECT DISTINCT json_extract_string(item.value, '$') AS sensor "
            "FROM flightlines, json_each(available_sensors_json) AS item "
            "WHERE status = 'accepted' ORDER BY sensor",
        ),
        "schema_fingerprints": _list_values(
            con,
            "SELECT DISTINCT schema_sha256 FROM source_files "
            "WHERE status IN ('accepted', 'available') "
            "AND schema_sha256 IS NOT NULL ORDER BY schema_sha256",
        ),
        "analysis_profiles": _list_values(
            con,
            "SELECT DISTINCT analysis_profile FROM flightlines "
            "WHERE analysis_profile IS NOT NULL ORDER BY analysis_profile",
        ),
        "available_translation_pairs": _list_values(
            con,
            "SELECT DISTINCT item.key FROM flightlines, "
            "json_each(translation_availability_json) item "
            "WHERE status = 'accepted' AND TRY_CAST(item.value AS BOOLEAN) "
            "ORDER BY item.key",
        ),
        "regression_eligible_translation_pairs": _list_values(
            con,
            "SELECT DISTINCT item.key FROM flightlines, "
            "json_each(analysis_eligibility_json) item "
            "WHERE status = 'accepted' AND TRY_CAST(item.value AS BOOLEAN) "
            "ORDER BY item.key",
        ),
        "qa_status_counts": {
            str(status): int(count)
            for status, count in con.execute(
                "SELECT qa_status, COUNT(*) FROM flightlines "
                "WHERE status = 'accepted' GROUP BY qa_status ORDER BY qa_status"
            ).fetchall()
        },
        "schema_inconsistent_product_keys": _list_values(
            con,
            "SELECT COALESCE(product_key, relative_path) FROM source_files source "
            "JOIN flightlines flight USING (candidate_id) "
            "WHERE flight.status = 'accepted' AND source.storage_format = 'parquet' "
            "AND source.status = 'available' GROUP BY ALL "
            "HAVING COUNT(DISTINCT schema_sha256) > 1 ORDER BY 1",
        ),
        "exclusion_counts_by_reason": {
            str(reason): int(count)
            for reason, count in con.execute(
                "SELECT reason_code, COUNT(*) FROM exclusions "
                "GROUP BY reason_code ORDER BY reason_code"
            ).fetchall()
        },
    }
    # Preserve the former key for compatibility while exposing the architectural
    # meaning directly to new callers.
    summary["estimated_analysis_output_bytes"] = summary[
        "estimated_analysis_cache_bytes"
    ]
    summary["tabular_schemas_consistent_by_product"] = not bool(
        summary["schema_inconsistent_product_keys"]
    )
    con.execute("DROP TABLE IF EXISTS dataset_census_summary")
    con.execute(
        """
        CREATE TABLE dataset_census_summary AS SELECT
            ?::VARCHAR AS analysis_run_id,
            ?::BIGINT AS candidate_source_directories,
            ?::BIGINT AS candidate_outer_batch_folders,
            ?::BIGINT AS candidate_flightline_records,
            ?::BIGINT AS accepted_canonical_flightlines,
            ?::BIGINT AS unique_canonical_flightlines,
            ?::BIGINT AS duplicate_candidates,
            ?::BIGINT AS duplicate_canonical_ids,
            ?::BIGINT AS rejected_flightline_records,
            ?::BIGINT AS total_source_tree_bytes,
            ?::BIGINT AS candidate_merged_parquet_bytes,
            ?::BIGINT AS accepted_merged_parquet_bytes,
            ?::BIGINT AS accepted_observation_rows,
            ?::BIGINT AS selected_source_bytes,
            ?::BIGINT AS translation_eligible_flightlines,
            ?::BIGINT AS translation_available_flightlines,
            ?::BIGINT AS scientifically_blocked_flightlines,
            ?::BIGINT AS estimated_analysis_cache_bytes,
            ?::BIGINT AS estimated_analysis_output_bytes,
            ?::BIGINT AS estimated_materialized_pixel_bytes,
            ?::BIGINT AS qa_available_flightlines,
            ?::BIGINT AS corrected_products_found,
            ?::BIGINT AS raw_products_found,
            ?::BIGINT AS target_sensor_products_found,
            ?::BIGINT AS tabular_products_found,
            ?::BIGINT AS tabular_product_rows,
                ?::BIGINT AS tabular_product_bytes,
                ?::BIGINT AS unregistered_tabular_products,
                ?::BIGINT AS duplicate_product_candidates,
                ?::BIGINT AS missing_tabular_product_instances,
                ?::VARCHAR AS sites_json,
            ?::VARCHAR AS acquisition_dates_json,
            ?::VARCHAR AS acquisition_years_json,
            ?::VARCHAR AS sensors_json,
            ?::VARCHAR AS schema_fingerprints_json,
            ?::VARCHAR AS analysis_profiles_json,
            ?::VARCHAR AS available_translation_pairs_json,
            ?::VARCHAR AS regression_eligible_translation_pairs_json,
            ?::VARCHAR AS qa_status_counts_json,
            ?::VARCHAR AS schema_inconsistent_product_keys_json,
            ?::BOOLEAN AS tabular_schemas_consistent_by_product,
            ?::VARCHAR AS exclusion_counts_by_reason_json
        """,
        [
            summary["analysis_run_id"],
            summary["candidate_source_directories"],
            summary["candidate_outer_batch_folders"],
            summary["candidate_flightline_records"],
            summary["accepted_canonical_flightlines"],
            summary["unique_canonical_flightlines"],
            summary["duplicate_candidates"],
            summary["duplicate_canonical_ids"],
            summary["rejected_flightline_records"],
            summary["total_source_tree_bytes"],
            summary["candidate_merged_parquet_bytes"],
            summary["accepted_merged_parquet_bytes"],
            summary["accepted_observation_rows"],
            summary["selected_source_bytes"],
            summary["translation_eligible_flightlines"],
            summary["translation_available_flightlines"],
            summary["scientifically_blocked_flightlines"],
            summary["estimated_analysis_cache_bytes"],
            summary["estimated_analysis_output_bytes"],
            summary["estimated_materialized_pixel_bytes"],
            summary["qa_available_flightlines"],
            summary["corrected_products_found"],
            summary["raw_products_found"],
            summary["target_sensor_products_found"],
            summary["tabular_products_found"],
            summary["tabular_product_rows"],
                summary["tabular_product_bytes"],
                summary["unregistered_tabular_products"],
                summary["duplicate_product_candidates"],
                summary["missing_tabular_product_instances"],
                json.dumps(summary["sites"]),
            json.dumps(summary["acquisition_dates"]),
            json.dumps(summary["acquisition_years"]),
            json.dumps(summary["sensors"]),
            json.dumps(summary["schema_fingerprints"]),
            json.dumps(summary["analysis_profiles"]),
            json.dumps(summary["available_translation_pairs"]),
            json.dumps(summary["regression_eligible_translation_pairs"]),
            json.dumps(summary["qa_status_counts"], sort_keys=True),
            json.dumps(summary["schema_inconsistent_product_keys"]),
            summary["tabular_schemas_consistent_by_product"],
            json.dumps(summary["exclusion_counts_by_reason"]),
        ],
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_site AS
        SELECT site, COUNT(*) AS flightline_count,
               COALESCE(SUM(row_count), 0)::BIGINT AS row_count,
               COALESCE(SUM(size_bytes), 0)::BIGINT AS size_bytes,
               COUNT(*) FILTER (WHERE translation_eligible) AS translation_eligible_count
        FROM flightlines WHERE status = 'accepted'
        GROUP BY site ORDER BY site
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_year AS
        SELECT acquisition_year, COUNT(*) AS flightline_count,
               COALESCE(SUM(row_count), 0)::BIGINT AS row_count
        FROM flightlines WHERE status = 'accepted'
        GROUP BY acquisition_year ORDER BY acquisition_year
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_sensor AS
        SELECT json_extract_string(item.value, '$') AS sensor,
               COUNT(DISTINCT canonical_flightline_id) AS flightline_count
        FROM flightlines, json_each(available_sensors_json) AS item
        WHERE status = 'accepted'
        GROUP BY sensor ORDER BY sensor
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_schema AS
        SELECT schema_sha256, COUNT(*) AS source_file_count,
               COALESCE(SUM(row_count), 0)::BIGINT AS row_count
        FROM source_files WHERE status IN ('accepted', 'available')
               AND schema_sha256 IS NOT NULL
        GROUP BY schema_sha256 ORDER BY schema_sha256
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_product AS
        WITH accepted_count AS (
            SELECT COUNT(*)::BIGINT AS value
            FROM flightlines WHERE status = 'accepted'
        )
        SELECT COALESCE(source.product_key, source.relative_path) AS product_key,
               source.product_role,
               source.sensor_name,
               source.storage_format,
               source.product_semantics,
               COUNT(*)::BIGINT AS product_count,
               COUNT(DISTINCT source.canonical_flightline_id)::BIGINT
                   AS flightline_count,
               MAX(accepted_count.value) AS expected_flightline_count,
               (MAX(accepted_count.value)
                - COUNT(DISTINCT source.canonical_flightline_id))::BIGINT
                   AS missing_flightline_count,
               COALESCE(SUM(source.row_count), 0)::BIGINT AS row_count,
               COALESCE(SUM(source.size_bytes), 0)::BIGINT AS size_bytes,
               COUNT(DISTINCT source.schema_sha256)::BIGINT AS schema_count
        FROM source_files source
        JOIN flightlines flight USING (candidate_id)
        CROSS JOIN accepted_count
        WHERE flight.status = 'accepted' AND source.status = 'available'
        GROUP BY ALL
        ORDER BY product_role, sensor_name, product_key
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_inconsistencies AS
        SELECT canonical_flightline_id, source_directory,
               status AS issue_type, rejection_reason AS detail
        FROM flightlines WHERE status <> 'accepted'
        UNION ALL
        SELECT canonical_flightline_id, source_directory,
               'missing_qa' AS issue_type, 'No QA product was discovered.' AS detail
        FROM flightlines WHERE status = 'accepted' AND qa_products_json = '[]'
        UNION ALL
        SELECT canonical_flightline_id, source_directory,
               'missing_processing_metadata' AS issue_type,
               'No processing metadata product was discovered.' AS detail
        FROM flightlines WHERE status = 'accepted' AND metadata_products_json = '[]'
        UNION ALL
        SELECT canonical_flightline_id, source_directory,
               'translation_unavailable' AS issue_type,
               'No compatible requested sensor translation pair was found.' AS detail
        FROM flightlines WHERE status = 'accepted' AND NOT translation_available
        UNION ALL
        SELECT canonical_flightline_id, source_directory,
               'scientifically_blocked' AS issue_type,
               'Translation products are available, but they are not independent regression evidence.' AS detail
        FROM flightlines WHERE status = 'accepted' AND translation_available
             AND NOT translation_eligible
        UNION ALL
        SELECT canonical_flightline_id, source_directory,
               reason_code AS issue_type,
               detail || ' Product: ' || product_key AS detail
        FROM dataset_census_missing_products
        ORDER BY canonical_flightline_id, source_directory, issue_type
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_census_by_exclusion_reason AS
        SELECT reason_code, COUNT(*)::BIGINT AS exclusion_count,
               COUNT(DISTINCT canonical_flightline_id)::BIGINT
                   AS flightline_count
        FROM exclusions GROUP BY reason_code ORDER BY reason_code
        """
    )
    for table, target in table_outputs:
        copy_table_atomic(con, f"SELECT * FROM {table}", target)
    write_json_atomic(
        output.summary_json,
        {
            "schema_version": 1,
            "analysis": "dataset_census",
            "observation_scan_performed": False,
            **summary,
        },
    )
    report = f"""# SpectralBridge bulk dataset census

Analysis run: `{analysis_run_id}`

- Candidate source directories: {summary['candidate_source_directories']}
- Candidate outer storage folders: {summary['candidate_outer_batch_folders']}
- Accepted canonical flightlines: {summary['accepted_canonical_flightlines']}
- Duplicate candidates excluded: {summary['duplicate_candidates']}
- Rejected flightline records: {summary['rejected_flightline_records']}
- Total source-tree bytes: {summary['total_source_tree_bytes']:,}
- Accepted valid rows (source metadata or streamed statistics): {summary['accepted_observation_rows']:,}
- Selected source bytes: {summary['selected_source_bytes']:,}
- Accepted analysis-table/cache bytes: {summary['accepted_merged_parquet_bytes']:,}
- Canonical per-flight tabular products: {summary['tabular_products_found']}
- Tabular product rows (summed across products): {summary['tabular_product_rows']:,}
- Tabular product bytes: {summary['tabular_product_bytes']:,}
- Unregistered tabular products: {summary['unregistered_tabular_products']}
- Duplicate product candidates: {summary['duplicate_product_candidates']}
- Missing tabular product instances: {summary['missing_tabular_product_instances']}
- Tabular schemas consistent within product identities: {summary['tabular_schemas_consistent_by_product']}
- Translation-eligible flightlines: {summary['translation_eligible_flightlines']}
- Translation-available flightlines: {summary['translation_available_flightlines']}
- Scientifically blocked flightlines: {summary['scientifically_blocked_flightlines']}
- QA available: {summary['qa_available_flightlines']} flightlines
- Corrected ENVI products found: {summary['corrected_products_found']}
- Raw ENVI products found: {summary['raw_products_found']}
- Target-sensor ENVI products found: {summary['target_sensor_products_found']}
- Estimated compact analysis-output bytes: {summary['estimated_analysis_output_bytes']:,}
- Estimated explicit materialized-pixel bytes: {summary['estimated_materialized_pixel_bytes']:,}
- Sites: {', '.join(summary['sites']) or 'none'}
- Years: {', '.join(str(item) for item in summary['acquisition_years']) or 'none'}
- Sensors: {', '.join(summary['sensors']) or 'none'}
- Analysis profiles: {', '.join(summary['analysis_profiles']) or 'none'}
- Available translation pairs: {', '.join(summary['available_translation_pairs']) or 'none'}
- Regression-eligible translation pairs: {', '.join(summary['regression_eligible_translation_pairs']) or 'none'}
- QA states: {json.dumps(summary['qa_status_counts'], sort_keys=True)}
- Schema inconsistencies by product: {', '.join(summary['schema_inconsistent_product_keys']) or 'none'}
- Exclusions by reason: {json.dumps(summary['exclusion_counts_by_reason'], sort_keys=True)}

Counts come from canonical identity, ENVI headers, file metadata, JSON QA, and
Parquet footers where present. No raster population or full observation scan is
performed by this preflight analysis. Review the duplicate, rejected-source,
exclusion, and inconsistency catalogs before interpreting population results.
"""
    write_text_atomic(output.report, report)
    return {
        "status": "created",
        "summary": summary,
        "summary_parquet": str(output.summary_parquet),
        "summary_json": str(output.summary_json),
        "report": str(output.report),
        "missing_products": str(output.missing_products),
    }


__all__ = ["DatasetCensusPaths", "REQUIRED_INPUT_TABLES", "run_dataset_census"]
