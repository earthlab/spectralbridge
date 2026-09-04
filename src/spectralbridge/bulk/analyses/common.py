"""Shared projected-query helpers for bulk analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import duckdb

from spectralbridge.sensor_pairs import MICASENSE_LANDSAT_PAIRS

from ..dataset import observation_columns, quote_identifier


@dataclass(frozen=True)
class PairSpec:
    micasense_sensor: str
    landsat_sensor: str
    band_index: int
    x_column: str
    y_column: str
    error_columns: tuple[str, ...]


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


def available_pair_specs(con: duckdb.DuckDBPyConnection) -> list[PairSpec]:
    columns = observation_columns(con)
    column_set = set(columns)
    mapped = band_map(columns)
    result: list[PairSpec] = []
    for micasense_sensor, landsat_sensors in MICASENSE_LANDSAT_PAIRS.items():
        for landsat_sensor in landsat_sensors:
            common = sorted(
                mapped.get(micasense_sensor, set())
                & mapped.get(landsat_sensor, set())
            )
            for band_index in common:
                errors = tuple(
                    column
                    for label in (micasense_sensor, landsat_sensor)
                    for column in _possible_error_columns(label, band_index)
                    if column in column_set
                )
                result.append(
                    PairSpec(
                        micasense_sensor=micasense_sensor,
                        landsat_sensor=landsat_sensor,
                        band_index=band_index,
                        x_column=f"{micasense_sensor}_band_{band_index}",
                        y_column=f"{landsat_sensor}_band_{band_index}",
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
