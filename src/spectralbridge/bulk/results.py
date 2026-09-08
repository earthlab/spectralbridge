"""Interpret completed bulk translations from compact result tables only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .provenance import signature_sha256, write_json_atomic, write_text_atomic


BULK_RESULTS_SCHEMA_VERSION = 1
_GLOBAL_LEVELS = ("pixel_pooled", "flightline_balanced", "site_balanced")
_LEVEL_LABELS = {
    "pixel_pooled": "Pixel pooled",
    "flightline_balanced": "Flightline balanced",
    "site_balanced": "Site balanced",
}
_IDENTITY_COLUMNS = (
    "translation_pair",
    "source_sensor",
    "target_sensor",
    "source_band_index",
    "target_band_index",
    "band_index",
)


@dataclass(frozen=True)
class BulkResultsConfig:
    """Configurable review criteria for compact bulk translation results.

    Thresholds are report-screening defaults, not scientific acceptance
    criteria. A result that triggers no warning is not automatically approved
    for universal calibration or extrapolation beyond the evaluated domain.
    """

    representative_source_value: float | None = None
    r2_review_threshold: float = 0.90
    absolute_correction_review_threshold_pct: float = 20.0
    weighting_slope_spread_review_threshold: float = 0.05
    flightline_slope_iqr_review_threshold: float = 0.05
    site_slope_range_review_threshold: float = 0.05
    loso_r2_review_threshold: float = 0.80
    correction_denominator_floor: float = 1.0e-8
    figure_dpi: int = 150

    def validate(self) -> None:
        if self.representative_source_value is not None and not math.isfinite(
            self.representative_source_value
        ):
            raise ValueError("representative_source_value must be finite or None")
        for name, value in (
            ("r2_review_threshold", self.r2_review_threshold),
            ("loso_r2_review_threshold", self.loso_r2_review_threshold),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and between zero and one")
        for name, value in (
            (
                "absolute_correction_review_threshold_pct",
                self.absolute_correction_review_threshold_pct,
            ),
            (
                "weighting_slope_spread_review_threshold",
                self.weighting_slope_spread_review_threshold,
            ),
            (
                "flightline_slope_iqr_review_threshold",
                self.flightline_slope_iqr_review_threshold,
            ),
            (
                "site_slope_range_review_threshold",
                self.site_slope_range_review_threshold,
            ),
            ("correction_denominator_floor", self.correction_denominator_floor),
        ):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.figure_dpi < 72:
            raise ValueError("figure_dpi must be at least 72")


@dataclass(frozen=True)
class BulkResultsPaths:
    """Canonical compact inputs and interpretation outputs for one bulk run."""

    bulk_output: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "bulk_output", Path(self.bulk_output))

    @property
    def manifest(self) -> Path:
        return self.bulk_output / "catalog" / "bulk_manifest.json"

    @property
    def candidates(self) -> Path:
        return self.bulk_output / "coefficients" / "candidate_translation_coefficients.parquet"

    @property
    def per_flightline(self) -> Path:
        return self.bulk_output / "analyses" / "sensor_translation" / "per_flightline.parquet"

    @property
    def per_site(self) -> Path:
        return self.bulk_output / "analyses" / "sensor_translation" / "per_site.parquet"

    @property
    def loso(self) -> Path:
        return self.bulk_output / "analyses" / "leave_one_site_out" / "leave_one_site_out.parquet"

    @property
    def analysis_dir(self) -> Path:
        return self.bulk_output / "analyses" / "bulk_results"

    @property
    def figures_dir(self) -> Path:
        return self.bulk_output / "figures" / "bulk_results"

    @property
    def report_dir(self) -> Path:
        return self.bulk_output / "reports" / "bulk_results"

    @property
    def pair_band_summary(self) -> Path:
        return self.analysis_dir / "pair_band_summary.parquet"

    @property
    def weighting_comparison(self) -> Path:
        return self.analysis_dir / "weighting_comparison.parquet"

    @property
    def flightline_stability(self) -> Path:
        return self.analysis_dir / "flightline_stability.parquet"

    @property
    def site_stability(self) -> Path:
        return self.analysis_dir / "site_stability.parquet"

    @property
    def loso_transferability(self) -> Path:
        return self.analysis_dir / "loso_transferability.parquet"

    @property
    def attention_flags(self) -> Path:
        return self.analysis_dir / "attention_flags.parquet"

    @property
    def metadata(self) -> Path:
        return self.analysis_dir / "bulk_results_summary.json"

    @property
    def coefficient_figure(self) -> Path:
        return self.figures_dir / "translation_coefficients_and_fit.png"

    @property
    def correction_figure(self) -> Path:
        return self.figures_dir / "fitted_correction_magnitude.png"

    @property
    def transferability_figure(self) -> Path:
        return self.figures_dir / "stability_and_transferability.png"

    @property
    def report(self) -> Path:
        return self.report_dir / "bulk_translation_results.md"

    @property
    def required_inputs(self) -> tuple[Path, ...]:
        return (
            self.manifest,
            self.candidates,
            self.per_flightline,
            self.per_site,
            self.loso,
        )


_WEIGHTING_SCHEMA = pa.schema(
    [
        *(pa.field(name, pa.string()) for name in _IDENTITY_COLUMNS[:3]),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("band_index", pa.int32()),
        ("analysis_level", pa.string()),
        ("status", pa.string()),
        ("slope", pa.float64()),
        ("intercept", pa.float64()),
        ("r2", pa.float64()),
        ("rmse", pa.float64()),
        ("mae", pa.float64()),
        ("sample_count", pa.int64()),
        ("flightline_count", pa.int64()),
        ("site_count", pa.int64()),
        ("representative_source_value", pa.float64()),
        ("representative_source_value_method", pa.string()),
        ("fitted_target_value", pa.float64()),
        ("fitted_correction", pa.float64()),
        ("fitted_correction_percent", pa.float64()),
        ("slope_minus_identity", pa.float64()),
    ]
)

_STABILITY_SCHEMA = pa.schema(
    [
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("band_index", pa.int32()),
        ("fit_count", pa.int64()),
        ("ok_fit_count", pa.int64()),
        ("slope_min", pa.float64()),
        ("slope_q25", pa.float64()),
        ("slope_median", pa.float64()),
        ("slope_q75", pa.float64()),
        ("slope_max", pa.float64()),
        ("slope_iqr", pa.float64()),
        ("slope_range", pa.float64()),
        ("r2_min", pa.float64()),
        ("r2_median", pa.float64()),
        ("below_r2_review_count", pa.int64()),
        ("weakest_identity", pa.string()),
        ("weakest_r2", pa.float64()),
    ]
)

_LOSO_SCHEMA = pa.schema(
    [
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("band_index", pa.int32()),
        ("evaluation_count", pa.int64()),
        ("ok_evaluation_count", pa.int64()),
        ("held_out_r2_min", pa.float64()),
        ("held_out_r2_median", pa.float64()),
        ("held_out_rmse_max", pa.float64()),
        ("held_out_mae_max", pa.float64()),
        ("absolute_held_out_bias_max", pa.float64()),
        ("training_slope_min", pa.float64()),
        ("training_slope_max", pa.float64()),
        ("training_slope_range", pa.float64()),
        ("below_r2_review_count", pa.int64()),
        ("weakest_held_out_site", pa.string()),
        ("weakest_held_out_r2", pa.float64()),
    ]
)

_FLAG_SCHEMA = pa.schema(
    [
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("band_index", pa.int32()),
        ("flag_code", pa.string()),
        ("analysis_scope", pa.string()),
        ("metric", pa.string()),
        ("observed_value", pa.float64()),
        ("review_threshold", pa.float64()),
        ("comparison", pa.string()),
        ("detail", pa.string()),
    ]
)

_PAIR_SUMMARY_SCHEMA = pa.schema(
    [
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("band_index", pa.int32()),
        ("representative_source_value", pa.float64()),
        ("representative_source_value_method", pa.string()),
        ("sample_count", pa.int64()),
        ("flightline_count", pa.int64()),
        ("site_count", pa.int64()),
        ("candidate_level_count", pa.int64()),
        ("candidate_ok_count", pa.int64()),
        ("candidate_slope_min", pa.float64()),
        ("candidate_slope_max", pa.float64()),
        ("candidate_slope_spread", pa.float64()),
        ("candidate_r2_min", pa.float64()),
        ("candidate_r2_median", pa.float64()),
        ("maximum_absolute_fitted_correction_percent", pa.float64()),
        ("flightline_fit_count", pa.int64()),
        ("flightline_slope_iqr", pa.float64()),
        ("flightline_r2_min", pa.float64()),
        ("weakest_flightline_id", pa.string()),
        ("site_fit_count", pa.int64()),
        ("site_slope_range", pa.float64()),
        ("site_r2_min", pa.float64()),
        ("weakest_site", pa.string()),
        ("loso_evaluation_count", pa.int64()),
        ("loso_ok_evaluation_count", pa.int64()),
        ("loso_held_out_r2_min", pa.float64()),
        ("weakest_loso_site", pa.string()),
        ("warning_count", pa.int64()),
        ("warning_codes_json", pa.string()),
        ("screening_status", pa.string()),
    ]
)


_REQUIRED_COLUMNS = {
    "candidates": {
        *_IDENTITY_COLUMNS,
        "analysis_level",
        "status",
        "slope",
        "intercept",
        "r2",
        "rmse",
        "mae",
        "sample_count",
        "flightline_count",
        "site_count",
        "x_mean",
    },
    "per_flightline": {
        *_IDENTITY_COLUMNS,
        "flightline_id",
        "site",
        "status",
        "slope",
        "r2",
    },
    "per_site": {
        *_IDENTITY_COLUMNS,
        "site",
        "status",
        "slope",
        "r2",
    },
    "loso": {
        *_IDENTITY_COLUMNS,
        "held_out_site",
        "status",
        "training_slope",
        "held_out_r2",
        "held_out_rmse",
        "held_out_mae",
        "held_out_bias",
    },
}


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _key(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["translation_pair"]), int(row["band_index"])


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "translation_pair": str(row["translation_pair"]),
        "source_sensor": str(row["source_sensor"]),
        "target_sensor": str(row["target_sensor"]),
        "source_band_index": int(row["source_band_index"]),
        "target_band_index": int(row["target_band_index"]),
        "band_index": int(row["band_index"]),
    }


def _read_compact(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing completed bulk {label} table: {path}")
    try:
        table = pq.read_table(path)
    except Exception as exc:
        raise ValueError(f"Unreadable completed bulk {label} table: {path}") from exc
    missing = sorted(_REQUIRED_COLUMNS[label] - set(table.column_names))
    if missing:
        raise ValueError(
            f"Completed bulk {label} table is missing required columns: {missing}"
        )
    return table.to_pylist()


def _file_signature(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "path": path.resolve().as_posix(),
        "size_bytes": int(stat.st_size),
        "modified_time_ns": int(stat.st_mtime_ns),
        "sha256": digest.hexdigest(),
    }


def _group(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    result: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(_key(row), []).append(row)
    return result


def _distribution(values: Iterable[Any]) -> dict[str, float | None]:
    selected = np.asarray(
        [value for item in values if (value := _finite(item)) is not None],
        dtype=np.float64,
    )
    if selected.size == 0:
        return {
            "min": None,
            "q25": None,
            "median": None,
            "q75": None,
            "max": None,
            "iqr": None,
            "range": None,
        }
    q25, median, q75 = np.quantile(selected, (0.25, 0.5, 0.75))
    minimum = float(selected.min())
    maximum = float(selected.max())
    return {
        "min": minimum,
        "q25": float(q25),
        "median": float(median),
        "q75": float(q75),
        "max": maximum,
        "iqr": float(q75 - q25),
        "range": float(maximum - minimum),
    }


def _worst_r2(
    rows: Sequence[dict[str, Any]], identity_field: str, r2_field: str
) -> tuple[str | None, float | None]:
    finite = [row for row in rows if _finite(row.get(r2_field)) is not None]
    if not finite:
        return None, None
    worst = min(
        finite,
        key=lambda row: (
            float(row[r2_field]),
            str(row.get(identity_field) or ""),
        ),
    )
    return str(worst.get(identity_field) or "") or None, float(worst[r2_field])


def _summarize_stability(
    rows: Sequence[dict[str, Any]],
    *,
    identity_field: str,
    r2_threshold: float,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for _, group in sorted(_group(rows).items()):
        template = group[0]
        ok = [
            row
            for row in group
            if row.get("status") == "ok" and _finite(row.get("slope")) is not None
        ]
        slope = _distribution(row.get("slope") for row in ok)
        r2 = _distribution(row.get("r2") for row in ok)
        weakest_identity, weakest_r2 = _worst_r2(ok, identity_field, "r2")
        summaries.append(
            {
                **_identity(template),
                "fit_count": len(group),
                "ok_fit_count": len(ok),
                "slope_min": slope["min"],
                "slope_q25": slope["q25"],
                "slope_median": slope["median"],
                "slope_q75": slope["q75"],
                "slope_max": slope["max"],
                "slope_iqr": slope["iqr"],
                "slope_range": slope["range"],
                "r2_min": r2["min"],
                "r2_median": r2["median"],
                "below_r2_review_count": sum(
                    value < r2_threshold
                    for row in ok
                    if (value := _finite(row.get("r2"))) is not None
                ),
                "weakest_identity": weakest_identity,
                "weakest_r2": weakest_r2,
            }
        )
    return summaries


def _summarize_loso(
    rows: Sequence[dict[str, Any]], config: BulkResultsConfig
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for _, group in sorted(_group(rows).items()):
        template = group[0]
        ok = [row for row in group if row.get("status") == "ok"]
        r2 = _distribution(row.get("held_out_r2") for row in ok)
        slope = _distribution(row.get("training_slope") for row in ok)
        rmse = _distribution(row.get("held_out_rmse") for row in ok)
        mae = _distribution(row.get("held_out_mae") for row in ok)
        absolute_bias = _distribution(
            abs(value)
            for row in ok
            if (value := _finite(row.get("held_out_bias"))) is not None
        )
        weakest_site, weakest_r2 = _worst_r2(
            ok, "held_out_site", "held_out_r2"
        )
        summaries.append(
            {
                **_identity(template),
                "evaluation_count": len(group),
                "ok_evaluation_count": len(ok),
                "held_out_r2_min": r2["min"],
                "held_out_r2_median": r2["median"],
                "held_out_rmse_max": rmse["max"],
                "held_out_mae_max": mae["max"],
                "absolute_held_out_bias_max": absolute_bias["max"],
                "training_slope_min": slope["min"],
                "training_slope_max": slope["max"],
                "training_slope_range": slope["range"],
                "below_r2_review_count": sum(
                    value < config.loso_r2_review_threshold
                    for row in ok
                    if (value := _finite(row.get("held_out_r2"))) is not None
                ),
                "weakest_held_out_site": weakest_site,
                "weakest_held_out_r2": weakest_r2,
            }
        )
    return summaries


def _representative_value(
    rows: Sequence[dict[str, Any]], config: BulkResultsConfig
) -> tuple[float | None, str]:
    if config.representative_source_value is not None:
        return float(config.representative_source_value), "configured_common_value"
    pooled = next(
        (row for row in rows if row.get("analysis_level") == "pixel_pooled"),
        None,
    )
    if pooled is not None and (value := _finite(pooled.get("x_mean"))) is not None:
        return value, "pixel_pooled_source_mean"
    for row in rows:
        if (value := _finite(row.get("x_mean"))) is not None:
            return value, "first_available_candidate_source_mean"
    return None, "unavailable"


def _weighting_rows(
    candidates: Sequence[dict[str, Any]], config: BulkResultsConfig
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for _, group in sorted(_group(candidates).items()):
        x_reference, method = _representative_value(group, config)
        for row in sorted(
            group,
            key=lambda item: _GLOBAL_LEVELS.index(str(item["analysis_level"]))
            if item.get("analysis_level") in _GLOBAL_LEVELS
            else len(_GLOBAL_LEVELS),
        ):
            slope = _finite(row.get("slope"))
            intercept = _finite(row.get("intercept"))
            fitted = (
                slope * x_reference + intercept
                if slope is not None
                and intercept is not None
                and x_reference is not None
                else None
            )
            correction = fitted - x_reference if fitted is not None else None
            correction_pct = (
                100.0 * correction / x_reference
                if correction is not None
                and x_reference is not None
                and abs(x_reference) > config.correction_denominator_floor
                else None
            )
            result.append(
                {
                    **_identity(row),
                    "analysis_level": str(row.get("analysis_level") or ""),
                    "status": str(row.get("status") or ""),
                    "slope": slope,
                    "intercept": intercept,
                    "r2": _finite(row.get("r2")),
                    "rmse": _finite(row.get("rmse")),
                    "mae": _finite(row.get("mae")),
                    "sample_count": _integer(row.get("sample_count")),
                    "flightline_count": _integer(row.get("flightline_count")),
                    "site_count": _integer(row.get("site_count")),
                    "representative_source_value": x_reference,
                    "representative_source_value_method": method,
                    "fitted_target_value": fitted,
                    "fitted_correction": correction,
                    "fitted_correction_percent": correction_pct,
                    "slope_minus_identity": slope - 1.0 if slope is not None else None,
                }
            )
    return result


def _flag(
    template: dict[str, Any],
    code: str,
    scope: str,
    metric: str,
    value: float,
    threshold: float,
    comparison: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "translation_pair": template["translation_pair"],
        "source_sensor": template["source_sensor"],
        "target_sensor": template["target_sensor"],
        "source_band_index": template["source_band_index"],
        "target_band_index": template["target_band_index"],
        "band_index": template["band_index"],
        "flag_code": code,
        "analysis_scope": scope,
        "metric": metric,
        "observed_value": value,
        "review_threshold": threshold,
        "comparison": comparison,
        "detail": detail,
    }


def _build_pair_summaries(
    weighting: Sequence[dict[str, Any]],
    flightline: Sequence[dict[str, Any]],
    site: Sequence[dict[str, Any]],
    loso: Sequence[dict[str, Any]],
    config: BulkResultsConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    weighting_by_key = _group(weighting)
    flightline_by_key = {_key(row): row for row in flightline}
    site_by_key = {_key(row): row for row in site}
    loso_by_key = {_key(row): row for row in loso}
    summaries: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    for key, rows in sorted(weighting_by_key.items()):
        template = rows[0]
        ok_candidates = [row for row in rows if row.get("status") == "ok"]
        valid_slopes = [
            value
            for row in ok_candidates
            if (value := _finite(row.get("slope"))) is not None
        ]
        valid_r2 = [
            value
            for row in ok_candidates
            if (value := _finite(row.get("r2"))) is not None
        ]
        correction_pct = [
            abs(value)
            for row in ok_candidates
            if (value := _finite(row.get("fitted_correction_percent"))) is not None
        ]
        candidate_slope_min = min(valid_slopes, default=None)
        candidate_slope_max = max(valid_slopes, default=None)
        candidate_slope_spread = (
            candidate_slope_max - candidate_slope_min
            if candidate_slope_min is not None and candidate_slope_max is not None
            else None
        )
        candidate_r2_min = min(valid_r2, default=None)
        candidate_r2_median = float(np.median(valid_r2)) if valid_r2 else None
        max_abs_correction = max(correction_pct, default=None)
        flight = flightline_by_key.get(key, {})
        site_row = site_by_key.get(key, {})
        loso_row = loso_by_key.get(key, {})

        present_levels = {
            str(row.get("analysis_level"))
            for row in rows
            if row.get("analysis_level") in _GLOBAL_LEVELS
        }
        if present_levels != set(_GLOBAL_LEVELS):
            missing_levels = sorted(set(_GLOBAL_LEVELS) - present_levels)
            flags.append(
                _flag(
                    template,
                    "incomplete_candidate_weightings",
                    "candidate_weightings",
                    "available_weighting_fraction",
                    len(present_levels) / len(_GLOBAL_LEVELS),
                    1.0,
                    "below",
                    "Missing candidate weighting levels: "
                    + (", ".join(missing_levels) or "none; unexpected duplicates present"),
                )
            )
        if len(ok_candidates) < len(rows):
            flags.append(
                _flag(
                    template,
                    "incomplete_candidate_fit",
                    "candidate_weightings",
                    "ok_candidate_fraction",
                    len(ok_candidates) / max(1, len(rows)),
                    1.0,
                    "below",
                    "At least one candidate weighting did not have status 'ok'.",
                )
            )
        if candidate_r2_min is not None and candidate_r2_min < config.r2_review_threshold:
            flags.append(
                _flag(
                    template,
                    "weak_global_fit",
                    "candidate_weightings",
                    "minimum_r2",
                    candidate_r2_min,
                    config.r2_review_threshold,
                    "below",
                    "At least one global weighting has R-squared below the configured review threshold.",
                )
            )
        if (
            max_abs_correction is not None
            and max_abs_correction
            > config.absolute_correction_review_threshold_pct
        ):
            flags.append(
                _flag(
                    template,
                    "large_fitted_correction",
                    "candidate_weightings",
                    "maximum_absolute_fitted_correction_percent",
                    max_abs_correction,
                    config.absolute_correction_review_threshold_pct,
                    "above",
                    "At least one weighting implies a large fitted correction at the common representative source value.",
                )
            )
        if (
            candidate_slope_spread is not None
            and candidate_slope_spread
            > config.weighting_slope_spread_review_threshold
        ):
            flags.append(
                _flag(
                    template,
                    "weighting_dependence",
                    "candidate_weightings",
                    "candidate_slope_spread",
                    candidate_slope_spread,
                    config.weighting_slope_spread_review_threshold,
                    "above",
                    "Pixel-pooled, flightline-balanced, and site-balanced slopes differ enough to require weighting review.",
                )
            )
        flight_iqr = _finite(flight.get("slope_iqr"))
        if (
            flight_iqr is not None
            and flight_iqr > config.flightline_slope_iqr_review_threshold
        ):
            flags.append(
                _flag(
                    template,
                    "flightline_heterogeneity",
                    "per_flightline",
                    "slope_iqr",
                    flight_iqr,
                    config.flightline_slope_iqr_review_threshold,
                    "above",
                    "The middle half of per-flightline slopes spans more than the configured review threshold.",
                )
            )
        flight_r2_min = _finite(flight.get("r2_min"))
        expected_flightlines = max(
            (_integer(row.get("flightline_count")) for row in rows), default=0
        )
        if _integer(flight.get("ok_fit_count")) < expected_flightlines:
            flags.append(
                _flag(
                    template,
                    "incomplete_flightline_fits",
                    "per_flightline",
                    "ok_fit_fraction",
                    _integer(flight.get("ok_fit_count"))
                    / max(1, expected_flightlines),
                    1.0,
                    "below",
                    "One or more expected per-flightline fits are missing or not 'ok'.",
                )
            )
        if flight_r2_min is not None and flight_r2_min < config.r2_review_threshold:
            flags.append(
                _flag(
                    template,
                    "weak_flightline_fit",
                    "per_flightline",
                    "minimum_r2",
                    flight_r2_min,
                    config.r2_review_threshold,
                    "below",
                    f"Weakest flightline: {flight.get('weakest_identity') or 'unknown'}.",
                )
            )
        site_range = _finite(site_row.get("slope_range"))
        if (
            site_range is not None
            and site_range > config.site_slope_range_review_threshold
        ):
            flags.append(
                _flag(
                    template,
                    "site_dependence",
                    "per_site",
                    "slope_range",
                    site_range,
                    config.site_slope_range_review_threshold,
                    "above",
                    "Per-site slopes span more than the configured review threshold.",
                )
            )
        site_r2_min = _finite(site_row.get("r2_min"))
        expected_sites = max(
            (_integer(row.get("site_count")) for row in rows), default=0
        )
        if _integer(site_row.get("ok_fit_count")) < expected_sites:
            flags.append(
                _flag(
                    template,
                    "incomplete_site_fits",
                    "per_site",
                    "ok_fit_fraction",
                    _integer(site_row.get("ok_fit_count")) / max(1, expected_sites),
                    1.0,
                    "below",
                    "One or more expected per-site fits are missing or not 'ok'.",
                )
            )
        if site_r2_min is not None and site_r2_min < config.r2_review_threshold:
            flags.append(
                _flag(
                    template,
                    "weak_site_fit",
                    "per_site",
                    "minimum_r2",
                    site_r2_min,
                    config.r2_review_threshold,
                    "below",
                    f"Weakest site: {site_row.get('weakest_identity') or 'unknown'}.",
                )
            )
        loso_r2_min = _finite(loso_row.get("held_out_r2_min"))
        if (
            loso_r2_min is not None
            and loso_r2_min < config.loso_r2_review_threshold
        ):
            flags.append(
                _flag(
                    template,
                    "weak_loso_transferability",
                    "leave_one_site_out",
                    "minimum_held_out_r2",
                    loso_r2_min,
                    config.loso_r2_review_threshold,
                    "below",
                    f"Weakest held-out site: {loso_row.get('weakest_held_out_site') or 'unknown'}.",
                )
            )
        expected_loso = expected_sites if expected_sites > 1 else 0
        if _integer(loso_row.get("ok_evaluation_count")) < expected_loso:
            flags.append(
                _flag(
                    template,
                    "incomplete_loso_evaluation",
                    "leave_one_site_out",
                    "ok_evaluation_fraction",
                    (
                        _integer(loso_row.get("ok_evaluation_count"))
                        / max(1, expected_loso)
                    ),
                    1.0,
                    "below",
                    "One or more expected held-out-site evaluations are missing or not 'ok'.",
                )
            )

        key_flags = [row for row in flags if _key(row) == key]
        summaries.append(
            {
                **_identity(template),
                "representative_source_value": _finite(
                    template.get("representative_source_value")
                ),
                "representative_source_value_method": str(
                    template.get("representative_source_value_method") or "unavailable"
                ),
                "sample_count": max(
                    (_integer(row.get("sample_count")) for row in rows), default=0
                ),
                "flightline_count": max(
                    (_integer(row.get("flightline_count")) for row in rows), default=0
                ),
                "site_count": max(
                    (_integer(row.get("site_count")) for row in rows), default=0
                ),
                "candidate_level_count": len(rows),
                "candidate_ok_count": len(ok_candidates),
                "candidate_slope_min": candidate_slope_min,
                "candidate_slope_max": candidate_slope_max,
                "candidate_slope_spread": candidate_slope_spread,
                "candidate_r2_min": candidate_r2_min,
                "candidate_r2_median": candidate_r2_median,
                "maximum_absolute_fitted_correction_percent": max_abs_correction,
                "flightline_fit_count": _integer(flight.get("fit_count")),
                "flightline_slope_iqr": flight_iqr,
                "flightline_r2_min": flight_r2_min,
                "weakest_flightline_id": flight.get("weakest_identity"),
                "site_fit_count": _integer(site_row.get("fit_count")),
                "site_slope_range": site_range,
                "site_r2_min": site_r2_min,
                "weakest_site": site_row.get("weakest_identity"),
                "loso_evaluation_count": _integer(loso_row.get("evaluation_count")),
                "loso_ok_evaluation_count": _integer(
                    loso_row.get("ok_evaluation_count")
                ),
                "loso_held_out_r2_min": loso_r2_min,
                "weakest_loso_site": loso_row.get("weakest_held_out_site"),
                "warning_count": len(key_flags),
                "warning_codes_json": json.dumps(
                    sorted({row["flag_code"] for row in key_flags})
                ),
                "screening_status": (
                    "review_required"
                    if key_flags
                    else "no_configured_warning_triggered"
                ),
            }
        )
    flags.sort(key=lambda row: (_key(row), row["flag_code"]))
    return summaries, flags


def _write_parquet(path: Path, rows: Sequence[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    table = pa.Table.from_pylist(list(rows), schema=schema)
    pq.write_table(table, temporary, compression="zstd")
    pq.read_schema(temporary)
    temporary.replace(path)


def _overview(
    manifest: dict[str, Any],
    weighting: Sequence[dict[str, Any]],
    pair_summaries: Sequence[dict[str, Any]],
    flightline_rows: Sequence[dict[str, Any]],
    site_rows: Sequence[dict[str, Any]],
    loso_rows: Sequence[dict[str, Any]],
    flags: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    successful = [row for row in weighting if row.get("status") == "ok"]
    slope = _distribution(row.get("slope") for row in successful)
    r2 = _distribution(row.get("r2") for row in successful)
    correction = _distribution(
        abs(value)
        for row in successful
        if (value := _finite(row.get("fitted_correction_percent"))) is not None
    )
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {}
    sites = sorted(
        {
            str(row["site"])
            for row in site_rows
            if row.get("site") not in (None, "")
        }
    )
    return {
        "analysis_run_id": manifest.get("analysis_run_id"),
        "accepted_flightlines": _integer(counts.get("accepted_flightlines")),
        "selected_observation_rows": _integer(counts.get("accepted_rows")),
        "sites": sites,
        "site_count": len(sites),
        "pair_band_count": len(pair_summaries),
        "candidate_coefficient_count": len(weighting),
        "successful_candidate_coefficient_count": len(successful),
        "per_flightline_fit_count": len(flightline_rows),
        "per_site_fit_count": len(site_rows),
        "leave_one_site_out_evaluation_count": len(loso_rows),
        "candidate_slope_median": slope["median"],
        "candidate_slope_min": slope["min"],
        "candidate_slope_max": slope["max"],
        "candidate_r2_median": r2["median"],
        "candidate_r2_min": r2["min"],
        "candidate_r2_max": r2["max"],
        "absolute_fitted_correction_percent_median": correction["median"],
        "absolute_fitted_correction_percent_max": correction["max"],
        "pair_bands_requiring_review": sum(
            row["screening_status"] == "review_required" for row in pair_summaries
        ),
        "attention_flag_count": len(flags),
    }


def _format(value: Any, digits: int = 4) -> str:
    numeric = _finite(value)
    return "not available" if numeric is None else f"{numeric:.{digits}f}"


def _labels(rows: Sequence[dict[str, Any]]) -> list[str]:
    return [f"{row['target_sensor']} B{row['target_band_index']}" for row in rows]


def _plot_value(value: Any) -> float:
    """Return a finite plotting value or NaN for a visible missing-data gap."""

    selected = _finite(value)
    return np.nan if selected is None else selected


def _save_figure(figure: Any, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.png")
    figure.savefig(temporary, dpi=dpi, bbox_inches="tight", facecolor="white")
    with temporary.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"Invalid PNG output: {temporary}")
    temporary.replace(path)


def _make_figures(
    paths: BulkResultsPaths,
    weighting: Sequence[dict[str, Any]],
    pair_summaries: Sequence[dict[str, Any]],
    flightline: Sequence[dict[str, Any]],
    site: Sequence[dict[str, Any]],
    loso: Sequence[dict[str, Any]],
    config: BulkResultsConfig,
) -> list[str]:
    from matplotlib.figure import Figure

    pair_keys = [_key(row) for row in pair_summaries]
    x = np.arange(len(pair_keys), dtype=np.float64)
    labels = _labels(pair_summaries)
    weighting_by_key = _group(weighting)

    figure = Figure(figsize=(max(11.0, len(x) * 0.42), 7.5), constrained_layout=True)
    axes = figure.subplots(2, 1, sharex=True)
    colors = ("#1F77B4", "#E07A1F", "#2A9D6F")
    for level, color in zip(_GLOBAL_LEVELS, colors):
        rows = {
            key: next(
                (row for row in weighting_by_key.get(key, []) if row["analysis_level"] == level),
                {},
            )
            for key in pair_keys
        }
        slopes = [_plot_value(rows[key].get("slope")) for key in pair_keys]
        r2 = [_plot_value(rows[key].get("r2")) for key in pair_keys]
        axes[0].plot(
            x,
            slopes,
            marker="o",
            linewidth=1.0,
            markersize=3.5,
            label=_LEVEL_LABELS[level],
            color=color,
        )
        axes[1].plot(
            x,
            r2,
            marker="o",
            linewidth=1.0,
            markersize=3.5,
            label=_LEVEL_LABELS[level],
            color=color,
        )
    axes[0].axhline(
        1.0,
        color="#30343B",
        linestyle="--",
        linewidth=0.9,
        label="Identity slope",
    )
    axes[0].set_ylabel("Slope")
    axes[0].set_title("Translation coefficients across weighting choices", loc="left")
    axes[1].set_ylabel("R-squared")
    axes[1].set_title("Fit strength does not establish interchangeability", loc="left")
    axes[1].axhline(
        config.r2_review_threshold,
        color="#8E4451",
        linestyle=":",
        linewidth=0.9,
        label="Review threshold",
    )
    axes[1].set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    for axis in axes:
        axis.grid(axis="y", color="#DCE3E8", linewidth=0.6)
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].legend(ncols=4, fontsize=8)
    _save_figure(figure, paths.coefficient_figure, config.figure_dpi)

    figure = Figure(figsize=(max(11.0, len(x) * 0.42), 5.4), constrained_layout=True)
    axis = figure.subplots()
    width = 0.24
    for offset, level, color in zip((-width, 0.0, width), _GLOBAL_LEVELS, colors):
        values = [
            _plot_value(
                next(
                    (
                        row.get("fitted_correction_percent")
                        for row in weighting_by_key.get(key, [])
                        if row["analysis_level"] == level
                    ),
                    None,
                )
            )
            for key in pair_keys
        ]
        axis.bar(
            x + offset,
            values,
            width=width,
            color=color,
            label=_LEVEL_LABELS[level],
        )
    axis.axhline(0.0, color="#30343B", linewidth=0.8)
    for threshold in (
        -config.absolute_correction_review_threshold_pct,
        config.absolute_correction_review_threshold_pct,
    ):
        axis.axhline(
            threshold,
            color="#8E4451",
            linestyle=":",
            linewidth=0.8,
        )
    axis.set_ylabel("Fitted correction at common source value (%)")
    axis.set_title("Correction direction and magnitude by weighting", loc="left")
    axis.set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    axis.grid(axis="y", color="#DCE3E8", linewidth=0.6)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(ncols=3, fontsize=8)
    _save_figure(figure, paths.correction_figure, config.figure_dpi)

    flightline_by_key = {_key(row): row for row in flightline}
    site_by_key = {_key(row): row for row in site}
    loso_by_key = {_key(row): row for row in loso}
    figure = Figure(figsize=(max(11.0, len(x) * 0.42), 8.0), constrained_layout=True)
    axes = figure.subplots(3, 1, sharex=True)
    axes[0].bar(
        x,
        [
            _plot_value(flightline_by_key.get(key, {}).get("slope_iqr"))
            for key in pair_keys
        ],
        color="#527DA4",
    )
    axes[0].set_ylabel("Slope IQR")
    axes[0].set_title("Per-flightline coefficient heterogeneity", loc="left")
    axes[0].axhline(
        config.flightline_slope_iqr_review_threshold,
        color="#8E4451",
        linestyle=":",
        linewidth=0.8,
    )
    axes[1].bar(
        x,
        [
            _plot_value(site_by_key.get(key, {}).get("slope_range"))
            for key in pair_keys
        ],
        color="#6E9F71",
    )
    axes[1].set_ylabel("Slope range")
    axes[1].set_title("Per-site coefficient dependence", loc="left")
    axes[1].axhline(
        config.site_slope_range_review_threshold,
        color="#8E4451",
        linestyle=":",
        linewidth=0.8,
    )
    axes[2].bar(
        x,
        [
            _plot_value(loso_by_key.get(key, {}).get("held_out_r2_min"))
            for key in pair_keys
        ],
        color="#C56B5D",
    )
    axes[2].set_ylabel("Worst held-out R-squared")
    axes[2].set_title("Leave-one-site-out transferability", loc="left")
    axes[2].axhline(
        config.loso_r2_review_threshold,
        color="#8E4451",
        linestyle=":",
        linewidth=0.8,
    )
    axes[2].set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    for axis in axes:
        axis.grid(axis="y", color="#DCE3E8", linewidth=0.6)
        axis.spines[["top", "right"]].set_visible(False)
    _save_figure(figure, paths.transferability_figure, config.figure_dpi)
    return [
        paths.coefficient_figure.as_posix(),
        paths.correction_figure.as_posix(),
        paths.transferability_figure.as_posix(),
    ]


def _markdown_report(
    overview: dict[str, Any],
    pair_summaries: Sequence[dict[str, Any]],
    flags: Sequence[dict[str, Any]],
    config: BulkResultsConfig,
    figure_paths: Sequence[str],
) -> str:
    figures = ""
    if figure_paths:
        figures = "\n## Figures\n\n" + "\n\n".join(
            f"![{Path(path).stem}](../../figures/bulk_results/{Path(path).name})"
            for path in figure_paths
        )
    rows = "\n".join(
        "| {target} B{band} | {slope} | {r2} | {correction} | {weighting} | {flightline} | {site} | {loso} | {status} |".format(
            target=row["target_sensor"],
            band=row["target_band_index"],
            slope=_format(row["candidate_slope_min"])
            + " to "
            + _format(row["candidate_slope_max"]),
            r2=_format(row["candidate_r2_min"]),
            correction=_format(row["maximum_absolute_fitted_correction_percent"], 2),
            weighting=_format(row["candidate_slope_spread"]),
            flightline=_format(row["flightline_slope_iqr"]),
            site=_format(row["site_slope_range"]),
            loso=_format(row["loso_held_out_r2_min"]),
            status=row["screening_status"],
        )
        for row in pair_summaries
    )
    warning_rows = "\n".join(
        f"| {row['target_sensor']} B{row['target_band_index']} | {row['flag_code']} | "
        f"{row['analysis_scope']} | {_format(row['observed_value'])} | "
        f"{row['comparison']} {_format(row['review_threshold'])} | {row['detail']} |"
        for row in flags
    ) or "| none | none | none | not applicable | not applicable | No configured warning triggered. |"
    return f"""# SpectralBridge bulk translation results

Analysis run: `{overview.get('analysis_run_id') or 'not recorded'}`

This report was calculated only from completed compact bulk-result tables. It
did not reopen source rasters, regenerate sufficient statistics, or create a
pixel-level cache.

## Collection and result counts

- Accepted flightlines: {overview['accepted_flightlines']:,}
- Sites ({overview['site_count']:,}): {', '.join(overview['sites']) or 'not available'}
- Selected observation rows represented by compact statistics: {overview['selected_observation_rows']:,}
- Translation pair-band combinations: {overview['pair_band_count']:,}
- Candidate coefficient rows: {overview['candidate_coefficient_count']:,}
- Successful candidate coefficient rows: {overview['successful_candidate_coefficient_count']:,}
- Per-flightline fits: {overview['per_flightline_fit_count']:,}
- Per-site fits: {overview['per_site_fit_count']:,}
- Leave-one-site-out evaluations: {overview['leave_one_site_out_evaluation_count']:,}

## Population overview

- Candidate slope median and range: {_format(overview['candidate_slope_median'])} ({_format(overview['candidate_slope_min'])} to {_format(overview['candidate_slope_max'])})
- Candidate R-squared median and range: {_format(overview['candidate_r2_median'])} ({_format(overview['candidate_r2_min'])} to {_format(overview['candidate_r2_max'])})
- Median absolute fitted correction at each pair-band's common representative source value: {_format(overview['absolute_fitted_correction_percent_median'], 2)}%
- Largest absolute fitted correction at a representative source value: {_format(overview['absolute_fitted_correction_percent_max'], 2)}%
- Pair-bands requiring review: {overview['pair_bands_requiring_review']:,} of {overview['pair_band_count']:,}

High R-squared indicates a strong fitted relationship; it does not establish
sensor interchangeability. Compare weighting choices, per-flightline and
per-site distributions, and leave-one-site-out performance before promoting a
coefficient. Corrections are evaluated at one common source value per pair-band
(the pixel-pooled source mean unless explicitly configured), so weighting
differences are compared at the same reflectance.

## Pair-band screening summary

| Target band | Candidate slope range | Minimum candidate R-squared | Maximum absolute correction (%) | Weighting slope spread | Flightline slope IQR | Site slope range | Worst LOSO R-squared | Screening status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{rows}

## Attention flags

| Target band | Flag | Scope | Observed | Review rule | Detail |
| --- | --- | --- | ---: | --- | --- |
{warning_rows}

## Interpretation boundary

The thresholds below are configurable screening aids, not universal scientific
acceptance criteria. `no_configured_warning_triggered` means only that these
rules did not fire. It does not approve empirical calibration, extrapolation to
an unseen reflectance domain, or transfer to a site unlike those evaluated.

```json
{json.dumps(asdict(config), indent=2, sort_keys=True)}
```
{figures}
"""


def _outputs_valid(
    paths: BulkResultsPaths,
    *,
    make_figures: bool,
    make_report: bool,
) -> bool:
    required = [
        paths.pair_band_summary,
        paths.weighting_comparison,
        paths.flightline_stability,
        paths.site_stability,
        paths.loso_transferability,
        paths.attention_flags,
        paths.metadata,
    ]
    if make_figures:
        required.extend(
            (
                paths.coefficient_figure,
                paths.correction_figure,
                paths.transferability_figure,
            )
        )
    if make_report:
        required.append(paths.report)
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    try:
        for path in required[:6]:
            pq.read_schema(path)
    except Exception:
        return False
    return True


def summarize_bulk_results(
    bulk_output: str | Path,
    *,
    config: BulkResultsConfig | None = None,
    make_figures: bool = True,
    make_report: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Summarize completed translation results without the source archive.

    Only the completed bulk manifest and compact model-result Parquets are read.
    Source rasters, sufficient-statistics checkpoints, diagnostic pixel samples,
    and observation datasets are neither required nor opened.
    """

    config = config or BulkResultsConfig()
    config.validate()
    paths = BulkResultsPaths(Path(bulk_output).expanduser().resolve())
    if not paths.bulk_output.is_dir():
        raise FileNotFoundError(f"Completed bulk output does not exist: {paths.bulk_output}")
    missing = [path for path in paths.required_inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Completed bulk output is missing compact result inputs: "
            + ", ".join(path.as_posix() for path in missing)
        )
    try:
        manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unreadable completed bulk manifest: {paths.manifest}") from exc
    if manifest.get("status") != "complete":
        raise ValueError(
            f"Bulk manifest status must be 'complete', found {manifest.get('status')!r}"
        )

    inputs = {
        label: _file_signature(path)
        for label, path in (
            ("manifest", paths.manifest),
            ("candidate_coefficients", paths.candidates),
            ("per_flightline", paths.per_flightline),
            ("per_site", paths.per_site),
            ("leave_one_site_out", paths.loso),
        )
    }
    run_signature = signature_sha256(
        {
            "bulk_results_schema_version": BULK_RESULTS_SCHEMA_VERSION,
            "inputs": inputs,
            "configuration": asdict(config),
            "make_figures": make_figures,
            "make_report": make_report,
        }
    )
    if not force and paths.metadata.is_file():
        try:
            previous = json.loads(paths.metadata.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous = {}
        if (
            previous.get("results_signature_sha256") == run_signature
            and _outputs_valid(
                paths,
                make_figures=make_figures,
                make_report=make_report,
            )
        ):
            return {**previous, "status": "reused"}

    candidates = _read_compact(paths.candidates, "candidates")
    per_flightline = _read_compact(paths.per_flightline, "per_flightline")
    per_site = _read_compact(paths.per_site, "per_site")
    loso_rows = _read_compact(paths.loso, "loso")
    candidate_levels = {str(row.get("analysis_level")) for row in candidates}
    if "pixel_pooled" not in candidate_levels:
        raise ValueError("Candidate coefficients must include pixel_pooled results")

    weighting = _weighting_rows(candidates, config)
    flightline = _summarize_stability(
        per_flightline,
        identity_field="flightline_id",
        r2_threshold=config.r2_review_threshold,
    )
    site = _summarize_stability(
        per_site,
        identity_field="site",
        r2_threshold=config.r2_review_threshold,
    )
    loso = _summarize_loso(loso_rows, config)
    pair_summaries, flags = _build_pair_summaries(
        weighting, flightline, site, loso, config
    )
    if not pair_summaries:
        raise ValueError("Candidate coefficients contain no translation pair-band results")

    _write_parquet(paths.weighting_comparison, weighting, _WEIGHTING_SCHEMA)
    _write_parquet(paths.flightline_stability, flightline, _STABILITY_SCHEMA)
    _write_parquet(paths.site_stability, site, _STABILITY_SCHEMA)
    _write_parquet(paths.loso_transferability, loso, _LOSO_SCHEMA)
    _write_parquet(paths.attention_flags, flags, _FLAG_SCHEMA)
    _write_parquet(paths.pair_band_summary, pair_summaries, _PAIR_SUMMARY_SCHEMA)
    overview = _overview(
        manifest,
        weighting,
        pair_summaries,
        per_flightline,
        per_site,
        loso_rows,
        flags,
    )
    figure_paths = (
        _make_figures(
            paths,
            weighting,
            pair_summaries,
            flightline,
            site,
            loso,
            config,
        )
        if make_figures
        else []
    )
    if make_report:
        write_text_atomic(
            paths.report,
            _markdown_report(overview, pair_summaries, flags, config, figure_paths),
        )
    compact_outputs = {
        "pair_band_summary": paths.pair_band_summary.as_posix(),
        "weighting_comparison": paths.weighting_comparison.as_posix(),
        "flightline_stability": paths.flightline_stability.as_posix(),
        "site_stability": paths.site_stability.as_posix(),
        "loso_transferability": paths.loso_transferability.as_posix(),
        "attention_flags": paths.attention_flags.as_posix(),
    }
    metadata = {
        "schema_version": BULK_RESULTS_SCHEMA_VERSION,
        "analysis": "bulk_translation_results_interpretation",
        "status": "complete",
        "source_data_policy": "completed_compact_bulk_outputs_only",
        "source_rasters_opened": False,
        "sufficient_statistics_regenerated": False,
        "pixel_cache_created": False,
        "bulk_output": paths.bulk_output.as_posix(),
        "bulk_analysis_run_id": manifest.get("analysis_run_id"),
        "results_signature_sha256": run_signature,
        "input_compact_outputs": inputs,
        "configuration": asdict(config),
        "screening_interpretation": (
            "Review flags are configurable diagnostics, not scientific approval. "
            "No configured warning triggered does not establish universal validity."
        ),
        "representative_correction_definition": (
            "100 * ((slope * x_reference + intercept) - x_reference) / x_reference; "
            "x_reference is shared by all weightings within a pair-band"
        ),
        "overview": overview,
        "pair_band_summaries": pair_summaries,
        "attention_flags": flags,
        "compact_outputs": compact_outputs,
        "metadata": paths.metadata.as_posix(),
        "figures": figure_paths,
        "report": paths.report.as_posix() if make_report else None,
    }
    write_json_atomic(paths.metadata, metadata)
    return {**metadata, "status": "created"}


__all__ = [
    "BULK_RESULTS_SCHEMA_VERSION",
    "BulkResultsConfig",
    "BulkResultsPaths",
    "summarize_bulk_results",
]
