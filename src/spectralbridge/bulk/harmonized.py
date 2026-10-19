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

    Parameters
    ----------
    input_path : str | Path
        Existing source tree or merged Parquet to inventory; input products are read in place.
    output_dir : str | Path
        Directory for generated products; bulk outputs must be outside the read-only input tree.
    kwargs : Any
        Additional keyword options forwarded to run_bulk_pipeline; materialize_observations is controlled by this builder and must not be supplied.

    Returns
    -------
    dict[str, Any]
        Bulk workflow result including the explicitly materialized combined pixel dataset and provenance paths.

    Raises
    ------
    TypeError
        If unsupported keyword options are supplied.

    Notes
    -----
    This compatibility builder currently produces the established combined
    Parquet through the bulk pipeline. It is deliberately separate from normal
    analysis so no caller can create a pixel-scale copy by accepting defaults.
    A future dedicated partitioned/Zarr builder can replace this implementation
    without changing the analysis contract.

    See Also
    --------
    spectralbridge.pipelines.bulk.run_bulk_pipeline : Related source-derived API contract.

    Examples
    --------
    This explicitly writes a pixel-scale product and can require substantial disk space. Normal compact analysis uses run_bulk_pipeline instead.

    >>> from spectralbridge import build_harmonized_dataset
    >>> result = build_harmonized_dataset(source_dir, output_dir)  # doctest: +SKIP
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
