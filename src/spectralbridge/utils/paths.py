"""Path utilities for locating package data files."""
from __future__ import annotations

from pathlib import Path


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_package_data_path(filename: str) -> Path:
    """Return the absolute path to a bundled data file.

    Parameters
    ----------
    filename : str
        Package-relative resource name beneath spectralbridge/data; missing resources raise FileNotFoundError.

    Returns
    -------
    Path
        Absolute existing bundled resource path.

    Raises
    ------
    FileNotFoundError
        If a required source or completed artifact is absent.

    See Also
    --------
    spectralbridge.pipelines.pipeline.process_one_flightline : Related source-derived API contract.

    Examples
    --------
    >>> from spectralbridge.utils import get_package_data_path
    >>> assert get_package_data_path("landsat_band_parameters.json").is_file()
    """

    data_path = _package_root() / "data" / filename
    if not data_path.exists():
        raise FileNotFoundError(f"Missing data file: {data_path}")
    return data_path
