"""DuckDB-backed virtual observation dataset and catalog persistence."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

import duckdb
import pyarrow.parquet as pq

from .models import BulkAnalysisPaths, FlightlineRecord, SourceFileRecord


def quote_path(path: str | Path) -> str:
    return Path(path).as_posix().replace("'", "''")


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def configure_duckdb(
    con: duckdb.DuckDBPyConnection,
    *,
    memory_limit: str | None,
    threads: int | None,
    temp_directory: Path | None,
) -> None:
    """Apply bounded-resource settings used by catalog and analysis queries."""

    if memory_limit:
        con.execute("SET memory_limit = ?", [memory_limit])
    if threads is not None:
        if threads < 1:
            raise ValueError("threads must be at least 1")
        con.execute(f"SET threads = {int(threads)}")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        con.execute("SET temp_directory = ?", [temp_directory.as_posix()])
        con.execute("SET preserve_insertion_order = false")


def copy_table_atomic(
    con: duckdb.DuckDBPyConnection,
    table_or_query: str,
    output_path: Path,
    *,
    row_group_size: int | None = None,
) -> Path:
    """Write a small table or projected query to Parquet atomically."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    options = "FORMAT PARQUET, COMPRESSION ZSTD"
    if row_group_size is not None:
        if row_group_size < 1:
            raise ValueError("row_group_size must be at least 1")
        options += f", ROW_GROUP_SIZE {int(row_group_size)}"
    con.execute(
        f"COPY ({table_or_query}) TO '{quote_path(temporary)}' ({options})"
    )
    pq.read_schema(temporary)
    temporary.replace(output_path)
    return output_path


_SOURCE_FILES_DDL = """
CREATE TABLE source_files (
    source_id VARCHAR,
    candidate_id VARCHAR,
    canonical_flightline_id VARCHAR,
    identity_source VARCHAR,
    site VARCHAR,
    acquisition_date VARCHAR,
    source_directory VARCHAR,
    source_path VARCHAR,
    relative_path VARCHAR,
    input_kind VARCHAR,
    status VARCHAR,
    reason VARCHAR,
    row_count BIGINT,
    column_count BIGINT,
    size_bytes BIGINT,
    modified_time_ns BIGINT,
    schema_sha256 VARCHAR,
    available_sensors_json VARCHAR,
    translation_eligible BOOLEAN
)
"""


_FLIGHTLINES_DDL = """
CREATE TABLE flightlines (
    candidate_id VARCHAR,
    canonical_flightline_id VARCHAR,
    identity_source VARCHAR,
    site VARCHAR,
    acquisition_date VARCHAR,
    acquisition_year INTEGER,
    source_directory VARCHAR,
    canonical_merged_parquet VARCHAR,
    polygon_merged_parquet VARCHAR,
    selected_source_ids_json VARCHAR,
    selected_source_paths_json VARCHAR,
    qa_products_json VARCHAR,
    metadata_products_json VARCHAR,
    available_sensors_json VARCHAR,
    processing_stages_json VARCHAR,
    row_count BIGINT,
    size_bytes BIGINT,
    source_directory_size_bytes BIGINT,
    schema_fingerprints_json VARCHAR,
    brightness_state_json VARCHAR,
    correction_state_json VARCHAR,
    translation_eligible BOOLEAN,
    status VARCHAR,
    rejection_reason VARCHAR,
    duplicate_status VARCHAR,
    duplicate_candidate_count INTEGER,
    source_provenance_json VARCHAR
)
"""


def _insert_dataclasses(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    records: Sequence[Any],
) -> None:
    if not records:
        return
    values = [tuple(asdict(record).values()) for record in records]
    placeholders = ", ".join("?" for _ in values[0])
    con.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", values)


def _case_expression(
    sources: Sequence[SourceFileRecord],
    attribute: str,
    *,
    default: str = "NULL",
) -> str:
    clauses: list[str] = []
    for source in sources:
        value = getattr(source, attribute)
        if value is None:
            rendered = "NULL"
        elif isinstance(value, bool):
            rendered = "TRUE" if value else "FALSE"
        else:
            rendered = "'" + str(value).replace("'", "''") + "'"
        clauses.append(
            "WHEN '" + quote_path(source.source_path) + f"' THEN {rendered}"
        )
    return "CASE filename " + " ".join(clauses) + f" ELSE {default} END"


def _create_observation_views(
    con: duckdb.DuckDBPyConnection,
    accepted_sources: Sequence[SourceFileRecord],
    paths: BulkAnalysisPaths,
    *,
    materialize_observations: bool,
    row_group_size: int,
) -> None:
    if not accepted_sources:
        con.execute(
            """
            CREATE VIEW bulk_observations_virtual AS
            SELECT
                CAST(NULL AS VARCHAR) AS bulk_source_path,
                CAST(NULL AS VARCHAR) AS bulk_source_relative_path,
                CAST(NULL AS VARCHAR) AS bulk_source_kind,
                CAST(NULL AS VARCHAR) AS bulk_source_id,
                CAST(NULL AS VARCHAR) AS bulk_flightline_id,
                CAST(NULL AS VARCHAR) AS bulk_site,
                CAST(NULL AS VARCHAR) AS bulk_acquisition_date
            WHERE FALSE
            """
        )
    else:
        files_sql = ", ".join(
            "'" + quote_path(source.source_path) + "'" for source in accepted_sources
        )
        relative_case = _case_expression(accepted_sources, "relative_path", default="filename")
        kind_case = _case_expression(accepted_sources, "input_kind")
        source_id_case = _case_expression(accepted_sources, "source_id")
        flightline_case = _case_expression(
            accepted_sources, "canonical_flightline_id"
        )
        site_case = _case_expression(accepted_sources, "site")
        date_case = _case_expression(accepted_sources, "acquisition_date")
        con.execute(
            f"""
            CREATE VIEW bulk_observations_virtual AS
            SELECT
                * EXCLUDE (filename),
                filename AS bulk_source_path,
                {relative_case} AS bulk_source_relative_path,
                {kind_case} AS bulk_source_kind,
                {source_id_case} AS bulk_source_id,
                {flightline_case} AS bulk_flightline_id,
                {site_case} AS bulk_site,
                {date_case} AS bulk_acquisition_date
            FROM read_parquet([{files_sql}], union_by_name = TRUE, filename = TRUE)
            """
        )

    if materialize_observations:
        copy_table_atomic(
            con,
            "SELECT * FROM bulk_observations_virtual",
            paths.observations,
            row_group_size=row_group_size,
        )
        con.execute(
            "CREATE VIEW bulk_observations AS SELECT * FROM read_parquet('"
            + quote_path(paths.observations)
            + "')"
        )
    else:
        if paths.observations.exists():
            paths.observations.unlink()
        con.execute("CREATE VIEW bulk_observations AS SELECT * FROM bulk_observations_virtual")


def create_bulk_database(
    paths: BulkAnalysisPaths,
    source_files: Sequence[SourceFileRecord],
    flightlines: Sequence[FlightlineRecord],
    *,
    metadata: dict[str, Any],
    materialize_observations: bool,
    row_group_size: int,
    memory_limit: str | None,
    threads: int | None,
    temp_directory: Path | None,
) -> tuple[duckdb.DuckDBPyConnection, Path]:
    """Create a temporary database ready for modular analysis execution."""

    paths.ensure_directories()
    temporary_database = paths.database.with_suffix(".tmp.duckdb")
    if temporary_database.exists():
        temporary_database.unlink()
    con = duckdb.connect(str(temporary_database))
    configure_duckdb(
        con,
        memory_limit=memory_limit,
        threads=threads,
        temp_directory=temp_directory,
    )
    con.execute(_SOURCE_FILES_DDL)
    con.execute(_FLIGHTLINES_DDL)
    _insert_dataclasses(con, "source_files", source_files)
    _insert_dataclasses(con, "flightlines", flightlines)
    con.execute("CREATE VIEW bulk_sources AS SELECT * FROM source_files")
    con.execute(
        "CREATE TABLE duplicates AS SELECT * FROM flightlines "
        "WHERE duplicate_status = 'duplicate_canonical_id'"
    )
    con.execute(
        "CREATE TABLE rejected_sources AS SELECT * FROM flightlines "
        "WHERE status IN ('rejected', 'duplicate_excluded')"
    )
    con.execute("CREATE TABLE bulk_metadata (key VARCHAR PRIMARY KEY, value_json VARCHAR)")
    if metadata:
        con.executemany(
            "INSERT INTO bulk_metadata VALUES (?, ?)",
            [(key, json.dumps(value, sort_keys=True)) for key, value in metadata.items()],
        )
    accepted_sources = [source for source in source_files if source.status == "accepted"]
    _create_observation_views(
        con,
        accepted_sources,
        paths,
        materialize_observations=materialize_observations,
        row_group_size=row_group_size,
    )
    for table_name, output_path in (
        ("flightlines", paths.flightlines),
        ("source_files", paths.source_files),
        ("duplicates", paths.duplicates),
        ("rejected_sources", paths.rejected_sources),
    ):
        copy_table_atomic(con, f"SELECT * FROM {table_name}", output_path)
    return con, temporary_database


def finalize_bulk_database(
    con: duckdb.DuckDBPyConnection,
    temporary_database: Path,
    database_path: Path,
) -> None:
    """Checkpoint, close, and atomically publish the database."""

    con.execute("CHECKPOINT")
    con.close()
    temporary_database.replace(database_path)


def observation_columns(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [row[0] for row in con.execute("DESCRIBE bulk_observations").fetchall()]


__all__ = [
    "configure_duckdb",
    "copy_table_atomic",
    "create_bulk_database",
    "finalize_bulk_database",
    "observation_columns",
    "quote_identifier",
    "quote_path",
]
