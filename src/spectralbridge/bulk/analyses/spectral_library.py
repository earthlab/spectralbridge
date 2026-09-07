"""Bounded summaries and low-alpha reports for an existing spectral library."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import math
from pathlib import Path
import re
from typing import Any, Iterator, Sequence

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ..dataset import quote_identifier
from ..models import BulkAnalysisPaths
from ..provenance import signature_sha256, write_json_atomic


SPECTRAL_LIBRARY_SCHEMA_VERSION = 2
DEFAULT_QUANTILES = (0.025, 0.10, 0.25, 0.50, 0.75, 0.90, 0.975)
DEFAULT_PLOT_Y_QUANTILES = (0.005, 0.995)
DEFAULT_NODATA_VALUES = (-9999.0,)
_SPECTRAL_COLUMN = re.compile(
    r"^(?P<stage>.+?)_b(?P<band>\d+)_wl(?P<wavelength>\d+(?:\.\d+)?)nm$",
    re.IGNORECASE,
)
_SPECIES_CANDIDATES = (
    "species",
    "scientific_name",
    "scientificname",
    "taxon_name",
    "taxon",
)
_FIELD_CANDIDATES = {
    "polygon": ("polygon_id", "polygonid"),
    "flightline": ("flightline_id", "flightline", "bulk_flightline_id"),
    "site": ("site", "site_code", "bulk_site"),
    "acquisition_date": ("acquisition_date", "date", "bulk_acquisition_date"),
    "pixel": ("pixel_id", "pixelid"),
}
_NODATA_METADATA_KEYS = {
    "nodata",
    "no_data",
    "no data",
    "_fillvalue",
    "fill_value",
    "data ignore value",
}


@dataclass(frozen=True)
class SpectralBand:
    column: str
    stage: str
    band_index: int
    wavelength_nm: float


@dataclass(frozen=True)
class SpectralLibrarySchema:
    source: Path
    source_signature_sha256: str
    row_count: int
    species_field: str
    polygon_field: str | None
    flightline_field: str | None
    site_field: str | None
    acquisition_date_field: str | None
    pixel_field: str | None
    spectral_stage: str
    bands: tuple[SpectralBand, ...]
    available_spectral_stages: tuple[str, ...]
    detected_nodata_values: tuple[float, ...]

    @property
    def wavelengths_nm(self) -> tuple[float, ...]:
        return tuple(band.wavelength_nm for band in self.bands)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source"] = self.source.as_posix()
        payload["wavelengths_nm"] = list(self.wavelengths_nm)
        payload["detected_nodata_values"] = list(self.detected_nodata_values)
        payload["band_count"] = len(self.bands)
        return payload


@dataclass(frozen=True)
class SpectralLibraryPlotConfig:
    """Explicit controls for potentially expensive spectral-library reports."""

    species_field: str | None = None
    spectral_stage: str | None = None
    species_sort: str = "count_desc"
    panels_per_page: int = 4
    trace_batch_size: int = 2_000
    summary_band_batch_size: int = 32
    max_traces_per_group: int | None = None
    sampling_seed: int = 0
    raster_dpi: int = 150
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES
    plot_y_quantiles: tuple[float, float] = DEFAULT_PLOT_Y_QUANTILES
    species_y_scale: str = "global_robust"
    spectral_plot_minimum_reflectance: float | None = None
    nodata_values: tuple[float, ...] = DEFAULT_NODATA_VALUES
    nodata_tolerance: float = 0.01
    max_extreme_spectra_per_species: int = 100

    def validate(self) -> None:
        if self.species_sort not in {"alphabetical", "count_desc"}:
            raise ValueError("species_sort must be 'alphabetical' or 'count_desc'")
        if self.panels_per_page < 1 or self.panels_per_page > 8:
            raise ValueError("panels_per_page must be between 1 and 8")
        if self.trace_batch_size < 1:
            raise ValueError("trace_batch_size must be at least 1")
        if self.summary_band_batch_size < 1:
            raise ValueError("summary_band_batch_size must be at least 1")
        if self.max_traces_per_group is not None and self.max_traces_per_group < 1:
            raise ValueError("max_traces_per_group must be at least 1 when set")
        if self.raster_dpi < 72:
            raise ValueError("raster_dpi must be at least 72")
        if not self.quantiles or tuple(sorted(self.quantiles)) != self.quantiles:
            raise ValueError("quantiles must be a non-empty sorted tuple")
        if any(not 0.0 < value < 1.0 for value in self.quantiles):
            raise ValueError("quantiles must be strictly between zero and one")
        if 0.5 not in self.quantiles:
            raise ValueError("quantiles must include 0.5 for the median")
        low, high = self.plot_y_quantiles
        if not 0.0 < low < high < 1.0:
            raise ValueError(
                "plot_y_quantiles must contain increasing probabilities between zero and one"
            )
        if self.species_y_scale not in {
            "global_robust",
            "global_full",
            "per_group_robust",
        }:
            raise ValueError(
                "species_y_scale must be 'global_robust', 'global_full', or "
                "'per_group_robust'"
            )
        if (
            self.spectral_plot_minimum_reflectance is not None
            and not math.isfinite(self.spectral_plot_minimum_reflectance)
        ):
            raise ValueError("spectral_plot_minimum_reflectance must be finite or None")
        if any(not math.isfinite(value) for value in self.nodata_values):
            raise ValueError("nodata_values must contain only finite values")
        if not math.isfinite(self.nodata_tolerance) or self.nodata_tolerance < 0.0:
            raise ValueError("nodata_tolerance must be finite and non-negative")
        if self.max_extreme_spectra_per_species < 1:
            raise ValueError("max_extreme_spectra_per_species must be at least 1")


@dataclass(frozen=True)
class SpectralLibraryPaths:
    analysis_dir: Path
    figures_dir: Path

    @classmethod
    def from_bulk_paths(cls, paths: BulkAnalysisPaths) -> SpectralLibraryPaths:
        return cls(
            analysis_dir=paths.analyses_dir / "spectral_library",
            figures_dir=paths.figures_dir / "spectral_library",
        )

    @property
    def species_summary(self) -> Path:
        return self.analysis_dir / "species_summary.parquet"

    @property
    def species_band_summary(self) -> Path:
        return self.analysis_dir / "species_band_summary.parquet"

    @property
    def species_quantiles(self) -> Path:
        return self.analysis_dir / "species_quantiles.parquet"

    @property
    def species_medians(self) -> Path:
        return self.analysis_dir / "species_median_spectra.parquet"

    @property
    def group_counts(self) -> Path:
        return self.analysis_dir / "group_counts.parquet"

    @property
    def species_plot_ranges(self) -> Path:
        return self.analysis_dir / "species_plot_ranges.parquet"

    @property
    def extreme_spectra(self) -> Path:
        return self.analysis_dir / "extreme_spectra.parquet"

    @property
    def metadata(self) -> Path:
        return self.analysis_dir / "spectral_library_summary.json"

    @property
    def species_variability(self) -> Path:
        return self.figures_dir / "spectral_library_species_variability.pdf"

    @property
    def species_variability_full_range(self) -> Path:
        return self.figures_dir / "spectral_library_species_variability_full_range.pdf"

    @property
    def species_quantile_report(self) -> Path:
        return self.figures_dir / "spectral_library_species_quantiles.pdf"

    @property
    def species_median_report(self) -> Path:
        return self.figures_dir / "spectral_library_species_medians.pdf"

    @property
    def observation_counts(self) -> Path:
        return self.figures_dir / "spectral_library_observation_counts.pdf"

    @property
    def hierarchy_report(self) -> Path:
        return self.figures_dir / "spectral_library_hierarchical_variability.pdf"

    @property
    def site_variability(self) -> Path:
        return self.figures_dir / "spectral_library_site_variability.pdf"

    @property
    def flightline_variability(self) -> Path:
        return self.figures_dir / "spectral_library_flightline_variability.pdf"


_GROUP_COUNT_SCHEMA = pa.schema(
    [
        ("grouping_field", pa.string()),
        ("group_value", pa.string()),
        ("observation_count", pa.int64()),
        ("valid_spectrum_count", pa.int64()),
        ("species_count", pa.int64()),
        ("polygon_count", pa.int64()),
        ("flightline_count", pa.int64()),
        ("site_count", pa.int64()),
    ]
)
_BAND_SUMMARY_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("spectral_stage", pa.string()),
        ("band_index", pa.int32()),
        ("wavelength_nm", pa.float64()),
        ("valid_spectrum_count", pa.int64()),
        ("reflectance_min", pa.float64()),
        ("reflectance_max", pa.float64()),
        ("reflectance_mean", pa.float64()),
        ("reflectance_median", pa.float64()),
    ]
)
_QUANTILE_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("spectral_stage", pa.string()),
        ("band_index", pa.int32()),
        ("wavelength_nm", pa.float64()),
        ("quantile", pa.float64()),
        ("reflectance", pa.float64()),
        ("method", pa.string()),
    ]
)
_MEDIAN_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("spectral_stage", pa.string()),
        ("band_index", pa.int32()),
        ("wavelength_nm", pa.float64()),
        ("median_reflectance", pa.float64()),
        ("method", pa.string()),
    ]
)
_SPECIES_SUMMARY_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("observation_count", pa.int64()),
        ("valid_spectrum_count", pa.int64()),
        ("polygon_count", pa.int64()),
        ("flightline_count", pa.int64()),
        ("site_count", pa.int64()),
        ("spectral_stage", pa.string()),
        ("band_count", pa.int32()),
        ("wavelength_min_nm", pa.float64()),
        ("wavelength_max_nm", pa.float64()),
        ("reflectance_min", pa.float64()),
        ("reflectance_max", pa.float64()),
    ]
)
_PLOT_RANGE_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("valid_spectrum_count", pa.int64()),
        ("full_minimum", pa.float64()),
        ("full_maximum", pa.float64()),
        ("global_robust_lower", pa.float64()),
        ("global_robust_upper", pa.float64()),
        ("species_robust_lower", pa.float64()),
        ("species_robust_upper", pa.float64()),
        ("global_values_below", pa.int64()),
        ("global_values_above", pa.int64()),
        ("global_spectra_outside", pa.int64()),
        ("species_values_below", pa.int64()),
        ("species_values_above", pa.int64()),
        ("species_spectra_outside", pa.int64()),
    ]
)
_EXTREME_SPECTRUM_SCHEMA = pa.schema(
    [
        ("species", pa.string()),
        ("polygon_id", pa.string()),
        ("flightline_id", pa.string()),
        ("site", pa.string()),
        ("pixel_id", pa.string()),
        ("spectrum_minimum", pa.float64()),
        ("spectrum_maximum", pa.float64()),
        ("wavelengths_below_robust_range", pa.int32()),
        ("wavelengths_above_robust_range", pa.int32()),
        ("wavelengths_outside_robust_range", pa.int32()),
        ("rank_within_species", pa.int32()),
        ("range_policy", pa.string()),
    ]
)


def _field(columns: Sequence[str], explicit: str | None, candidates: Sequence[str]) -> str | None:
    by_lower = {name.lower(): name for name in columns}
    if explicit is not None:
        if explicit not in columns:
            raise ValueError(f"Requested spectral-library field is absent: {explicit}")
        return explicit
    for candidate in candidates:
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]
    return None


def _metadata_nodata_values(parquet: pq.ParquetFile) -> tuple[float, ...]:
    values: set[float] = set()
    metadata_sources = [parquet.schema_arrow.metadata, parquet.metadata.metadata]
    metadata_sources.extend(field.metadata for field in parquet.schema_arrow)
    for metadata in metadata_sources:
        if not metadata:
            continue
        for raw_key, raw_value in metadata.items():
            key = raw_key.decode("utf-8", errors="ignore").strip().lower()
            if key not in _NODATA_METADATA_KEYS:
                continue
            value = raw_value.decode("utf-8", errors="ignore")
            for match in re.findall(
                r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?",
                value,
            ):
                parsed = float(match)
                if math.isfinite(parsed):
                    values.add(parsed)
    return tuple(sorted(values))


def inspect_spectral_library(
    path: str | Path,
    *,
    species_field: str | None = None,
    spectral_stage: str | None = None,
) -> SpectralLibrarySchema:
    """Inspect a merged polygon Parquet and select one coherent spectral stage."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Spectral library Parquet does not exist: {source}")
    parquet = pq.ParquetFile(source)
    arrow_schema = parquet.schema_arrow
    columns = arrow_schema.names
    resolved_species = _field(columns, species_field, _SPECIES_CANDIDATES)
    if resolved_species is None:
        raise ValueError(
            "Spectral library has no recognized species field; pass "
            "SpectralLibraryPlotConfig(species_field=...). Available columns: "
            + ", ".join(columns)
        )
    stage_bands: dict[str, list[SpectralBand]] = {}
    for field_value in arrow_schema:
        match = _SPECTRAL_COLUMN.fullmatch(field_value.name)
        if match is None:
            continue
        if not (
            pa.types.is_integer(field_value.type)
            or pa.types.is_floating(field_value.type)
            or pa.types.is_decimal(field_value.type)
        ):
            raise ValueError(
                f"Spectral column must be numeric: {field_value.name} ({field_value.type})"
            )
        stage = match.group("stage")
        stage_bands.setdefault(stage, []).append(
            SpectralBand(
                column=field_value.name,
                stage=stage,
                band_index=int(match.group("band")),
                wavelength_nm=float(match.group("wavelength")),
            )
        )
    if not stage_bands:
        raise ValueError(
            "No wavelength-bearing wide spectral columns were found. Expected "
            "names like corr_b001_wl0450nm. Arbitrary band numbers are not plotted."
        )
    stages = tuple(sorted(stage_bands, key=str.lower))
    if spectral_stage is not None:
        matches = [stage for stage in stages if stage.lower() == spectral_stage.lower()]
        if not matches:
            raise ValueError(
                f"Requested spectral stage {spectral_stage!r} is absent; available: {stages}"
            )
        selected_stage = matches[0]
    else:
        preferred = [
            stage
            for preferred_name in ("corr", "corrected", "brdfandtopo_corrected")
            for stage in stages
            if stage.lower() == preferred_name
        ]
        if preferred:
            selected_stage = preferred[0]
        elif len(stages) == 1:
            selected_stage = stages[0]
        else:
            raise ValueError(
                "The spectral library contains multiple spectral stages; pass "
                f"SpectralLibraryPlotConfig(spectral_stage=...). Available: {stages}"
            )
    bands = tuple(
        sorted(
            stage_bands[selected_stage],
            key=lambda item: (item.wavelength_nm, item.band_index, item.column),
        )
    )
    if len({band.band_index for band in bands}) != len(bands):
        raise ValueError(f"Duplicate band indices in spectral stage {selected_stage!r}")
    if len({band.wavelength_nm for band in bands}) != len(bands):
        raise ValueError(f"Duplicate wavelengths in spectral stage {selected_stage!r}")
    stat = source.stat()
    signature = signature_sha256(
        {
            "path": source.as_posix(),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "row_count": parquet.metadata.num_rows,
            "schema": [(field_value.name, str(field_value.type)) for field_value in arrow_schema],
        }
    )
    fields = {
        key: _field(columns, None, candidates)
        for key, candidates in _FIELD_CANDIDATES.items()
    }
    return SpectralLibrarySchema(
        source=source,
        source_signature_sha256=signature,
        row_count=int(parquet.metadata.num_rows),
        species_field=resolved_species,
        polygon_field=fields["polygon"],
        flightline_field=fields["flightline"],
        site_field=fields["site"],
        acquisition_date_field=fields["acquisition_date"],
        pixel_field=fields["pixel"],
        spectral_stage=selected_stage,
        bands=bands,
        available_spectral_stages=stages,
        detected_nodata_values=_metadata_nodata_values(parquet),
    )


def trace_alpha(trace_count: int) -> float:
    """Deterministic low-alpha rule for qualitative trace-density ensembles."""

    if trace_count < 1:
        return 0.03
    return min(0.03, max(0.003, 0.2 / math.sqrt(trace_count)))


def _valid_predicate(
    schema: SpectralLibrarySchema,
    config: SpectralLibraryPlotConfig,
) -> str:
    checks = []
    nodata_values = tuple(
        sorted(set(config.nodata_values).union(schema.detected_nodata_values))
    )
    for band in schema.bands:
        column = quote_identifier(band.column)
        value = f"TRY_CAST({column} AS DOUBLE)"
        band_checks = [f"{column} IS NOT NULL", f"isfinite({value})"]
        band_checks.extend(
            f"ABS({value} - {repr(float(nodata))}) > {repr(config.nodata_tolerance)}"
            for nodata in nodata_values
        )
        if config.spectral_plot_minimum_reflectance is not None:
            band_checks.append(
                f"{value} >= {repr(float(config.spectral_plot_minimum_reflectance))}"
            )
        checks.append("(" + " AND ".join(band_checks) + ")")
    return " AND ".join(checks)


def _visualization_validity_policy(
    schema: SpectralLibrarySchema,
    config: SpectralLibraryPlotConfig,
) -> dict[str, Any]:
    nodata_values = tuple(
        sorted(set(config.nodata_values).union(schema.detected_nodata_values))
    )
    return {
        "complete_spectrum_required": True,
        "finite_values_required": True,
        "null_values_excluded": True,
        "nodata_values_excluded": list(nodata_values),
        "schema_detected_nodata_values": list(schema.detected_nodata_values),
        "nodata_tolerance": config.nodata_tolerance,
        "minimum_reflectance": config.spectral_plot_minimum_reflectance,
        "finite_negative_reflectance_allowed": (
            config.spectral_plot_minimum_reflectance is None
            or config.spectral_plot_minimum_reflectance < 0.0
        ),
        "separate_from_translation_regression_validity": True,
    }


def _distinct(field: str | None, valid_name: str = "is_valid") -> str:
    if field is None:
        return "0::BIGINT"
    return (
        "COUNT(DISTINCT CASE WHEN "
        + valid_name
        + " THEN CAST("
        + quote_identifier(field)
        + " AS VARCHAR) END)::BIGINT"
    )


def _group_count_rows(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    grouping_field: str,
    config: SpectralLibraryPlotConfig,
) -> list[dict[str, Any]]:
    field_sql = quote_identifier(grouping_field)
    projected_fields = []
    for field in (
        grouping_field,
        schema.species_field,
        schema.polygon_field,
        schema.flightline_field,
        schema.site_field,
    ):
        if field is not None and field not in projected_fields:
            projected_fields.append(field)
    projection = ", ".join(quote_identifier(field) for field in projected_fields)
    query = f"""
        WITH base AS (
            SELECT {projection}, ({_valid_predicate(schema, config)}) AS is_valid
            FROM read_parquet(?)
            WHERE {field_sql} IS NOT NULL
              AND TRIM(CAST({field_sql} AS VARCHAR)) <> ''
        )
        SELECT
            CAST({field_sql} AS VARCHAR) AS group_value,
            COUNT(*)::BIGINT AS observation_count,
            COUNT(*) FILTER (WHERE is_valid)::BIGINT AS valid_spectrum_count,
            {_distinct(schema.species_field)} AS species_count,
            {_distinct(schema.polygon_field)} AS polygon_count,
            {_distinct(schema.flightline_field)} AS flightline_count,
            {_distinct(schema.site_field)} AS site_count
        FROM base
        GROUP BY CAST({field_sql} AS VARCHAR)
        ORDER BY group_value
    """
    rows = con.execute(query, [schema.source.as_posix()]).to_arrow_table().to_pylist()
    for row in rows:
        row["grouping_field"] = grouping_field
        if grouping_field == schema.species_field:
            row["species_count"] = 1 if row["valid_spectrum_count"] else 0
    return rows


def _write_table_atomic(path: Path, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), temporary, compression="zstd")
    pq.read_schema(temporary)
    temporary.replace(path)


def _write_group_counts(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    config: SpectralLibraryPlotConfig,
) -> list[dict[str, Any]]:
    fields = [schema.species_field]
    fields.extend(
        field
        for field in (schema.site_field, schema.flightline_field, schema.polygon_field)
        if field is not None and field not in fields
    )
    rows = [
        row
        for field in fields
        for row in _group_count_rows(con, schema, field, config)
    ]
    rows.sort(key=lambda row: (row["grouping_field"], row["group_value"]))
    _write_table_atomic(paths.group_counts, rows, _GROUP_COUNT_SCHEMA)
    return rows


def _open_writers(paths: SpectralLibraryPaths) -> dict[str, tuple[pq.ParquetWriter, Path, Path]]:
    definitions = {
        "band": (paths.species_band_summary, _BAND_SUMMARY_SCHEMA),
        "quantile": (paths.species_quantiles, _QUANTILE_SCHEMA),
        "median": (paths.species_medians, _MEDIAN_SCHEMA),
    }
    result = {}
    for key, (final, schema) in definitions.items():
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = final.with_suffix(".tmp.parquet")
        if temporary.exists():
            temporary.unlink()
        result[key] = (pq.ParquetWriter(temporary, schema, compression="zstd"), temporary, final)
    return result


def _write_species_spectral_summaries(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    *,
    band_batch_size: int,
    quantiles: tuple[float, ...],
    config: SpectralLibraryPlotConfig,
) -> dict[str, tuple[float, float]]:
    writers = _open_writers(paths)
    bounds: dict[str, tuple[float, float]] = {}
    species_sql = quote_identifier(schema.species_field)
    quantile_sql = "[" + ",".join(repr(float(value)) for value in quantiles) + "]"
    try:
        for start in range(0, len(schema.bands), band_batch_size):
            bands = schema.bands[start : start + band_batch_size]
            expressions = []
            for index, band in enumerate(bands):
                column = f"TRY_CAST({quote_identifier(band.column)} AS DOUBLE)"
                expressions.extend(
                    (
                        f"MIN({column}) AS min_{index}",
                        f"MAX({column}) AS max_{index}",
                        f"AVG({column}) AS mean_{index}",
                        f"approx_quantile({column}, {quantile_sql}) AS quantiles_{index}",
                    )
                )
            query = f"""
                SELECT CAST({species_sql} AS VARCHAR) AS species,
                       COUNT(*)::BIGINT AS valid_spectrum_count,
                       {', '.join(expressions)}
                FROM read_parquet(?)
                WHERE {species_sql} IS NOT NULL
                  AND TRIM(CAST({species_sql} AS VARCHAR)) <> ''
                  AND {_valid_predicate(schema, config)}
                GROUP BY CAST({species_sql} AS VARCHAR)
                ORDER BY species
            """
            records = con.execute(query, [schema.source.as_posix()]).to_arrow_table().to_pylist()
            band_rows: list[dict[str, Any]] = []
            quantile_rows: list[dict[str, Any]] = []
            median_rows: list[dict[str, Any]] = []
            for record in records:
                species = str(record["species"])
                for index, band in enumerate(bands):
                    minimum = float(record[f"min_{index}"])
                    maximum = float(record[f"max_{index}"])
                    old_minimum, old_maximum = bounds.get(species, (math.inf, -math.inf))
                    bounds[species] = (min(old_minimum, minimum), max(old_maximum, maximum))
                    values = [float(value) for value in record[f"quantiles_{index}"]]
                    median = values[quantiles.index(0.5)]
                    band_rows.append(
                        {
                            "species": species,
                            "spectral_stage": schema.spectral_stage,
                            "band_index": band.band_index,
                            "wavelength_nm": band.wavelength_nm,
                            "valid_spectrum_count": int(record["valid_spectrum_count"]),
                            "reflectance_min": minimum,
                            "reflectance_max": maximum,
                            "reflectance_mean": float(record[f"mean_{index}"]),
                            "reflectance_median": median,
                        }
                    )
                    median_rows.append(
                        {
                            "species": species,
                            "spectral_stage": schema.spectral_stage,
                            "band_index": band.band_index,
                            "wavelength_nm": band.wavelength_nm,
                            "median_reflectance": median,
                            "method": "duckdb_approx_quantile",
                        }
                    )
                    quantile_rows.extend(
                        {
                            "species": species,
                            "spectral_stage": schema.spectral_stage,
                            "band_index": band.band_index,
                            "wavelength_nm": band.wavelength_nm,
                            "quantile": quantile,
                            "reflectance": value,
                            "method": "duckdb_approx_quantile",
                        }
                        for quantile, value in zip(quantiles, values)
                    )
            writers["band"][0].write_table(
                pa.Table.from_pylist(band_rows, schema=_BAND_SUMMARY_SCHEMA)
            )
            writers["quantile"][0].write_table(
                pa.Table.from_pylist(quantile_rows, schema=_QUANTILE_SCHEMA)
            )
            writers["median"][0].write_table(
                pa.Table.from_pylist(median_rows, schema=_MEDIAN_SCHEMA)
            )
    finally:
        for writer, _, _ in writers.values():
            writer.close()
    for _, temporary, final in writers.values():
        pq.read_schema(temporary)
        temporary.replace(final)
    return bounds


def _write_species_summary(
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    group_rows: Sequence[dict[str, Any]],
    bounds: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    result = []
    for row in group_rows:
        if row["grouping_field"] != schema.species_field:
            continue
        minimum, maximum = bounds.get(str(row["group_value"]), (math.nan, math.nan))
        result.append(
            {
                "species": row["group_value"],
                "observation_count": row["observation_count"],
                "valid_spectrum_count": row["valid_spectrum_count"],
                "polygon_count": row["polygon_count"],
                "flightline_count": row["flightline_count"],
                "site_count": row["site_count"],
                "spectral_stage": schema.spectral_stage,
                "band_count": len(schema.bands),
                "wavelength_min_nm": min(schema.wavelengths_nm),
                "wavelength_max_nm": max(schema.wavelengths_nm),
                "reflectance_min": minimum if math.isfinite(minimum) else None,
                "reflectance_max": maximum if math.isfinite(maximum) else None,
            }
        )
    result.sort(key=lambda row: row["species"].casefold())
    _write_table_atomic(paths.species_summary, result, _SPECIES_SUMMARY_SCHEMA)
    return result


def _band_values_expression(schema: SpectralLibrarySchema) -> str:
    return "[" + ", ".join(
        f"TRY_CAST({quote_identifier(band.column)} AS DOUBLE)"
        for band in schema.bands
    ) + "]"


def _outside_value_expression(
    schema: SpectralLibrarySchema,
    operator: str,
    bound: str,
) -> str:
    return " + ".join(
        "CASE WHEN TRY_CAST("
        + quote_identifier(band.column)
        + f" AS DOUBLE) {operator} {bound} THEN 1 ELSE 0 END"
        for band in schema.bands
    )


def _outside_spectrum_expression(
    schema: SpectralLibrarySchema,
    lower: str,
    upper: str,
) -> str:
    return " OR ".join(
        "TRY_CAST("
        + quote_identifier(band.column)
        + f" AS DOUBLE) < {lower} OR TRY_CAST("
        + quote_identifier(band.column)
        + f" AS DOUBLE) > {upper}"
        for band in schema.bands
    )


def _write_plot_ranges(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    group_rows: Sequence[dict[str, Any]],
    full_bounds: dict[str, tuple[float, float]],
    config: SpectralLibraryPlotConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    low_quantile, high_quantile = config.plot_y_quantiles
    species_sql = quote_identifier(schema.species_field)
    values_sql = _band_values_expression(schema)
    quantile_sql = f"[{low_quantile!r}, {high_quantile!r}]"
    base = f"""
        WITH valid AS (
            SELECT CAST({species_sql} AS VARCHAR) AS species, {values_sql} AS values
            FROM read_parquet(?)
            WHERE {species_sql} IS NOT NULL
              AND TRIM(CAST({species_sql} AS VARCHAR)) <> ''
              AND {_valid_predicate(schema, config)}
        ), spectral_values AS (
            SELECT species, UNNEST(values) AS reflectance
            FROM valid
        )
    """
    global_values = con.execute(
        base
        + f"SELECT approx_quantile(reflectance, {quantile_sql}) FROM spectral_values",
        [schema.source.as_posix()],
    ).fetchone()[0]
    global_robust = (float(global_values[0]), float(global_values[1]))
    species_records = con.execute(
        base
        + f"""
            SELECT species, approx_quantile(reflectance, {quantile_sql}) AS bounds
            FROM spectral_values
            GROUP BY species
            ORDER BY species
        """,
        [schema.source.as_posix()],
    ).fetchall()
    robust_by_species = {
        str(species): (float(values[0]), float(values[1]))
        for species, values in species_records
    }
    bounds_table = pa.table(
        {
            "species": list(robust_by_species),
            "species_robust_lower": [
                robust_by_species[species][0] for species in robust_by_species
            ],
            "species_robust_upper": [
                robust_by_species[species][1] for species in robust_by_species
            ],
        }
    )
    relation_name = "_spectralbridge_species_robust_bounds"
    con.register(relation_name, bounds_table)
    try:
        global_lower = repr(global_robust[0])
        global_upper = repr(global_robust[1])
        records = con.execute(
            f"""
                WITH valid AS (
                    SELECT *
                    FROM read_parquet(?)
                    WHERE {species_sql} IS NOT NULL
                      AND TRIM(CAST({species_sql} AS VARCHAR)) <> ''
                      AND {_valid_predicate(schema, config)}
                )
                SELECT
                    CAST(valid.{species_sql} AS VARCHAR) AS species,
                    SUM({_outside_value_expression(schema, '<', global_lower)})::BIGINT
                        AS global_values_below,
                    SUM({_outside_value_expression(schema, '>', global_upper)})::BIGINT
                        AS global_values_above,
                    COUNT(*) FILTER (WHERE {_outside_spectrum_expression(schema, global_lower, global_upper)})::BIGINT
                        AS global_spectra_outside,
                    SUM({_outside_value_expression(schema, '<', 'species_robust_lower')})::BIGINT
                        AS species_values_below,
                    SUM({_outside_value_expression(schema, '>', 'species_robust_upper')})::BIGINT
                        AS species_values_above,
                    COUNT(*) FILTER (WHERE {_outside_spectrum_expression(schema, 'species_robust_lower', 'species_robust_upper')})::BIGINT
                        AS species_spectra_outside
                FROM valid
                JOIN {relation_name} bounds
                  ON CAST(valid.{species_sql} AS VARCHAR) = bounds.species
                GROUP BY CAST(valid.{species_sql} AS VARCHAR)
                ORDER BY species
            """,
            [schema.source.as_posix()],
        ).to_arrow_table().to_pylist()
    finally:
        con.unregister(relation_name)
    counts_by_species = {
        str(row["group_value"]): int(row["valid_spectrum_count"])
        for row in group_rows
        if row["grouping_field"] == schema.species_field
    }
    rows = []
    for record in records:
        species = str(record["species"])
        full_minimum, full_maximum = full_bounds[species]
        species_robust = robust_by_species[species]
        rows.append(
            {
                "species": species,
                "valid_spectrum_count": counts_by_species[species],
                "full_minimum": full_minimum,
                "full_maximum": full_maximum,
                "global_robust_lower": global_robust[0],
                "global_robust_upper": global_robust[1],
                "species_robust_lower": species_robust[0],
                "species_robust_upper": species_robust[1],
                **{key: int(record[key]) for key in record if key != "species"},
            }
        )
    _write_table_atomic(paths.species_plot_ranges, rows, _PLOT_RANGE_SCHEMA)
    global_full = (
        min(value[0] for value in full_bounds.values()),
        max(value[1] for value in full_bounds.values()),
    )
    metadata = {
        "quantiles": [low_quantile, high_quantile],
        "method": "DuckDB approx_quantile over all valid selected-stage values",
        "global_robust": list(global_robust),
        "global_full": list(global_full),
        "global_values_below": sum(row["global_values_below"] for row in rows),
        "global_values_above": sum(row["global_values_above"] for row in rows),
        "global_spectra_outside": sum(row["global_spectra_outside"] for row in rows),
        "graphical_clipping_only": True,
        "analytical_summaries_unchanged": True,
    }
    return rows, metadata


def _metadata_expression(field: str | None, alias: str) -> str:
    if field is None:
        return f"NULL::VARCHAR AS {quote_identifier(alias)}"
    return (
        f"CAST({quote_identifier(field)} AS VARCHAR) AS {quote_identifier(alias)}"
    )


def _write_extreme_spectra(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    config: SpectralLibraryPlotConfig,
) -> list[dict[str, Any]]:
    range_policy = (
        config.species_y_scale
        if config.species_y_scale != "global_full"
        else "global_robust"
    )
    if range_policy == "per_group_robust":
        lower = "species_robust_lower"
        upper = "species_robust_upper"
    else:
        lower = "global_robust_lower"
        upper = "global_robust_upper"
    species_sql = quote_identifier(schema.species_field)
    metadata = ", ".join(
        (
            _metadata_expression(schema.polygon_field, "polygon_id"),
            _metadata_expression(schema.flightline_field, "flightline_id"),
            _metadata_expression(schema.site_field, "site"),
            _metadata_expression(schema.pixel_field, "pixel_id"),
        )
    )
    values = ", ".join(
        f"TRY_CAST({quote_identifier(band.column)} AS DOUBLE)"
        for band in schema.bands
    )
    below = _outside_value_expression(schema, "<", lower)
    above = _outside_value_expression(schema, ">", upper)
    rows = con.execute(
        f"""
            WITH valid AS (
                SELECT CAST({species_sql} AS VARCHAR) AS species,
                       {metadata},
                       {', '.join(quote_identifier(band.column) for band in schema.bands)}
                FROM read_parquet(?)
                WHERE {species_sql} IS NOT NULL
                  AND TRIM(CAST({species_sql} AS VARCHAR)) <> ''
                  AND {_valid_predicate(schema, config)}
            ), scored AS (
                SELECT valid.*,
                       {lower} AS display_lower,
                       {upper} AS display_upper,
                       LEAST({values}) AS spectrum_minimum,
                       GREATEST({values}) AS spectrum_maximum,
                       ({below})::INTEGER AS wavelengths_below_robust_range,
                       ({above})::INTEGER AS wavelengths_above_robust_range
                FROM valid
                JOIN read_parquet(?) ranges USING (species)
            ), ranked AS (
                SELECT *,
                       wavelengths_below_robust_range
                           + wavelengths_above_robust_range
                           AS wavelengths_outside_robust_range,
                       ROW_NUMBER() OVER (
                           PARTITION BY species
                           ORDER BY
                               wavelengths_below_robust_range
                                   + wavelengths_above_robust_range DESC,
                               GREATEST(
                                   ABS(spectrum_minimum - display_lower),
                                   ABS(spectrum_maximum - display_upper)
                               ) DESC,
                               hash(
                                   COALESCE(pixel_id, ''),
                                   COALESCE(polygon_id, ''),
                                   COALESCE(flightline_id, ''),
                                   COALESCE(site, '')
                               )
                       )::INTEGER AS rank_within_species
                FROM scored
                WHERE wavelengths_below_robust_range
                    + wavelengths_above_robust_range > 0
            )
            SELECT species, polygon_id, flightline_id, site, pixel_id,
                   spectrum_minimum, spectrum_maximum,
                   wavelengths_below_robust_range,
                   wavelengths_above_robust_range,
                   wavelengths_outside_robust_range,
                   rank_within_species,
                   ? AS range_policy
            FROM ranked
            WHERE rank_within_species <= ?
            ORDER BY species, rank_within_species
        """,
        [
            schema.source.as_posix(),
            paths.species_plot_ranges.as_posix(),
            range_policy,
            config.max_extreme_spectra_per_species,
        ],
    ).to_arrow_table().to_pylist()
    _write_table_atomic(paths.extreme_spectra, rows, _EXTREME_SPECTRUM_SCHEMA)
    return rows


def _ordered_groups(
    rows: Sequence[dict[str, Any]],
    *,
    grouping_field: str,
    order: str,
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row["grouping_field"] == grouping_field and row["valid_spectrum_count"] > 0
    ]
    if order == "alphabetical":
        return sorted(selected, key=lambda row: row["group_value"].casefold())
    return sorted(
        selected,
        key=lambda row: (-row["valid_spectrum_count"], row["group_value"].casefold()),
    )


def inspect_spectral_library_preflight(
    path: str | Path,
    *,
    config: SpectralLibraryPlotConfig | None = None,
) -> dict[str, Any]:
    """Inspect schema, exact group counts, and approximate report cost without PDFs."""

    config = config or SpectralLibraryPlotConfig()
    config.validate()
    schema = inspect_spectral_library(
        path,
        species_field=config.species_field,
        spectral_stage=config.spectral_stage,
    )
    fields = [schema.species_field]
    fields.extend(
        field
        for field in (schema.polygon_field, schema.flightline_field, schema.site_field)
        if field is not None and field not in fields
    )
    with duckdb.connect() as con:
        group_rows = [
            row
            for field in fields
            for row in _group_count_rows(con, schema, field, config)
        ]
    groups_by_field = {
        field: [
            row
            for row in group_rows
            if row["grouping_field"] == field and row["valid_spectrum_count"] > 0
        ]
        for field in fields
    }
    species_rows = groups_by_field[schema.species_field]
    species_counts = [int(row["valid_spectrum_count"]) for row in species_rows]
    largest = (
        max(
            species_rows,
            key=lambda row: (
                int(row["valid_spectrum_count"]),
                str(row["group_value"]).casefold(),
            ),
        )
        if species_rows
        else None
    )

    def rendered_count(rows: Sequence[dict[str, Any]]) -> int:
        return sum(
            min(
                int(row["valid_spectrum_count"]),
                config.max_traces_per_group
                or int(row["valid_spectrum_count"]),
            )
            for row in rows
        )

    species_pages = math.ceil(len(species_rows) / config.panels_per_page)
    site_rows = groups_by_field.get(schema.site_field or "", [])
    flightline_rows = groups_by_field.get(schema.flightline_field or "", [])
    hierarchy_levels = sum(
        field is not None
        for field in (schema.polygon_field, schema.flightline_field, schema.site_field)
    )
    compact_scans = (
        len(fields)
        + math.ceil(len(schema.bands) / config.summary_band_batch_size)
        + 4
    )
    full_report_scans = (
        2 * len(species_rows)
        + 2 * len(site_rows)
        + 2 * len(flightline_rows)
        + hierarchy_levels * len(species_rows)
    )
    expected_pages = {
        "species_medians": 1 if species_rows else 0,
        "observation_counts": math.ceil(len(species_rows) / 35),
        "species_variability": species_pages,
        "species_variability_full_range": species_pages,
        "species_quantiles": species_pages,
        "hierarchical_variability": species_pages if hierarchy_levels else 0,
        "site_variability": math.ceil(len(site_rows) / config.panels_per_page),
        "flightline_variability": math.ceil(
            len(flightline_rows) / config.panels_per_page
        ),
    }
    counts = {
        "source_rows": schema.row_count,
        "valid_spectra": sum(species_counts),
        "species": len(species_rows),
        "polygons": len(groups_by_field.get(schema.polygon_field or "", [])),
        "flightlines": len(flightline_rows),
        "sites": len(site_rows),
    }
    return {
        "source": schema.source.as_posix(),
        "source_size_bytes": schema.source.stat().st_size,
        "source_signature_sha256": schema.source_signature_sha256,
        "schema": schema.to_dict(),
        "visualization_validity": _visualization_validity_policy(schema, config),
        "counts": counts,
        "largest_species": (
            {
                "species": str(largest["group_value"]),
                "valid_spectrum_count": int(largest["valid_spectrum_count"]),
            }
            if largest is not None
            else None
        ),
        "median_valid_spectra_per_species": (
            float(np.median(species_counts)) if species_counts else 0.0
        ),
        "species_over_10k_traces": sum(count > 10_000 for count in species_counts),
        "species_over_100k_traces": sum(count > 100_000 for count in species_counts),
        "estimated_total_raw_traces_to_render": (
            2 * rendered_count(species_rows)
            + rendered_count(site_rows)
            + rendered_count(flightline_rows)
        ),
        "trace_cap": config.max_traces_per_group,
        "all_valid_traces_requested": config.max_traces_per_group is None,
        "expected_pages": expected_pages,
        "expected_repeated_parquet_scans": {
            "preflight_group_count_scans": len(fields),
            "compact_summary_and_diagnostic_scans": compact_scans,
            "full_report_group_filtered_scans": full_report_scans,
            "note": (
                "Counts are logical source scans; DuckDB may prune row groups/columns. "
                "PDF rendering rescans one selected group at a time."
            ),
        },
        "configuration": asdict(config),
        "pdfs_generated": False,
    }


def _report_cost_from_group_rows(
    schema: SpectralLibrarySchema,
    config: SpectralLibraryPlotConfig,
    group_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    def selected(field: str | None) -> list[dict[str, Any]]:
        if field is None:
            return []
        return [
            row
            for row in group_rows
            if row["grouping_field"] == field and row["valid_spectrum_count"] > 0
        ]

    def rendered(rows: Sequence[dict[str, Any]]) -> int:
        return sum(
            min(
                int(row["valid_spectrum_count"]),
                config.max_traces_per_group
                or int(row["valid_spectrum_count"]),
            )
            for row in rows
        )

    species_rows = selected(schema.species_field)
    site_rows = selected(schema.site_field)
    flightline_rows = selected(schema.flightline_field)
    species_counts = [int(row["valid_spectrum_count"]) for row in species_rows]
    largest = (
        max(
            species_rows,
            key=lambda row: (
                int(row["valid_spectrum_count"]),
                str(row["group_value"]).casefold(),
            ),
        )
        if species_rows
        else None
    )
    panels = config.panels_per_page
    species_pages = math.ceil(len(species_rows) / panels)
    hierarchy_levels = sum(
        field is not None
        for field in (schema.polygon_field, schema.flightline_field, schema.site_field)
    )
    fields_scanned = 1 + hierarchy_levels
    compact_scans = (
        fields_scanned
        + math.ceil(len(schema.bands) / config.summary_band_batch_size)
        + 4
    )
    full_report_scans = (
        2 * len(species_rows)
        + 2 * len(site_rows)
        + 2 * len(flightline_rows)
        + hierarchy_levels * len(species_rows)
    )
    return {
        "source_rows": schema.row_count,
        "source_size_bytes": schema.source.stat().st_size,
        "species_count": len(species_rows),
        "largest_species": (
            {
                "species": str(largest["group_value"]),
                "valid_spectrum_count": int(largest["valid_spectrum_count"]),
            }
            if largest is not None
            else None
        ),
        "median_valid_spectra_per_species": (
            float(np.median(species_counts)) if species_counts else 0.0
        ),
        "species_over_10k_traces": sum(count > 10_000 for count in species_counts),
        "species_over_100k_traces": sum(count > 100_000 for count in species_counts),
        "estimated_total_raw_traces_to_render": (
            2 * rendered(species_rows)
            + rendered(site_rows)
            + rendered(flightline_rows)
        ),
        "trace_cap": config.max_traces_per_group,
        "all_valid_traces_requested": config.max_traces_per_group is None,
        "expected_full_report_pages": (
            3 * species_pages
            + (species_pages if hierarchy_levels else 0)
            + math.ceil(len(site_rows) / panels)
            + math.ceil(len(flightline_rows) / panels)
            + math.ceil(len(species_rows) / 35)
            + (1 if species_rows else 0)
        ),
        "expected_repeated_parquet_scans": {
            "compact_summary_and_diagnostic_scans": compact_scans,
            "full_report_group_filtered_scans": full_report_scans,
            "note": (
                "Counts are logical source scans; DuckDB may prune row groups/columns. "
                "PDF rendering rescans one selected group at a time."
            ),
        },
    }


def iter_group_spectra(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    *,
    grouping_field: str,
    group_value: str,
    batch_size: int,
    max_traces: int | None = None,
    sampling_seed: int = 0,
    config: SpectralLibraryPlotConfig | None = None,
) -> Iterator[np.ndarray]:
    """Yield one group's spectra as bounded NumPy batches without pandas."""

    config = config or SpectralLibraryPlotConfig()
    config.validate()
    fields = ", ".join(quote_identifier(band.column) for band in schema.bands)
    group_sql = quote_identifier(grouping_field)
    base = (
        f"SELECT {fields} FROM read_parquet(?) "
        f"WHERE CAST({group_sql} AS VARCHAR) = ? AND "
        f"{_valid_predicate(schema, config)}"
    )
    parameters: list[Any] = [schema.source.as_posix(), group_value]
    if max_traces is not None:
        identity_fields = [
            field
            for field in (
                schema.pixel_field,
                schema.polygon_field,
                schema.flightline_field,
                schema.site_field,
                schema.species_field,
            )
            if field is not None
        ]
        identity = ", ".join(
            f"COALESCE(CAST({quote_identifier(field)} AS VARCHAR), '')"
            for field in identity_fields
        )
        if not identity:
            identity = f"CAST({quote_identifier(schema.bands[0].column)} AS VARCHAR)"
        base += (
            " ORDER BY hash(concat_ws('|', "
            + identity
            + ", CAST(? AS VARCHAR))) LIMIT ?"
        )
        parameters.extend((sampling_seed, max_traces))
    reader = con.execute(base, parameters).to_arrow_reader(batch_size)
    for batch in reader:
        if batch.num_rows == 0:
            continue
        yield np.column_stack(
            [
                batch.column(index).to_numpy(zero_copy_only=False).astype(np.float64)
                for index in range(batch.num_columns)
            ]
        )


def _group_median(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    grouping_field: str,
    group_value: str,
    config: SpectralLibraryPlotConfig,
) -> np.ndarray:
    expressions = ", ".join(
        "approx_quantile(TRY_CAST("
        + quote_identifier(band.column)
        + " AS DOUBLE), 0.5)"
        for band in schema.bands
    )
    query = (
        f"SELECT {expressions} FROM read_parquet(?) WHERE "
        f"CAST({quote_identifier(grouping_field)} AS VARCHAR) = ? AND "
        + _valid_predicate(schema, config)
    )
    row = con.execute(query, [schema.source.as_posix(), group_value]).fetchone()
    return np.asarray(row, dtype=np.float64)


def _species_median(
    con: duckdb.DuckDBPyConnection,
    paths: SpectralLibraryPaths,
    species: str,
) -> np.ndarray:
    rows = con.execute(
        "SELECT median_reflectance FROM read_parquet(?) WHERE species = ? "
        "ORDER BY wavelength_nm, band_index",
        [paths.species_medians.as_posix(), species],
    ).fetchall()
    return np.asarray([row[0] for row in rows], dtype=np.float64)


def _trace_raster(
    wavelengths: np.ndarray,
    spectra: Iterator[np.ndarray],
    *,
    alpha: float,
    x_limits: tuple[float, float],
    y_limits: tuple[float, float],
    dpi: int,
    color: str = "#2A6F97",
    linewidth: float = 0.28,
) -> np.ndarray:
    return _layered_trace_raster(
        wavelengths,
        ((spectra, color, alpha, linewidth),),
        x_limits=x_limits,
        y_limits=y_limits,
        dpi=dpi,
    )


def _layered_trace_raster(
    wavelengths: np.ndarray,
    layers: Sequence[tuple[Iterator[np.ndarray], str, float, float]],
    *,
    x_limits: tuple[float, float],
    y_limits: tuple[float, float],
    dpi: int,
) -> np.ndarray:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure

    figure = Figure(figsize=(5.0, 2.7), dpi=dpi, facecolor="white")
    canvas = FigureCanvasAgg(figure)
    axis = figure.add_axes((0, 0, 1, 1), facecolor="white")
    axis.set_axis_off()
    axis.set_xlim(*x_limits)
    axis.set_ylim(*y_limits)
    canvas.draw()
    for spectra, color, alpha, linewidth in layers:
        for values in spectra:
            segments = np.empty((values.shape[0], values.shape[1], 2), dtype=np.float64)
            segments[:, :, 0] = wavelengths
            segments[:, :, 1] = values
            collection = LineCollection(
                segments,
                colors=color,
                linewidths=linewidth,
                alpha=alpha,
                antialiased=False,
            )
            axis.add_collection(collection)
            axis.draw_artist(collection)
            collection.remove()
    return np.asarray(canvas.buffer_rgba()).copy()


def _limits(values: tuple[float, float]) -> tuple[float, float]:
    minimum, maximum = values
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        return (0.0, 1.0)
    if minimum == maximum:
        padding = max(0.01, abs(minimum) * 0.05)
        return minimum - padding, maximum + padding
    padding = (maximum - minimum) * 0.025
    return minimum - padding, maximum + padding


def _page_layout(panels_per_page: int) -> tuple[int, int]:
    columns = 2 if panels_per_page > 1 else 1
    rows = math.ceil(panels_per_page / columns)
    return rows, columns


def _pdf_metadata(title: str, subject: str) -> dict[str, Any]:
    return {
        "Title": title,
        "Author": "SpectralBridge",
        "Subject": subject,
        "Keywords": "spectral library, reflectance, variability, low-alpha ensemble",
        "CreationDate": datetime.now(timezone.utc),
    }


def _finish_pdf(temporary: Path, final: Path) -> None:
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise RuntimeError(f"Spectral-library PDF was not created: {temporary}")
    with temporary.open("rb") as stream:
        if stream.read(4) != b"%PDF":
            raise RuntimeError(f"Invalid PDF output: {temporary}")
    temporary.replace(final)


def _trace_report(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    groups: Sequence[dict[str, Any]],
    *,
    grouping_field: str,
    output: Path,
    config: SpectralLibraryPlotConfig,
    global_bounds: tuple[float, float],
    display_mode: str,
    species_range_rows: Sequence[dict[str, Any]] = (),
) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    if temporary.exists():
        temporary.unlink()
    wavelengths = np.asarray(schema.wavelengths_nm, dtype=np.float64)
    x_limits = _limits((float(wavelengths.min()), float(wavelengths.max())))
    range_by_species = {str(row["species"]): row for row in species_range_rows}
    low_quantile, high_quantile = config.plot_y_quantiles
    if display_mode == "global_robust":
        range_note = (
            f"Common display range: robust {low_quantile * 100:g}-"
            f"{high_quantile * 100:g}% reflectance "
            f"[{global_bounds[0]:.4g}, {global_bounds[1]:.4g}]. "
            "Values outside are visually clipped only."
        )
        title_suffix = "robust common range"
    elif display_mode == "per_group_robust":
        range_note = (
            f"Each panel uses its robust {low_quantile * 100:g}-"
            f"{high_quantile * 100:g}% range. Values outside are visually clipped only; "
            "local scales maximize within-group detail."
        )
        title_suffix = "robust per-group range"
    else:
        range_note = (
            f"Common display range: full observed reflectance "
            f"[{global_bounds[0]:.4g}, {global_bounds[1]:.4g}]. No graphical clipping."
        )
        title_suffix = "full-range audit"
    rows, columns = _page_layout(config.panels_per_page)
    pages = 0
    with PdfPages(
        temporary,
        metadata=_pdf_metadata(
            f"Spectral library variability by {grouping_field}",
            "Qualitative low-alpha trace density; not a normalized probability density.",
        ),
    ) as pdf:
        for start in range(0, len(groups), config.panels_per_page):
            page_groups = groups[start : start + config.panels_per_page]
            figure = Figure(figsize=(11.0, 8.5), facecolor="white", constrained_layout=True)
            layout_engine = figure.get_layout_engine()
            if layout_engine is not None:
                layout_engine.set(rect=(0.0, 0.07, 1.0, 0.91))
            axes = figure.subplots(rows, columns, squeeze=False)
            for axis, group in zip(axes.flat, page_groups):
                group_range = range_by_species.get(str(group["group_value"]))
                if display_mode == "per_group_robust" and group_range is not None:
                    panel_bounds = (
                        float(group_range["species_robust_lower"]),
                        float(group_range["species_robust_upper"]),
                    )
                else:
                    panel_bounds = global_bounds
                y_limits = (
                    _limits(panel_bounds)
                    if display_mode == "global_full"
                    or panel_bounds[0] == panel_bounds[1]
                    else panel_bounds
                )
                count = int(group["valid_spectrum_count"])
                shown = min(count, config.max_traces_per_group or count)
                alpha = trace_alpha(shown)
                spectra = iter_group_spectra(
                    con,
                    schema,
                    grouping_field=grouping_field,
                    group_value=group["group_value"],
                    batch_size=config.trace_batch_size,
                    max_traces=config.max_traces_per_group,
                    sampling_seed=config.sampling_seed,
                    config=config,
                )
                raster = _trace_raster(
                    wavelengths,
                    spectra,
                    alpha=alpha,
                    x_limits=x_limits,
                    y_limits=y_limits,
                    dpi=config.raster_dpi,
                )
                axis.imshow(
                    raster,
                    extent=(*x_limits, *y_limits),
                    origin="upper",
                    aspect="auto",
                    interpolation="nearest",
                    zorder=1,
                )
                median = (
                    _species_median(con, paths, group["group_value"])
                    if grouping_field == schema.species_field
                    else _group_median(
                        con,
                        schema,
                        grouping_field,
                        group["group_value"],
                        config,
                    )
                )
                axis.plot(wavelengths, median, color="#172B4D", linewidth=1.25, zorder=3)
                suffix = f"{shown:,} of {count:,} traces" if shown != count else f"{count:,} spectra"
                if grouping_field == schema.species_field:
                    suffix += (
                        f" | {group['polygon_count']:,} polygons | "
                        f"{group['flightline_count']:,} flightlines | {group['site_count']:,} sites"
                    )
                    if group_range is not None and display_mode != "global_full":
                        outlier_key = (
                            "species_spectra_outside"
                            if display_mode == "per_group_robust"
                            else "global_spectra_outside"
                        )
                        outside = int(group_range[outlier_key])
                        if outside:
                            suffix += f" | {outside:,} outside display range"
                axis.set_title(
                    str(group["group_value"]),
                    loc="left",
                    fontsize=10,
                    weight="semibold",
                    pad=24,
                )
                axis.text(
                    0.0,
                    1.01,
                    f"{suffix}; trace alpha={alpha:.4f}",
                    transform=axis.transAxes,
                    fontsize=7,
                    color="#52606D",
                )
                axis.set_xlim(*x_limits)
                axis.set_ylim(*y_limits)
                axis.set_xlabel("Wavelength (nm)", fontsize=8)
                axis.set_ylabel("Reflectance", fontsize=8)
                axis.tick_params(labelsize=7)
                axis.spines[["top", "right"]].set_visible(False)
            for axis in axes.flat[len(page_groups) :]:
                axis.set_visible(False)
            pages += 1
            figure.suptitle(
                f"Spectral variability by {grouping_field} - {title_suffix}",
                fontsize=13,
            )
            figure.text(
                0.5,
                0.012,
                f"{range_note}\nPage {pages} | trace layer rasterized; axes and median remain vector",
                ha="center",
                fontsize=7,
                color="#52606D",
            )
            pdf.savefig(figure, dpi=config.raster_dpi)
    _finish_pdf(temporary, output)
    return pages


def _quantile_report(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    groups: Sequence[dict[str, Any]],
    config: SpectralLibraryPlotConfig,
) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure

    output = paths.species_quantile_report
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    if temporary.exists():
        temporary.unlink()
    rows, columns = _page_layout(config.panels_per_page)
    pages = 0
    with PdfPages(
        temporary,
        metadata=_pdf_metadata(
            "Spectral library species quantiles",
            "Approximate nested quantile envelopes complementing low-alpha traces.",
        ),
    ) as pdf:
        for start in range(0, len(groups), config.panels_per_page):
            page_groups = groups[start : start + config.panels_per_page]
            figure = Figure(figsize=(11.0, 8.5), facecolor="white", constrained_layout=True)
            axes = figure.subplots(rows, columns, squeeze=False)
            for axis, group in zip(axes.flat, page_groups):
                records = con.execute(
                    "SELECT wavelength_nm, quantile, reflectance FROM read_parquet(?) "
                    "WHERE species = ? ORDER BY wavelength_nm, quantile",
                    [paths.species_quantiles.as_posix(), group["group_value"]],
                ).fetchall()
                by_quantile: dict[float, tuple[list[float], list[float]]] = {}
                for wavelength, quantile, reflectance in records:
                    pair = by_quantile.setdefault(float(quantile), ([], []))
                    pair[0].append(float(wavelength))
                    pair[1].append(float(reflectance))
                for low, high, alpha in ((0.025, 0.975, 0.12), (0.10, 0.90, 0.18), (0.25, 0.75, 0.28)):
                    if low in by_quantile and high in by_quantile:
                        axis.fill_between(
                            by_quantile[low][0],
                            by_quantile[low][1],
                            by_quantile[high][1],
                            color="#2A6F97",
                            alpha=alpha,
                            linewidth=0,
                            label=f"{low:g}-{high:g}",
                        )
                median = by_quantile[0.5]
                axis.plot(median[0], median[1], color="#172B4D", linewidth=1.35, label="median")
                axis.set_title(
                    f"{group['group_value']} ({group['valid_spectrum_count']:,} spectra)",
                    loc="left",
                    fontsize=10,
                    weight="semibold",
                )
                axis.set_xlabel("Wavelength (nm)", fontsize=8)
                axis.set_ylabel("Reflectance", fontsize=8)
                axis.tick_params(labelsize=7)
                axis.spines[["top", "right"]].set_visible(False)
            for axis in axes.flat[len(page_groups) :]:
                axis.set_visible(False)
            pages += 1
            figure.suptitle("Within-species approximate spectral quantiles", fontsize=13)
            figure.text(0.5, 0.005, f"Page {pages}", ha="center", fontsize=7, color="#52606D")
            pdf.savefig(figure)
    _finish_pdf(temporary, output)
    return pages


def _median_overview_report(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    groups: Sequence[dict[str, Any]],
) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure

    output = paths.species_median_report
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    if temporary.exists():
        temporary.unlink()
    wavelengths = np.asarray(schema.wavelengths_nm)
    spectra = np.vstack(
        [_species_median(con, paths, group["group_value"]) for group in groups]
    )
    segments = np.empty((len(groups), len(wavelengths), 2), dtype=np.float64)
    segments[:, :, 0] = wavelengths
    segments[:, :, 1] = spectra
    with PdfPages(
        temporary,
        metadata=_pdf_metadata(
            "Spectral library species medians",
            "One low-alpha median spectrum per species; between-species spectral diversity.",
        ),
    ) as pdf:
        figure = Figure(figsize=(11.0, 8.5), facecolor="white", constrained_layout=True)
        axis = figure.subplots()
        axis.add_collection(
            LineCollection(
                segments,
                colors="#2A6F97",
                alpha=trace_alpha(len(groups)),
                linewidths=0.65,
                rasterized=True,
            )
        )
        axis.autoscale()
        axis.set_xlabel("Wavelength (nm)")
        axis.set_ylabel("Median reflectance")
        axis.set_title(f"Between-species spectral diversity ({len(groups):,} species)", loc="left")
        axis.spines[["top", "right"]].set_visible(False)
        axis.text(
            0.0,
            -0.10,
            "Each line is one species median. Overplotting is qualitative, not a normalized density.",
            transform=axis.transAxes,
            fontsize=8,
            color="#52606D",
        )
        pdf.savefig(figure)
    _finish_pdf(temporary, output)
    return 1


def _counts_report(
    groups: Sequence[dict[str, Any]],
    paths: SpectralLibraryPaths,
) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure

    output = paths.observation_counts
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    if temporary.exists():
        temporary.unlink()
    per_page = 35
    pages = 0
    with PdfPages(
        temporary,
        metadata=_pdf_metadata(
            "Spectral library observation counts",
            "Species contributions and hierarchy counts.",
        ),
    ) as pdf:
        for start in range(0, len(groups), per_page):
            page_groups = groups[start : start + per_page]
            figure = Figure(figsize=(11.0, 8.5), facecolor="white", constrained_layout=True)
            axis = figure.subplots()
            labels = [str(row["group_value"]) for row in reversed(page_groups)]
            counts = [int(row["valid_spectrum_count"]) for row in reversed(page_groups)]
            bars = axis.barh(labels, counts, color="#2A6F97", alpha=0.82)
            annotations = [
                (
                    f"{int(row['valid_spectrum_count']):,} spectra | "
                    f"{int(row['polygon_count']):,} polygons | "
                    f"{int(row['flightline_count']):,} flightlines | "
                    f"{int(row['site_count']):,} sites"
                )
                for row in reversed(page_groups)
            ]
            axis.bar_label(bars, labels=annotations, padding=3, fontsize=6)
            axis.margins(x=0.25)
            if counts and min(counts) > 0 and max(counts) / min(counts) >= 50:
                axis.set_xscale("log")
                axis.set_xlabel("Valid spectra (log scale)")
            else:
                axis.set_xlabel("Valid spectra")
            axis.set_title("Spectral-library observations by species", loc="left")
            axis.tick_params(axis="y", labelsize=7)
            axis.spines[["top", "right"]].set_visible(False)
            pages += 1
            figure.text(
                0.99,
                0.005,
                f"Page {pages}",
                ha="right",
                fontsize=7,
                color="#52606D",
            )
            pdf.savefig(figure)
    _finish_pdf(temporary, output)
    return pages


def _iter_hierarchy_medians(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    *,
    species: str,
    grouping_field: str,
    batch_size: int,
    config: SpectralLibraryPlotConfig,
) -> Iterator[np.ndarray]:
    expressions = ", ".join(
        "approx_quantile(TRY_CAST("
        + quote_identifier(band.column)
        + " AS DOUBLE), 0.5) AS "
        + quote_identifier(f"band_{index}")
        for index, band in enumerate(schema.bands)
    )
    query = f"""
        SELECT {expressions}
        FROM read_parquet(?)
        WHERE CAST({quote_identifier(schema.species_field)} AS VARCHAR) = ?
          AND {quote_identifier(grouping_field)} IS NOT NULL
          AND {_valid_predicate(schema, config)}
        GROUP BY {quote_identifier(grouping_field)}
    """
    reader = con.execute(query, [schema.source.as_posix(), species]).to_arrow_reader(
        batch_size
    )
    for batch in reader:
        yield np.column_stack(
            [batch.column(index).to_numpy(zero_copy_only=False) for index in range(batch.num_columns)]
        ).astype(np.float64)


def _hierarchy_report(
    con: duckdb.DuckDBPyConnection,
    schema: SpectralLibrarySchema,
    paths: SpectralLibraryPaths,
    groups: Sequence[dict[str, Any]],
    config: SpectralLibraryPlotConfig,
    global_bounds: tuple[float, float],
) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.lines import Line2D
    from matplotlib.figure import Figure

    hierarchy = [
        (schema.polygon_field, "polygon medians", "#86BBD8", 0.08, 0.35),
        (schema.flightline_field, "flightline medians", "#F6AE2D", 0.24, 0.65),
        (schema.site_field, "site medians", "#D1495B", 0.55, 0.9),
    ]
    hierarchy = [item for item in hierarchy if item[0] is not None]
    if not hierarchy:
        return 0
    output = paths.hierarchy_report
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    if temporary.exists():
        temporary.unlink()
    wavelengths = np.asarray(schema.wavelengths_nm, dtype=np.float64)
    x_limits = _limits((float(wavelengths.min()), float(wavelengths.max())))
    y_limits = _limits(global_bounds)
    page_rows, page_columns = _page_layout(config.panels_per_page)
    pages = 0
    with PdfPages(
        temporary,
        metadata=_pdf_metadata(
            "Spectral library hierarchical variability",
            "Polygon, flightline, and site median spectra within each species.",
        ),
    ) as pdf:
        for start in range(0, len(groups), config.panels_per_page):
            page_groups = groups[start : start + config.panels_per_page]
            figure = Figure(figsize=(11.0, 8.5), facecolor="white", constrained_layout=True)
            axes = figure.subplots(page_rows, page_columns, squeeze=False)
            for axis, group in zip(axes.flat, page_groups):
                layers = tuple(
                    (
                        _iter_hierarchy_medians(
                            con,
                            schema,
                            species=group["group_value"],
                            grouping_field=str(field),
                            batch_size=config.trace_batch_size,
                            config=config,
                        ),
                        color,
                        alpha,
                        linewidth,
                    )
                    for field, _, color, alpha, linewidth in hierarchy
                )
                raster = _layered_trace_raster(
                    wavelengths,
                    layers,
                    x_limits=x_limits,
                    y_limits=y_limits,
                    dpi=config.raster_dpi,
                )
                axis.imshow(
                    raster,
                    extent=(*x_limits, *y_limits),
                    origin="upper",
                    aspect="auto",
                    interpolation="nearest",
                    zorder=1,
                )
                axis.plot(
                    wavelengths,
                    _species_median(con, paths, group["group_value"]),
                    color="#172B4D",
                    linewidth=1.4,
                    label="species median",
                    zorder=3,
                )
                axis.set_title(str(group["group_value"]), loc="left", fontsize=10, weight="semibold")
                axis.set_xlim(*x_limits)
                axis.set_ylim(*y_limits)
                axis.set_xlabel("Wavelength (nm)", fontsize=8)
                axis.set_ylabel("Reflectance", fontsize=8)
                axis.tick_params(labelsize=7)
                axis.spines[["top", "right"]].set_visible(False)
            for axis in axes.flat[len(page_groups) :]:
                axis.set_visible(False)
            handles = [
                Line2D([0], [0], color=color, alpha=max(alpha, 0.5), linewidth=linewidth, label=label)
                for _, label, color, alpha, linewidth in hierarchy
            ]
            handles.append(Line2D([0], [0], color="#172B4D", linewidth=1.4, label="species median"))
            figure.legend(handles=handles, loc="outside lower center", ncols=len(handles), fontsize=7)
            pages += 1
            figure.suptitle("Hierarchical spectral variability within species", fontsize=13)
            pdf.savefig(figure, dpi=config.raster_dpi)
    _finish_pdf(temporary, output)
    return pages


def _register_outputs(
    con: duckdb.DuckDBPyConnection,
    paths: SpectralLibraryPaths,
) -> None:
    for table, path in (
        ("spectral_library_species_summary", paths.species_summary),
        ("spectral_library_species_band_summary", paths.species_band_summary),
        ("spectral_library_species_quantiles", paths.species_quantiles),
        ("spectral_library_species_medians", paths.species_medians),
        ("spectral_library_group_counts", paths.group_counts),
        ("spectral_library_species_plot_ranges", paths.species_plot_ranges),
        ("spectral_library_extreme_spectra", paths.extreme_spectra),
    ):
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_parquet(?)",
            [path.as_posix()],
        )


def run_spectral_library_analysis(
    con: duckdb.DuckDBPyConnection,
    bulk_paths: BulkAnalysisPaths,
    *,
    spectral_library: str | Path,
    analysis_run_id: str,
    config: SpectralLibraryPlotConfig | None = None,
    make_summary_plots: bool = True,
    make_full_spectral_reports: bool = False,
    minimum_reflectance: float | None = None,
) -> dict[str, Any]:
    """Build compact summaries and requested PDFs without copying source spectra."""

    config = config or SpectralLibraryPlotConfig()
    if minimum_reflectance is not None:
        legacy_minimum = float(minimum_reflectance)
        if not math.isfinite(legacy_minimum):
            raise ValueError("minimum_reflectance must be finite or None")
        configured_minimum = config.spectral_plot_minimum_reflectance
        if configured_minimum is not None and configured_minimum != legacy_minimum:
            raise ValueError(
                "minimum_reflectance and spectral_plot_minimum_reflectance disagree"
            )
        config = replace(
            config,
            spectral_plot_minimum_reflectance=legacy_minimum,
        )
    config.validate()
    schema = inspect_spectral_library(
        spectral_library,
        species_field=config.species_field,
        spectral_stage=config.spectral_stage,
    )
    paths = SpectralLibraryPaths.from_bulk_paths(bulk_paths)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.figures_dir.mkdir(parents=True, exist_ok=True)
    group_rows = _write_group_counts(
        con,
        schema,
        paths,
        config,
    )
    bounds = _write_species_spectral_summaries(
        con,
        schema,
        paths,
        band_batch_size=config.summary_band_batch_size,
        quantiles=config.quantiles,
        config=config,
    )
    species_summary = _write_species_summary(schema, paths, group_rows, bounds)
    species_groups = _ordered_groups(
        group_rows,
        grouping_field=schema.species_field,
        order=config.species_sort,
    )
    if not species_groups:
        raise ValueError(
            "Spectral library contains no complete spectra satisfying the "
            "configured visualization validity rule by species"
        )
    range_rows, range_metadata = _write_plot_ranges(
        con,
        schema,
        paths,
        group_rows,
        bounds,
        config,
    )
    extreme_rows = _write_extreme_spectra(con, schema, paths, config)
    global_full_bounds = tuple(range_metadata["global_full"])
    global_robust_bounds = tuple(range_metadata["global_robust"])
    primary_bounds = (
        global_full_bounds
        if config.species_y_scale == "global_full"
        else global_robust_bounds
    )
    reports: dict[str, dict[str, Any]] = {}
    if make_summary_plots or make_full_spectral_reports:
        reports["species_medians"] = {
            "path": paths.species_median_report.as_posix(),
            "pages": _median_overview_report(con, schema, paths, species_groups),
        }
        reports["observation_counts"] = {
            "path": paths.observation_counts.as_posix(),
            "pages": _counts_report(species_groups, paths),
        }
    if make_full_spectral_reports:
        reports["species_variability"] = {
            "path": paths.species_variability.as_posix(),
            "pages": _trace_report(
                con,
                schema,
                paths,
                species_groups,
                grouping_field=schema.species_field,
                output=paths.species_variability,
                config=config,
                global_bounds=primary_bounds,
                display_mode=config.species_y_scale,
                species_range_rows=range_rows,
            ),
            "display_mode": config.species_y_scale,
            "display_bounds": list(primary_bounds),
            "graphical_clipping_only": config.species_y_scale != "global_full",
        }
        reports["species_variability_full_range"] = {
            "path": paths.species_variability_full_range.as_posix(),
            "pages": _trace_report(
                con,
                schema,
                paths,
                species_groups,
                grouping_field=schema.species_field,
                output=paths.species_variability_full_range,
                config=config,
                global_bounds=global_full_bounds,
                display_mode="global_full",
                species_range_rows=range_rows,
            ),
            "display_mode": "global_full",
            "display_bounds": list(global_full_bounds),
            "graphical_clipping_only": False,
        }
        reports["species_quantiles"] = {
            "path": paths.species_quantile_report.as_posix(),
            "pages": _quantile_report(con, schema, paths, species_groups, config),
        }
        hierarchy_pages = _hierarchy_report(
            con,
            schema,
            paths,
            species_groups,
            config,
            global_robust_bounds,
        )
        if hierarchy_pages:
            reports["hierarchical_variability"] = {
                "path": paths.hierarchy_report.as_posix(),
                "pages": hierarchy_pages,
            }
        for field, label, output in (
            (schema.site_field, "site", paths.site_variability),
            (schema.flightline_field, "flightline", paths.flightline_variability),
        ):
            if field is None:
                continue
            groups = _ordered_groups(
                group_rows,
                grouping_field=field,
                order="count_desc",
            )
            reports[f"{label}_variability"] = {
                "path": output.as_posix(),
                "pages": _trace_report(
                    con,
                    schema,
                    paths,
                    groups,
                    grouping_field=field,
                    output=output,
                    config=config,
                    global_bounds=global_robust_bounds,
                    display_mode="global_robust",
                ),
            }
    _register_outputs(con, paths)
    output_sizes = {
        key: Path(value["path"]).stat().st_size for key, value in reports.items()
    }
    metadata = {
        "schema_version": SPECTRAL_LIBRARY_SCHEMA_VERSION,
        "analysis": "spectral_library_variability",
        "analysis_run_id": analysis_run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "spectralbridge_version": _spectralbridge_version(),
        "source_data_policy": "read_only_in_place",
        "source": schema.source.as_posix(),
        "source_signature_sha256": schema.source_signature_sha256,
        "schema": schema.to_dict(),
        "configuration": asdict(config),
        "visualization_validity": _visualization_validity_policy(schema, config),
        "report_cost": _report_cost_from_group_rows(schema, config, group_rows),
        "plot_ranges": range_metadata,
        "extreme_spectra": {
            "path": paths.extreme_spectra.as_posix(),
            "row_count": len(extreme_rows),
            "maximum_rows_per_species": config.max_extreme_spectra_per_species,
            "bounded_ranked_output": True,
        },
        "quantile_method": "DuckDB approx_quantile in bounded spectral-band batches",
        "trace_alpha_rule": "min(0.03, max(0.003, 0.2 / sqrt(rendered_trace_count)))",
        "trace_layer_rasterized": True,
        "sampling": {
            "enabled": config.max_traces_per_group is not None,
            "maximum_traces_per_group": config.max_traces_per_group,
            "seed": config.sampling_seed,
            "method": "deterministic DuckDB hash order" if config.max_traces_per_group else None,
        },
        "observation_count": schema.row_count,
        "valid_observation_count": sum(
            row["valid_spectrum_count"]
            for row in group_rows
            if row["grouping_field"] == schema.species_field
        ),
        "species_count": len(species_summary),
        "species_order": [row["group_value"] for row in species_groups],
        "wavelength_range_nm": [min(schema.wavelengths_nm), max(schema.wavelengths_nm)],
        "reports": reports,
        "report_sizes_bytes": output_sizes,
        "compact_outputs": {
            "species_summary": paths.species_summary.as_posix(),
            "species_band_summary": paths.species_band_summary.as_posix(),
            "species_quantiles": paths.species_quantiles.as_posix(),
            "species_median_spectra": paths.species_medians.as_posix(),
            "group_counts": paths.group_counts.as_posix(),
            "species_plot_ranges": paths.species_plot_ranges.as_posix(),
            "extreme_spectra": paths.extreme_spectra.as_posix(),
        },
        "interpretation": (
            "Low-alpha overplotting is a qualitative spectral trace density, "
            "not a normalized probability density. Robust-range clipping is "
            "graphical only; analytical summaries and the full-range audit preserve outliers."
        ),
    }
    write_json_atomic(paths.metadata, metadata)
    return metadata


def _spectralbridge_version() -> str:
    import spectralbridge

    return spectralbridge.__version__


__all__ = [
    "DEFAULT_QUANTILES",
    "SPECTRAL_LIBRARY_SCHEMA_VERSION",
    "SpectralBand",
    "SpectralLibraryPaths",
    "SpectralLibraryPlotConfig",
    "SpectralLibrarySchema",
    "inspect_spectral_library",
    "inspect_spectral_library_preflight",
    "iter_group_spectra",
    "run_spectral_library_analysis",
    "trace_alpha",
]
