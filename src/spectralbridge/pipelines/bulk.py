"""Independent cross-run aggregation and pooled sensor regression pipeline.

The bulk pipeline consumes completed per-flightline merged Parquet products. It
does not download, correct, convolve, or mutate either NEON or drone products.
All bulk artifacts are written to a dedicated output directory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any, Literal, Sequence

import duckdb
import pyarrow.parquet as pq

from spectralbridge.sensor_pairs import (
    MICASENSE_LANDSAT_PAIRS,
    SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
)


LOGGER = logging.getLogger(__name__)
BULK_SCHEMA_VERSION = 1
BulkInputKind = Literal["full", "polygon", "both"]
_RESERVED_OBSERVATION_COLUMNS = {
    "filename",
    "bulk_source_path",
    "bulk_source_relative_path",
    "bulk_source_kind",
    "bulk_source_id",
}


@dataclass(frozen=True)
class BulkAnalysisPaths:
    """Canonical artifacts produced by one bulk-analysis run."""

    output_dir: Path

    @property
    def observations(self) -> Path:
        return self.output_dir / "bulk_observations.parquet"

    @property
    def source_catalog(self) -> Path:
        return self.output_dir / "bulk_sources.parquet"

    @property
    def coefficients_parquet(self) -> Path:
        return self.output_dir / "synthetic_translation_coefficients.parquet"

    @property
    def coefficients_json(self) -> Path:
        return self.output_dir / "synthetic_translation_coefficients.json"

    @property
    def database(self) -> Path:
        return self.output_dir / "bulk_analysis.duckdb"

    @property
    def manifest(self) -> Path:
        return self.output_dir / "bulk_manifest.json"


@dataclass(frozen=True)
class BulkSource:
    """Inventory record for one discovered merged Parquet candidate."""

    source_id: str
    source_path: str
    relative_path: str
    input_kind: str
    status: str
    reason: str | None
    row_count: int | None
    column_count: int | None
    size_bytes: int
    modified_time_ns: int
    schema_sha256: str | None
    translation_eligible: bool


def _quote_path(path: str | Path) -> str:
    return Path(path).as_posix().replace("'", "''")


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _classify_merged_parquet(path: Path) -> str | None:
    name = path.name
    if name.endswith("_polygons_merged_pixel_extraction.parquet"):
        return "polygon"
    if name.endswith("_merged_pixel_extraction.parquet"):
        return "full"
    return None


def _kind_is_selected(source_kind: str, requested_kind: BulkInputKind) -> bool:
    return requested_kind == "both" or source_kind == requested_kind


def _has_translation_pair(columns: Sequence[str]) -> bool:
    bandmap = _band_map(columns)
    return any(
        bandmap.get(micasense_sensor, set()) & bandmap.get(landsat_sensor, set())
        for micasense_sensor, landsat_sensors in MICASENSE_LANDSAT_PAIRS.items()
        for landsat_sensor in landsat_sensors
    )


def discover_bulk_sources(
    input_path: str | Path,
    *,
    input_kind: BulkInputKind = "full",
    exclude_dir: str | Path | None = None,
) -> list[BulkSource]:
    """Recursively inventory canonical merged Parquet products.

    ``input_path`` may point to one canonical merged Parquet file or to a
    directory tree. Invalid Parquet candidates remain visible in the returned
    inventory with ``status="rejected"``.
    """

    root = Path(input_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Bulk input path does not exist: {root}")
    if input_kind not in {"full", "polygon", "both"}:
        raise ValueError("input_kind must be 'full', 'polygon', or 'both'")

    excluded = Path(exclude_dir).expanduser().resolve() if exclude_dir else None
    if root.is_file():
        candidates = [root]
        relative_root = root.parent
    elif root.is_dir():
        candidates = sorted(root.rglob("*.parquet"))
        relative_root = root
    else:
        raise ValueError(f"Bulk input must be a file or directory: {root}")

    inventory: list[BulkSource] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if excluded is not None and _path_is_within(resolved, excluded):
            continue
        source_kind = _classify_merged_parquet(resolved)
        if source_kind is None or not _kind_is_selected(source_kind, input_kind):
            continue

        stat = resolved.stat()
        relative_path = candidate.relative_to(relative_root).as_posix()
        source_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
        try:
            parquet_file = pq.ParquetFile(resolved)
            schema = parquet_file.schema_arrow
            schema_text = str(schema)
            schema_sha256 = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
            columns = schema.names
            reserved = sorted(_RESERVED_OBSERVATION_COLUMNS & set(columns))
            if reserved:
                raise ValueError(
                    "source uses bulk-reserved column name(s): "
                    + ", ".join(reserved)
                )
            row_count = int(parquet_file.metadata.num_rows)
            translation_eligible = _has_translation_pair(columns)
            status = "accepted"
            reason = None
            column_count = len(columns)
        except Exception as exc:
            schema_sha256 = None
            row_count = None
            translation_eligible = False
            status = "rejected"
            reason = f"{type(exc).__name__}: {exc}"
            column_count = None

        inventory.append(
            BulkSource(
                source_id=source_id,
                source_path=resolved.as_posix(),
                relative_path=relative_path,
                input_kind=source_kind,
                status=status,
                reason=reason,
                row_count=row_count,
                column_count=column_count,
                size_bytes=int(stat.st_size),
                modified_time_ns=int(stat.st_mtime_ns),
                schema_sha256=schema_sha256,
                translation_eligible=translation_eligible,
            )
        )
    return inventory


def _input_signature(
    root: Path,
    output_dir: Path,
    input_kind: BulkInputKind,
    minimum_reflectance: float,
    row_group_size: int,
    sources: Sequence[BulkSource],
) -> dict[str, Any]:
    return {
        "bulk_schema_version": BULK_SCHEMA_VERSION,
        "input_path": root.as_posix(),
        "output_dir": output_dir.as_posix(),
        "input_kind": input_kind,
        "minimum_reflectance": minimum_reflectance,
        "row_group_size": row_group_size,
        "sources": [asdict(source) for source in sources],
    }


def _outputs_are_valid(paths: BulkAnalysisPaths) -> bool:
    required = (
        paths.observations,
        paths.source_catalog,
        paths.coefficients_parquet,
        paths.coefficients_json,
        paths.database,
        paths.manifest,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    try:
        pq.read_schema(paths.observations)
        pq.read_schema(paths.source_catalog)
        pq.read_schema(paths.coefficients_parquet)
        payload = json.loads(paths.coefficients_json.read_text(encoding="utf-8"))
        if payload.get("schema_version") != BULK_SCHEMA_VERSION:
            return False
        with duckdb.connect(str(paths.database), read_only=True) as con:
            con.execute("SELECT COUNT(*) FROM bulk_sources").fetchone()
            con.execute(
                "SELECT COUNT(*) FROM synthetic_translation_coefficients"
            ).fetchone()
            con.execute("SELECT * FROM bulk_observations LIMIT 0").fetchall()
    except Exception:
        return False
    return True


def _configure_duckdb(
    con: duckdb.DuckDBPyConnection,
    *,
    memory_limit: str | None,
    threads: int | None,
    temp_directory: Path | None,
) -> None:
    if memory_limit:
        con.execute("SET memory_limit = ?", [memory_limit])
    if threads is not None:
        if threads < 1:
            raise ValueError("threads must be at least 1")
        con.execute(f"SET threads = {int(threads)}")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        con.execute("SET temp_directory = ?", [temp_directory.as_posix()])


def _materialize_observations(
    con: duckdb.DuckDBPyConnection,
    sources: Sequence[BulkSource],
    output_path: Path,
    *,
    row_group_size: int,
) -> int:
    if row_group_size < 1:
        raise ValueError("row_group_size must be at least 1")

    input_paths = [Path(source.source_path) for source in sources]
    files_sql = ", ".join(f"'{_quote_path(path)}'" for path in input_paths)
    relative_cases = " ".join(
        "WHEN '"
        + _quote_path(source.source_path)
        + "' THEN '"
        + source.relative_path.replace("'", "''")
        + "'"
        for source in sources
    )
    kind_cases = " ".join(
        "WHEN '"
        + _quote_path(source.source_path)
        + "' THEN '"
        + source.input_kind
        + "'"
        for source in sources
    )
    source_id_cases = " ".join(
        "WHEN '"
        + _quote_path(source.source_path)
        + "' THEN '"
        + source.source_id
        + "'"
        for source in sources
    )

    temp_path = output_path.with_suffix(".tmp.parquet")
    if temp_path.exists():
        temp_path.unlink()
    query = f"""
        SELECT
            * EXCLUDE (filename),
            filename AS bulk_source_path,
            CASE filename {relative_cases} ELSE filename END AS bulk_source_relative_path,
            CASE filename {kind_cases} ELSE NULL END AS bulk_source_kind,
            CASE filename {source_id_cases} ELSE NULL END AS bulk_source_id
        FROM read_parquet([{files_sql}], union_by_name = TRUE, filename = TRUE)
    """
    con.execute(
        "COPY ("
        + query
        + ") TO '"
        + _quote_path(temp_path)
        + f"' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {row_group_size})"
    )
    pq.read_schema(temp_path)
    temp_path.replace(output_path)
    row = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{_quote_path(output_path)}')"
    ).fetchone()
    return int(row[0]) if row else 0


def _band_map(columns: Sequence[str]) -> dict[str, set[int]]:
    mapped: dict[str, set[int]] = {}
    for column in columns:
        label, separator, suffix = column.rpartition("_band_")
        if separator and suffix.isdigit():
            mapped.setdefault(label, set()).add(int(suffix))
    return mapped


def _possible_error_columns(label: str, band_index: int) -> tuple[str, ...]:
    suffix = str(band_index)
    return (
        f"{label}_band_{suffix}_error",
        f"{label}_band_{suffix}_err",
        f"{label}_error_band_{suffix}",
        f"{label}_err_band_{suffix}",
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _calculate_pooled_regressions(
    con: duckdb.DuckDBPyConnection,
    observations_path: Path,
    *,
    minimum_reflectance: float,
) -> list[dict[str, Any]]:
    columns = list(pq.read_schema(observations_path).names)
    column_set = set(columns)
    bandmap = _band_map(columns)
    records: list[dict[str, Any]] = []

    for micasense_sensor, landsat_sensors in MICASENSE_LANDSAT_PAIRS.items():
        for landsat_sensor in landsat_sensors:
            common_bands = sorted(
                bandmap.get(micasense_sensor, set())
                & bandmap.get(landsat_sensor, set())
            )
            for band_index in common_bands:
                x_column = f"{micasense_sensor}_band_{band_index}"
                y_column = f"{landsat_sensor}_band_{band_index}"
                error_columns = [
                    column
                    for label in (micasense_sensor, landsat_sensor)
                    for column in _possible_error_columns(label, band_index)
                    if column in column_set
                ]
                error_filter = "".join(
                    " AND COALESCE(TRY_CAST("
                    + _quote_identifier(column)
                    + " AS DOUBLE), 0) = 0"
                    for column in error_columns
                )
                query = f"""
                    WITH candidate AS (
                        SELECT
                            TRY_CAST({_quote_identifier(x_column)} AS DOUBLE) AS x,
                            TRY_CAST({_quote_identifier(y_column)} AS DOUBLE) AS y,
                            bulk_source_id
                        FROM read_parquet('{_quote_path(observations_path)}')
                        WHERE TRUE {error_filter}
                    ), valid AS (
                        SELECT x, y, bulk_source_id
                        FROM candidate
                        WHERE x IS NOT NULL AND y IS NOT NULL
                          AND isfinite(x) AND isfinite(y)
                          AND x >= ? AND y >= ?
                    )
                    SELECT
                        COUNT(*) AS sample_count,
                        COUNT(DISTINCT bulk_source_id) AS source_count,
                        regr_slope(y, x) AS slope,
                        regr_intercept(y, x) AS intercept,
                        corr(x, y) AS correlation,
                        MIN(x) AS x_min,
                        MAX(x) AS x_max,
                        AVG(x) AS x_mean,
                        MIN(y) AS y_min,
                        MAX(y) AS y_max,
                        AVG(y) AS y_mean
                    FROM valid
                """
                row = con.execute(
                    query, [minimum_reflectance, minimum_reflectance]
                ).fetchone()
                if row is None:
                    continue
                (
                    sample_count,
                    source_count,
                    slope,
                    intercept,
                    correlation,
                    x_min,
                    x_max,
                    x_mean,
                    y_min,
                    y_max,
                    y_mean,
                ) = row
                slope_value = _optional_float(slope)
                intercept_value = _optional_float(intercept)
                status = (
                    "ok"
                    if slope_value is not None and intercept_value is not None
                    else "insufficient_data"
                )
                bias = rmse = mae = None
                if status == "ok":
                    residual_query = f"""
                        WITH candidate AS (
                            SELECT
                                TRY_CAST({_quote_identifier(x_column)} AS DOUBLE) AS x,
                                TRY_CAST({_quote_identifier(y_column)} AS DOUBLE) AS y
                            FROM read_parquet('{_quote_path(observations_path)}')
                            WHERE TRUE {error_filter}
                        ), valid AS (
                            SELECT x, y
                            FROM candidate
                            WHERE x IS NOT NULL AND y IS NOT NULL
                              AND isfinite(x) AND isfinite(y)
                              AND x >= ? AND y >= ?
                        )
                        SELECT
                            AVG(y - (? * x + ?)) AS bias,
                            SQRT(AVG(POWER(y - (? * x + ?), 2))) AS rmse,
                            AVG(ABS(y - (? * x + ?))) AS mae
                        FROM valid
                    """
                    residual = con.execute(
                        residual_query,
                        [
                            minimum_reflectance,
                            minimum_reflectance,
                            slope_value,
                            intercept_value,
                            slope_value,
                            intercept_value,
                            slope_value,
                            intercept_value,
                        ],
                    ).fetchone()
                    if residual:
                        bias, rmse, mae = residual

                correlation_value = _optional_float(correlation)
                records.append(
                    {
                        "micasense_sensor": micasense_sensor,
                        "landsat_sensor": landsat_sensor,
                        "band_index": band_index,
                        "x_column": x_column,
                        "y_column": y_column,
                        "equation": "landsat = slope * micasense + intercept",
                        "status": status,
                        "slope": slope_value,
                        "intercept": intercept_value,
                        "correlation": correlation_value,
                        "r2": (
                            correlation_value * correlation_value
                            if correlation_value is not None
                            else None
                        ),
                        "bias": _optional_float(bias),
                        "rmse": _optional_float(rmse),
                        "mae": _optional_float(mae),
                        "sample_count": int(sample_count),
                        "source_count": int(source_count),
                        "x_min": _optional_float(x_min),
                        "x_max": _optional_float(x_max),
                        "x_mean": _optional_float(x_mean),
                        "y_min": _optional_float(y_min),
                        "y_max": _optional_float(y_max),
                        "y_mean": _optional_float(y_mean),
                    }
                )
    return records


def _create_catalog_database(
    paths: BulkAnalysisPaths,
    sources: Sequence[BulkSource],
    regressions: Sequence[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    temporary_database = paths.database.with_suffix(".tmp.duckdb")
    if temporary_database.exists():
        temporary_database.unlink()

    con = duckdb.connect(str(temporary_database))
    try:
        con.execute(
            """
            CREATE TABLE bulk_sources (
                source_id VARCHAR,
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
                translation_eligible BOOLEAN
            )
            """
        )
        con.executemany(
            "INSERT INTO bulk_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [tuple(asdict(source).values()) for source in sources],
        )
        con.execute(
            """
            CREATE TABLE synthetic_translation_coefficients (
                micasense_sensor VARCHAR,
                landsat_sensor VARCHAR,
                band_index INTEGER,
                x_column VARCHAR,
                y_column VARCHAR,
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
                x_min DOUBLE,
                x_max DOUBLE,
                x_mean DOUBLE,
                y_min DOUBLE,
                y_max DOUBLE,
                y_mean DOUBLE
            )
            """
        )
        regression_columns = (
            "micasense_sensor",
            "landsat_sensor",
            "band_index",
            "x_column",
            "y_column",
            "equation",
            "status",
            "slope",
            "intercept",
            "correlation",
            "r2",
            "bias",
            "rmse",
            "mae",
            "sample_count",
            "source_count",
            "x_min",
            "x_max",
            "x_mean",
            "y_min",
            "y_max",
            "y_mean",
        )
        if regressions:
            placeholders = ", ".join("?" for _ in regression_columns)
            con.executemany(
                "INSERT INTO synthetic_translation_coefficients VALUES "
                f"({placeholders})",
                [
                    tuple(record[column] for column in regression_columns)
                    for record in regressions
                ],
            )
        con.execute(
            "CREATE TABLE bulk_metadata (key VARCHAR PRIMARY KEY, value_json VARCHAR)"
        )
        con.executemany(
            "INSERT INTO bulk_metadata VALUES (?, ?)",
            [
                (key, json.dumps(value, sort_keys=True))
                for key, value in metadata.items()
            ],
        )
        con.execute(
            "CREATE VIEW bulk_observations AS SELECT * FROM read_parquet('"
            + _quote_path(paths.observations)
            + "')"
        )

        for table_name, output_path in (
            ("bulk_sources", paths.source_catalog),
            ("synthetic_translation_coefficients", paths.coefficients_parquet),
        ):
            temporary_output = output_path.with_suffix(".tmp.parquet")
            if temporary_output.exists():
                temporary_output.unlink()
            con.execute(
                f"COPY {table_name} TO '{_quote_path(temporary_output)}' "
                "(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            pq.read_schema(temporary_output)
            temporary_output.replace(output_path)
    finally:
        con.close()
    temporary_database.replace(paths.database)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _result(
    paths: BulkAnalysisPaths,
    *,
    status: str,
    source_count: int,
    rejected_source_count: int,
    row_count: int,
    regression_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "source_count": source_count,
        "rejected_source_count": rejected_source_count,
        "row_count": row_count,
        "regression_count": regression_count,
        "observations": str(paths.observations),
        "source_catalog": str(paths.source_catalog),
        "coefficients_parquet": str(paths.coefficients_parquet),
        "coefficients_json": str(paths.coefficients_json),
        "database": str(paths.database),
        "manifest": str(paths.manifest),
    }


def run_bulk_pipeline(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    input_kind: BulkInputKind = "full",
    minimum_reflectance: float = 0.0,
    require_translation_pairs: bool = True,
    row_group_size: int = 50_000,
    memory_limit: str | None = None,
    threads: int | None = None,
    temp_directory: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Build a cross-run Parquet/DuckDB collection and pooled regressions.

    Args:
        input_path: One canonical merged Parquet file or a directory tree to
            search recursively.
        output_dir: Dedicated bulk-artifact directory. Defaults to
            ``<input directory>/spectralbridge_bulk``.
        input_kind: Select full-pixel masters, polygon masters, or both. The
            default is ``"full"`` to avoid counting a polygon subset again
            when both products exist for one flightline.
        minimum_reflectance: Lower inclusive bound used for both variables in
            pooled regressions.
        require_translation_pairs: Raise when no paired synthetic MicaSense and
            Landsat columns are available.
        row_group_size: Row-group size for the portable super-Parquet.
        memory_limit: Optional DuckDB memory-limit literal such as ``"8GB"``.
        threads: Optional DuckDB worker-thread count.
        temp_directory: Optional directory for DuckDB spill files.
        force: Rebuild even when the source inventory and outputs are current.

    Returns:
        A dictionary of output paths, counts, and ``status`` (``"created"`` or
        ``"reused"``).
    """

    root = Path(input_path).expanduser().resolve()
    minimum_reflectance = float(minimum_reflectance)
    if not math.isfinite(minimum_reflectance):
        raise ValueError("minimum_reflectance must be finite")
    if row_group_size < 1:
        raise ValueError("row_group_size must be at least 1")
    default_parent = root if root.is_dir() else root.parent
    resolved_output = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else (default_parent / "spectralbridge_bulk").resolve()
    )
    paths = BulkAnalysisPaths(resolved_output)
    inventory = discover_bulk_sources(
        root,
        input_kind=input_kind,
        exclude_dir=resolved_output,
    )
    accepted = [source for source in inventory if source.status == "accepted"]
    rejected = [source for source in inventory if source.status == "rejected"]
    if not accepted:
        raise FileNotFoundError(
            "No readable canonical merged Parquet products were found under "
            f"{root} for input_kind={input_kind!r}."
        )
    if require_translation_pairs and not any(
        source.translation_eligible for source in accepted
    ):
        raise ValueError(
            "The discovered merged Parquet products do not contain paired "
            "synthetic MicaSense and Landsat columns required for translation "
            "regressions."
        )

    signature = _input_signature(
        root,
        resolved_output,
        input_kind,
        minimum_reflectance,
        row_group_size,
        inventory,
    )
    if not force and paths.manifest.is_file():
        try:
            previous = json.loads(paths.manifest.read_text(encoding="utf-8"))
        except Exception:
            previous = {}
        if previous.get("input_signature") == signature and _outputs_are_valid(paths):
            return _result(
                paths,
                status="reused",
                source_count=int(previous["accepted_source_count"]),
                rejected_source_count=int(previous["rejected_source_count"]),
                row_count=int(previous["row_count"]),
                regression_count=int(previous["regression_count"]),
            )

    resolved_output.mkdir(parents=True, exist_ok=True)
    temporary_dir = (
        Path(temp_directory).expanduser().resolve()
        if temp_directory is not None
        else None
    )
    con = duckdb.connect()
    try:
        _configure_duckdb(
            con,
            memory_limit=memory_limit,
            threads=threads,
            temp_directory=temporary_dir,
        )
        row_count = _materialize_observations(
            con,
            accepted,
            paths.observations,
            row_group_size=row_group_size,
        )
        regressions = _calculate_pooled_regressions(
            con,
            paths.observations,
            minimum_reflectance=minimum_reflectance,
        )
    finally:
        con.close()

    if require_translation_pairs and not regressions:
        raise ValueError(
            "No common MicaSense/Landsat band pairs were available after the "
            "bulk merge."
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    coefficient_payload = {
        "schema_version": BULK_SCHEMA_VERSION,
        "diagnostic": "bulk_synthetic_sensor_linear_regression",
        "equation": "landsat = slope * micasense + intercept",
        "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
        "source_value_policy": (
            "Uses persisted source values as-is, including any brightness "
            "adjustment applied by an upstream run."
        ),
        "weighting": (
            "pooled valid rows; larger source tables contribute more observations"
        ),
        "minimum_reflectance": minimum_reflectance,
        "input_path": root.as_posix(),
        "accepted_source_count": len(accepted),
        "row_count": row_count,
        "generated_at_utc": generated_at,
        "regressions": regressions,
    }
    metadata = {
        "schema_version": BULK_SCHEMA_VERSION,
        "input_path": root.as_posix(),
        "input_kind": input_kind,
        "minimum_reflectance": minimum_reflectance,
        "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
        "generated_at_utc": generated_at,
    }
    _create_catalog_database(paths, inventory, regressions, metadata)
    _write_json_atomic(paths.coefficients_json, coefficient_payload)

    manifest_payload = {
        "schema_version": BULK_SCHEMA_VERSION,
        "pipeline": "spectralbridge_bulk_analysis",
        "generated_at_utc": generated_at,
        "input_signature": signature,
        "accepted_source_count": len(accepted),
        "rejected_source_count": len(rejected),
        "row_count": row_count,
        "regression_count": len(regressions),
        "outputs": {
            "observations": paths.observations.name,
            "source_catalog": paths.source_catalog.name,
            "coefficients_parquet": paths.coefficients_parquet.name,
            "coefficients_json": paths.coefficients_json.name,
            "database": paths.database.name,
        },
    }
    _write_json_atomic(paths.manifest, manifest_payload)
    LOGGER.info(
        "Bulk analysis created from %d source(s), %d row(s), and %d regression(s)",
        len(accepted),
        row_count,
        len(regressions),
    )
    return _result(
        paths,
        status="created",
        source_count=len(accepted),
        rejected_source_count=len(rejected),
        row_count=row_count,
        regression_count=len(regressions),
    )


__all__ = [
    "BULK_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkSource",
    "discover_bulk_sources",
    "run_bulk_pipeline",
]
