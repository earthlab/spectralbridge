"""Shared projected-query helpers for bulk analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import duckdb

from ..dataset import observation_columns, quote_identifier
from ..registry import DEFAULT_PRODUCT_REGISTRY, TranslationPair


@dataclass(frozen=True)
class PairSpec:
    translation_pair: str
    source_sensor: str
    target_sensor: str
    band_index: int
    source_band_index: int
    target_band_index: int
    x_column: str
    y_column: str
    error_columns: tuple[str, ...]

    @property
    def micasense_sensor(self) -> str:
        """Compatibility alias for the former source-sensor field."""

        return self.source_sensor

    @property
    def landsat_sensor(self) -> str:
        """Compatibility alias for the former target-sensor field."""

        return self.target_sensor


def band_map(columns: Sequence[str]) -> dict[str, set[int]]:
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


def available_pair_specs(
    con: duckdb.DuckDBPyConnection,
    translation_pairs: Sequence[TranslationPair] | None = None,
) -> list[PairSpec]:
    columns = observation_columns(con)
    column_set = set(columns)
    mapped = band_map(columns)
    result: list[PairSpec] = []
    pairs = translation_pairs or DEFAULT_PRODUCT_REGISTRY.translation_pairs
    for pair in pairs:
        if pair.band_pairs:
            matched_bands = pair.band_pairs
        else:
            common = sorted(
                mapped.get(pair.source_sensor, set())
                & mapped.get(pair.target_sensor, set())
            )
            matched_bands = tuple((index, index) for index in common)
        for pair_band_index, (source_band, target_band) in enumerate(
            matched_bands, start=1
        ):
            x_column = f"{pair.source_sensor}_band_{source_band}"
            y_column = f"{pair.target_sensor}_band_{target_band}"
            if x_column not in column_set or y_column not in column_set:
                continue
            errors = tuple(
                column
                for label, band_index in (
                    (pair.source_sensor, source_band),
                    (pair.target_sensor, target_band),
                )
                for column in _possible_error_columns(label, band_index)
                if column in column_set
            )
            result.append(
                PairSpec(
                    translation_pair=pair.key,
                    source_sensor=pair.source_sensor,
                    target_sensor=pair.target_sensor,
                    band_index=pair_band_index,
                    source_band_index=source_band,
                    target_band_index=target_band,
                    x_column=x_column,
                    y_column=y_column,
                    error_columns=errors,
                )
            )
    return result


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def valid_pair_cte(spec: PairSpec, minimum_reflectance: float) -> str:
    """Projected valid-pair CTE shared by all regression levels."""

    error_filter = "".join(
        " AND COALESCE(TRY_CAST("
        + quote_identifier(column)
        + " AS DOUBLE), 0) = 0"
        for column in spec.error_columns
    )
    x_column = quote_identifier(spec.x_column)
    y_column = quote_identifier(spec.y_column)
    threshold = repr(float(minimum_reflectance))
    return f"""
        candidate AS (
            SELECT
                TRY_CAST({x_column} AS DOUBLE) AS x,
                TRY_CAST({y_column} AS DOUBLE) AS y,
                bulk_source_id,
                bulk_flightline_id,
                bulk_site,
                bulk_acquisition_date
            FROM bulk_observations
            WHERE TRUE {error_filter}
        ),
        valid AS (
            SELECT * FROM candidate
            WHERE x IS NOT NULL AND y IS NOT NULL
              AND isfinite(x) AND isfinite(y)
              AND x >= {threshold} AND y >= {threshold}
        )
    """


def pair_literals(spec: PairSpec) -> str:
    return ", ".join(
        (
            f"{sql_literal(spec.translation_pair)} AS translation_pair",
            f"{sql_literal(spec.source_sensor)} AS source_sensor",
            f"{sql_literal(spec.target_sensor)} AS target_sensor",
            f"{spec.source_band_index} AS source_band_index",
            f"{spec.target_band_index} AS target_band_index",
            f"{sql_literal(spec.micasense_sensor)} AS micasense_sensor",
            f"{sql_literal(spec.landsat_sensor)} AS landsat_sensor",
            f"{spec.band_index} AS band_index",
            f"{sql_literal(spec.x_column)} AS x_column",
            f"{sql_literal(spec.y_column)} AS y_column",
        )
    )


__all__ = [
    "PairSpec",
    "available_pair_specs",
    "band_map",
    "pair_literals",
    "sql_literal",
    "valid_pair_cte",
]
