"""Bounded, restart-safe statistics over immutable ENVI flightline products."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict, dataclass, replace
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
from typing import Any, Iterator, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .models import BulkAnalysisPaths, FlightlineRecord
from .provenance import canonical_json, signature_sha256, write_json_atomic
from .registry import TranslationPair


STATISTICS_SCHEMA_VERSION = 1


@dataclass
class BivariateStatistics:
    """Numerically stable, mergeable bivariate population moments."""

    n: int = 0
    mean_x: float = 0.0
    mean_y: float = 0.0
    m2_x: float = 0.0
    m2_y: float = 0.0
    c_xy: float = 0.0
    x_min: float = math.inf
    x_max: float = -math.inf
    y_min: float = math.inf
    y_max: float = -math.inf

    def update(self, x: np.ndarray, y: np.ndarray) -> None:
        x64 = np.asarray(x, dtype=np.float64).reshape(-1)
        y64 = np.asarray(y, dtype=np.float64).reshape(-1)
        if x64.size != y64.size:
            raise ValueError("Aligned source and target chunks have different sizes")
        if x64.size == 0:
            return
        mean_x = float(np.mean(x64, dtype=np.float64))
        mean_y = float(np.mean(y64, dtype=np.float64))
        dx = x64 - mean_x
        dy = y64 - mean_y
        self.merge(
            BivariateStatistics(
                n=int(x64.size),
                mean_x=mean_x,
                mean_y=mean_y,
                m2_x=float(np.dot(dx, dx)),
                m2_y=float(np.dot(dy, dy)),
                c_xy=float(np.dot(dx, dy)),
                x_min=float(np.min(x64)),
                x_max=float(np.max(x64)),
                y_min=float(np.min(y64)),
                y_max=float(np.max(y64)),
            )
        )

    def merge(self, other: BivariateStatistics) -> BivariateStatistics:
        if other.n == 0:
            return self
        if self.n == 0:
            for name, value in asdict(other).items():
                setattr(self, name, value)
            return self
        total = self.n + other.n
        dx = other.mean_x - self.mean_x
        dy = other.mean_y - self.mean_y
        cross_weight = self.n * other.n / total
        self.m2_x += other.m2_x + dx * dx * cross_weight
        self.m2_y += other.m2_y + dy * dy * cross_weight
        self.c_xy += other.c_xy + dx * dy * cross_weight
        self.mean_x += dx * other.n / total
        self.mean_y += dy * other.n / total
        self.n = total
        self.x_min = min(self.x_min, other.x_min)
        self.x_max = max(self.x_max, other.x_max)
        self.y_min = min(self.y_min, other.y_min)
        self.y_max = max(self.y_max, other.y_max)
        return self

    def subtract(self, other: BivariateStatistics) -> BivariateStatistics:
        """Return the stable inverse merge ``self - other`` for LOSO fitting."""

        if other.n == 0:
            return self.copy()
        remaining = self.n - other.n
        if remaining <= 0:
            return BivariateStatistics()
        mean_x = (self.n * self.mean_x - other.n * other.mean_x) / remaining
        mean_y = (self.n * self.mean_y - other.n * other.mean_y) / remaining
        dx = other.mean_x - mean_x
        dy = other.mean_y - mean_y
        cross_weight = remaining * other.n / self.n
        return BivariateStatistics(
            n=remaining,
            mean_x=mean_x,
            mean_y=mean_y,
            m2_x=max(0.0, self.m2_x - other.m2_x - dx * dx * cross_weight),
            m2_y=max(0.0, self.m2_y - other.m2_y - dy * dy * cross_weight),
            c_xy=self.c_xy - other.c_xy - dx * dy * cross_weight,
        )

    def copy(self) -> BivariateStatistics:
        return BivariateStatistics(**asdict(self))

    @property
    def sum_x(self) -> float:
        return self.mean_x * self.n

    @property
    def sum_y(self) -> float:
        return self.mean_y * self.n

    @property
    def sum_x2(self) -> float:
        return self.m2_x + self.n * self.mean_x * self.mean_x

    @property
    def sum_y2(self) -> float:
        return self.m2_y + self.n * self.mean_y * self.mean_y

    @property
    def sum_xy(self) -> float:
        return self.c_xy + self.n * self.mean_x * self.mean_y

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> BivariateStatistics:
        return cls(
            n=int(row["n"]),
            mean_x=float(row["mean_x"] or 0.0),
            mean_y=float(row["mean_y"] or 0.0),
            m2_x=float(row["m2_x"] or 0.0),
            m2_y=float(row["m2_y"] or 0.0),
            c_xy=float(row["c_xy"] or 0.0),
            x_min=float(row["x_min"]) if row.get("x_min") is not None else math.inf,
            x_max=float(row["x_max"]) if row.get("x_max") is not None else -math.inf,
            y_min=float(row["y_min"]) if row.get("y_min") is not None else math.inf,
            y_max=float(row["y_max"]) if row.get("y_max") is not None else -math.inf,
        )


@dataclass(frozen=True)
class PairBand:
    translation_pair: str
    source_sensor: str
    target_sensor: str
    band_index: int
    source_band_index: int
    target_band_index: int

    @property
    def x_column(self) -> str:
        return f"{self.source_sensor}_band_{self.source_band_index}"

    @property
    def y_column(self) -> str:
        return f"{self.target_sensor}_band_{self.target_band_index}"


def pair_bands(pairs: Sequence[TranslationPair]) -> tuple[PairBand, ...]:
    result: list[PairBand] = []
    for pair in pairs:
        matched = pair.band_pairs
        if not matched:
            count = min(pair.expected_source_bands or 0, pair.expected_target_bands or 0)
            matched = tuple((index, index) for index in range(1, count + 1))
        result.extend(
            PairBand(
                translation_pair=pair.key,
                source_sensor=pair.source_sensor,
                target_sensor=pair.target_sensor,
                band_index=index,
                source_band_index=source_band,
                target_band_index=target_band,
            )
            for index, (source_band, target_band) in enumerate(matched, start=1)
        )
    return tuple(result)


def _valid_sensor_mask(values: np.ndarray, nodata: float | int | None) -> np.ndarray:
    valid = np.isfinite(values).all(axis=0)
    if nodata is not None:
        valid &= ~(values == nodata).any(axis=0)
    return valid.reshape(-1)


def iter_aligned_pair_chunks(
    flightline: FlightlineRecord,
    translation_pairs: Sequence[TranslationPair],
    *,
    chunk_size: int,
    minimum_reflectance: float,
) -> Iterator[tuple[int, dict[PairBand, tuple[np.ndarray, np.ndarray, np.ndarray]]]]:
    """Read all requested sensors together and yield aligned, valid pair arrays."""

    import rasterio
    from rasterio.windows import Window

    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    products = json.loads(flightline.target_products_json)
    eligibility = json.loads(flightline.analysis_eligibility_json)
    selected_pairs = tuple(pair for pair in translation_pairs if eligibility.get(pair.key))
    specs = pair_bands(selected_pairs)
    sensors = sorted(
        {sensor for spec in specs for sensor in (spec.source_sensor, spec.target_sensor)}
    )
    if not specs:
        return
    with ExitStack() as stack:
        datasets = {
            sensor: stack.enter_context(rasterio.open(products[sensor]["image"]))
            for sensor in sensors
        }
        reference_sensor = sensors[0]
        reference = datasets[reference_sensor]
        for sensor, dataset in datasets.items():
            compatible = (
                dataset.width == reference.width
                and dataset.height == reference.height
                and dataset.transform.almost_equals(reference.transform)
                and dataset.crs == reference.crs
            )
            if not compatible:
                raise ValueError(
                    "Spatially incompatible translation products for "
                    f"{flightline.canonical_flightline_id}: {reference_sensor} and {sensor}"
                )
        chunk_index = 0
        for row_start in range(0, reference.height, chunk_size):
            height = min(chunk_size, reference.height - row_start)
            for col_start in range(0, reference.width, chunk_size):
                width = min(chunk_size, reference.width - col_start)
                chunk_index += 1
                window = Window(col_start, row_start, width, height)
                arrays = {sensor: dataset.read(window=window) for sensor, dataset in datasets.items()}
                sensor_valid = {
                    sensor: _valid_sensor_mask(arrays[sensor], datasets[sensor].nodata)
                    for sensor in sensors
                }
                rows = np.repeat(np.arange(row_start, row_start + height), width)
                cols = np.tile(np.arange(col_start, col_start + width), height)
                pixel_ids = rows.astype(np.int64) * reference.width + cols.astype(np.int64)
                values: dict[PairBand, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
                for spec in specs:
                    x = arrays[spec.source_sensor][spec.source_band_index - 1].reshape(-1)
                    y = arrays[spec.target_sensor][spec.target_band_index - 1].reshape(-1)
                    valid = (
                        sensor_valid[spec.source_sensor]
                        & sensor_valid[spec.target_sensor]
                        & (x >= minimum_reflectance)
                        & (y >= minimum_reflectance)
                    )
                    values[spec] = (pixel_ids[valid], x[valid], y[valid])
                yield chunk_index, values


_STATISTICS_SCHEMA = pa.schema(
    [
        ("schema_version", pa.int32()),
        ("flightline_id", pa.string()),
        ("site", pa.string()),
        ("acquisition_date", pa.string()),
        ("translation_pair", pa.string()),
        ("source_sensor", pa.string()),
        ("target_sensor", pa.string()),
        ("band_index", pa.int32()),
        ("source_band_index", pa.int32()),
        ("target_band_index", pa.int32()),
        ("x_column", pa.string()),
        ("y_column", pa.string()),
        ("n", pa.int64()),
        ("sum_x", pa.float64()),
        ("sum_y", pa.float64()),
        ("sum_x2", pa.float64()),
        ("sum_y2", pa.float64()),
        ("sum_xy", pa.float64()),
        ("mean_x", pa.float64()),
        ("mean_y", pa.float64()),
        ("m2_x", pa.float64()),
        ("m2_y", pa.float64()),
        ("c_xy", pa.float64()),
        ("x_min", pa.float64()),
        ("x_max", pa.float64()),
        ("y_min", pa.float64()),
        ("y_max", pa.float64()),
        ("chunk_count", pa.int32()),
        ("checkpoint_signature_sha256", pa.string()),
    ]
)

_SAMPLE_SCHEMA = pa.schema(
    [
        ("flightline_id", pa.string()),
        ("site", pa.string()),
        ("translation_pair", pa.string()),
        ("band_index", pa.int32()),
        ("pixel_id", pa.int64()),
        ("x", pa.float64()),
        ("y", pa.float64()),
        ("sample_label", pa.string()),
    ]
)


def _write_parquet_atomic(path: Path, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), temporary, compression="zstd")
    pq.read_schema(temporary)
    temporary.replace(path)


def write_statistics(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_parquet_atomic(path, rows, _STATISTICS_SCHEMA)


def write_diagnostic_sample(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_parquet_atomic(path, rows, _SAMPLE_SCHEMA)


def _sample_priorities(
    seed: int,
    flightline_id: str,
    spec: PairBand,
    chunk_index: int,
    count: int,
) -> np.ndarray:
    """Return deterministic random priorities without hashing every pixel in Python."""

    payload = (
        f"{seed}|{flightline_id}|{spec.translation_pair}|{spec.band_index}|{chunk_index}"
    ).encode("utf-8")
    chunk_seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return np.random.default_rng(chunk_seed).integers(
        0,
        np.iinfo(np.uint64).max,
        size=count,
        dtype=np.uint64,
        endpoint=True,
    )


def compute_flightline_statistics(
    flightline: FlightlineRecord,
    paths: BulkAnalysisPaths,
    *,
    chunk_size: int,
    minimum_reflectance: float,
    translation_pairs: Sequence[TranslationPair],
    diagnostic_sample_size: int = 0,
    diagnostic_seed: int = 0,
    force: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], FlightlineRecord]:
    """Create or reuse one compact per-flightline analytical checkpoint."""

    flightline_id = flightline.canonical_flightline_id
    if not flightline_id:
        raise ValueError("Cannot analyze a flightline without canonical identity")
    products = json.loads(flightline.target_products_json)
    eligibility = json.loads(flightline.analysis_eligibility_json)
    selected_pairs = tuple(pair for pair in translation_pairs if eligibility.get(pair.key))
    selected_sensors = sorted(
        {sensor for pair in selected_pairs for sensor in (pair.source_sensor, pair.target_sensor)}
    )
    signature_payload = {
        "statistics_schema_version": STATISTICS_SCHEMA_VERSION,
        "flightline_id": flightline_id,
        "source_signatures": {
            sensor: products[sensor]["source_signature_sha256"] for sensor in selected_sensors
        },
        "translation_pairs": [asdict(pair) for pair in selected_pairs],
        "validity": {
            "finite": True,
            "exclude_sensor_pixel_if_any_band_is_nodata": True,
            "minimum_reflectance": minimum_reflectance,
        },
        "chunk_size": chunk_size,
        "diagnostic_sample_size": diagnostic_sample_size,
        "diagnostic_seed": diagnostic_seed,
    }
    checkpoint_signature = signature_sha256(signature_payload)
    directory = paths.flightline_statistics_dir / flightline_id
    statistics_path = directory / "sufficient_statistics.parquet"
    sample_path = directory / "diagnostic_sample.parquet"
    metadata_path = directory / "statistics_metadata.json"
    status_path = directory / "status.json"
    if not force and statistics_path.is_file() and metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            reusable = metadata.get("checkpoint_signature_sha256") == checkpoint_signature
            rows = pq.read_table(statistics_path).to_pylist() if reusable else []
            samples = (
                pq.read_table(sample_path).to_pylist()
                if reusable and sample_path.is_file()
                else []
            )
        except Exception:
            reusable = False
            rows = []
            samples = []
        if reusable:
            row_count = max((int(row["n"]) for row in rows), default=0)
            return rows, samples, replace(
                flightline,
                row_count=row_count,
                size_bytes=statistics_path.stat().st_size,
                schema_fingerprints_json=canonical_json([checkpoint_signature]),
                cache_observations=None,
                extraction_status="statistics_reused",
                estimated_cache_bytes=statistics_path.stat().st_size
                + (sample_path.stat().st_size if sample_path.is_file() else 0),
            )

    directory.mkdir(parents=True, exist_ok=True)
    moments = {spec: BivariateStatistics() for spec in pair_bands(selected_pairs)}
    specs = tuple(moments)
    sample_cap_by_spec = {
        spec: diagnostic_sample_size // max(1, len(specs))
        + (index < diagnostic_sample_size % max(1, len(specs)))
        for index, spec in enumerate(specs)
    }
    reservoirs: dict[PairBand, list[tuple[int, int, dict[str, Any]]]] = {
        spec: [] for spec in moments
    }
    chunk_count = 0
    for chunk_count, values in iter_aligned_pair_chunks(
        flightline,
        selected_pairs,
        chunk_size=chunk_size,
        minimum_reflectance=minimum_reflectance,
    ):
        for spec, (pixel_ids, x, y) in values.items():
            moments[spec].update(x, y)
            sample_cap = sample_cap_by_spec[spec]
            if sample_cap <= 0 or pixel_ids.size == 0:
                continue
            heap = reservoirs[spec]
            priorities = _sample_priorities(
                diagnostic_seed,
                flightline_id,
                spec,
                chunk_count,
                int(pixel_ids.size),
            )
            candidate_count = min(sample_cap, int(pixel_ids.size))
            candidate_indices = np.argpartition(
                priorities, candidate_count - 1
            )[:candidate_count]
            for candidate_index in candidate_indices:
                pixel_id = int(pixel_ids[candidate_index])
                priority = int(priorities[candidate_index])
                record = {
                    "flightline_id": flightline_id,
                    "site": flightline.site,
                    "translation_pair": spec.translation_pair,
                    "band_index": spec.band_index,
                    "pixel_id": pixel_id,
                    "x": float(x[candidate_index]),
                    "y": float(y[candidate_index]),
                    "sample_label": "deterministic_bounded_diagnostic_sample",
                }
                item = (-priority, pixel_id, record)
                if len(heap) < sample_cap:
                    heapq.heappush(heap, item)
                elif priority < -heap[0][0]:
                    heapq.heapreplace(heap, item)

    rows: list[dict[str, Any]] = []
    for spec, stats in moments.items():
        finite_bounds = stats.n > 0
        rows.append(
            {
                "schema_version": STATISTICS_SCHEMA_VERSION,
                "flightline_id": flightline_id,
                "site": flightline.site,
                "acquisition_date": flightline.acquisition_date,
                "translation_pair": spec.translation_pair,
                "source_sensor": spec.source_sensor,
                "target_sensor": spec.target_sensor,
                "band_index": spec.band_index,
                "source_band_index": spec.source_band_index,
                "target_band_index": spec.target_band_index,
                "x_column": spec.x_column,
                "y_column": spec.y_column,
                "n": stats.n,
                "sum_x": stats.sum_x,
                "sum_y": stats.sum_y,
                "sum_x2": stats.sum_x2,
                "sum_y2": stats.sum_y2,
                "sum_xy": stats.sum_xy,
                "mean_x": stats.mean_x if stats.n else None,
                "mean_y": stats.mean_y if stats.n else None,
                "m2_x": stats.m2_x,
                "m2_y": stats.m2_y,
                "c_xy": stats.c_xy,
                "x_min": stats.x_min if finite_bounds else None,
                "x_max": stats.x_max if finite_bounds else None,
                "y_min": stats.y_min if finite_bounds else None,
                "y_max": stats.y_max if finite_bounds else None,
                "chunk_count": chunk_count,
                "checkpoint_signature_sha256": checkpoint_signature,
            }
        )
    samples = [item[2] for heap in reservoirs.values() for item in heap]
    samples.sort(
        key=lambda row: (
            row["translation_pair"],
            row["band_index"],
            row["pixel_id"],
        )
    )
    write_statistics(statistics_path, rows)
    if diagnostic_sample_size:
        write_diagnostic_sample(sample_path, samples)
    elif sample_path.exists():
        sample_path.unlink()
    metadata = {
        **signature_payload,
        "checkpoint_signature_sha256": checkpoint_signature,
        "source_directory": flightline.source_directory,
        "statistics": statistics_path.as_posix(),
        "diagnostic_sample": sample_path.as_posix() if diagnostic_sample_size else None,
        "statistics_row_count": len(rows),
        "diagnostic_sample_row_count": len(samples),
        "chunk_count": chunk_count,
        "source_data_policy": "read_only",
        "spectralbridge_version": _spectralbridge_version(),
        "git_commit": os.environ.get("GITHUB_SHA"),
    }
    write_json_atomic(metadata_path, metadata)
    write_json_atomic(
        status_path,
        {"status": "success", "checkpoint_signature_sha256": checkpoint_signature},
    )
    row_count = max((stats.n for stats in moments.values()), default=0)
    return rows, samples, replace(
        flightline,
        row_count=row_count,
        size_bytes=statistics_path.stat().st_size,
        schema_fingerprints_json=canonical_json([checkpoint_signature]),
        cache_observations=None,
        extraction_status="statistics_success",
        estimated_cache_bytes=statistics_path.stat().st_size
        + (sample_path.stat().st_size if sample_path.is_file() else 0),
    )


def _spectralbridge_version() -> str:
    import spectralbridge

    return spectralbridge.__version__


__all__ = [
    "STATISTICS_SCHEMA_VERSION",
    "BivariateStatistics",
    "PairBand",
    "compute_flightline_statistics",
    "iter_aligned_pair_chunks",
    "pair_bands",
    "write_diagnostic_sample",
    "write_statistics",
]
