"""Explicit boundary for intentionally building a pixel-level bulk dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_harmonized_dataset(
    input_path: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the legacy combined pixel dataset as an explicit requested product.

    This compatibility builder currently produces the established combined
    Parquet through the bulk pipeline. It is deliberately separate from normal
    analysis so no caller can create a pixel-scale copy by accepting defaults.
    A future dedicated partitioned/Zarr builder can replace this implementation
    without changing the analysis contract.
    """

    if "materialize_observations" in kwargs:
        raise TypeError(
            "build_harmonized_dataset controls materialization; do not pass "
            "materialize_observations"
        )
    from spectralbridge.pipelines.bulk import run_bulk_pipeline

    return run_bulk_pipeline(
        input_path,
        output_dir,
        materialize_observations=True,
        **kwargs,
    )


__all__ = ["build_harmonized_dataset"]
