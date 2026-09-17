"""Helpers for reading NEON reflectance HDF5 products across layout versions."""

from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional

import h5py
import numpy as np

from .neon_schema import canonical_vectors, resolve

__all__ = [
    "is_pre_2021",
    "peek_neon_sample_count",
    "peek_neon_raster_shape",
    "read_neon_cube",
    "read_neon_reflectance_unitless",
    "_prepare_map_info",
    "_map_info_core",
]

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"_([0-9]{8})_")


def is_pre_2021(h5_path: Path) -> bool:
    """Return ``True`` when ``h5_path`` appears to be a pre-2021 NEON export."""

    path = Path(h5_path)
    match = _DATE_RE.search(path.name)
    if match:
        year = int(match.group(1)[:4])
        return year < 2021
    return False


def _prepare_map_info(map_info: np.ndarray | bytes | str) -> list[str]:
    """Parse the NEON map info dataset into an ENVI-style list of strings."""

    def _normalise(component: Any) -> str:
        if isinstance(component, (bytes, np.bytes_)):
            return component.decode("utf-8").strip()
        return str(component).strip()

    if isinstance(map_info, np.ndarray):
        if map_info.ndim == 0:
            return _prepare_map_info(map_info.item())
        if map_info.dtype.kind in {"S", "U", "O"}:
            return [_normalise(value) for value in map_info.tolist()]

    if isinstance(map_info, (bytes, np.bytes_)):
        map_info_str = map_info.decode("utf-8")
    else:
        map_info_str = str(map_info)

    map_info_str = map_info_str.strip()
    if map_info_str.startswith("{") and map_info_str.endswith("}"):
        map_info_str = map_info_str[1:-1]

    return [component.strip() for component in map_info_str.split(",")]


def _map_info_core(map_info_list: list[str]) -> tuple[float, float, float, float, float, float]:
    """Extract numeric components from the map info list for transforms."""

    if len(map_info_list) < 7:
        raise RuntimeError("Map info dataset is shorter than expected for ENVI metadata.")

    def _to_float(value: str) -> float:
        try:
            return float(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Cannot interpret map info value '{value}' as float.") from exc

    ref_x = _to_float(map_info_list[1])
    ref_y = _to_float(map_info_list[2])
    ref_easting = _to_float(map_info_list[3])
    ref_northing = _to_float(map_info_list[4])
    pixel_x = _to_float(map_info_list[5])
    pixel_y = _to_float(map_info_list[6])

    return ref_x, ref_y, ref_easting, ref_northing, pixel_x, pixel_y


def _as_str(value: Any) -> str:
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8")
    return str(value)


def _extract_units(wavelength_ds: h5py.Dataset, spectral_group: Optional[h5py.Group]) -> Optional[str]:
    for attr_name in ("Units", "Unit", "units"):
        if attr_name in wavelength_ds.attrs:
            return _as_str(wavelength_ds.attrs[attr_name])
    if spectral_group is not None:
        alt = spectral_group.get("Wavelength_Units")
        if alt is not None:
            return _as_str(alt[()])
    return None


def _extract_no_data(dataset: h5py.Dataset) -> float:
    for attr_name in ("Data_Ignore_Value", "_FillValue", "NoData", "no_data"):
        if attr_name in dataset.attrs:
            attr_value = dataset.attrs[attr_name]
            if isinstance(attr_value, (np.ndarray, list, tuple)):
                if len(attr_value) == 0:
                    continue
                attr_value = attr_value[0]
            return float(attr_value)
    raise RuntimeError("Reflectance dataset missing a recognised no-data attribute.")


def _extract_scale_factor(dataset: h5py.Dataset) -> float:
    """Return the reflectance scale factor for a NEON dataset, defaulting to 1.0."""

    for attr_name in (
        "Scale_Factor",
        "scale_factor",
        "Scale Factor",
        "scale factor",
    ):
        if attr_name in dataset.attrs:
            value = dataset.attrs[attr_name]
            if isinstance(value, (np.ndarray, list, tuple)):
                if len(value) == 0:
                    continue
                value = value[0]
            try:
                return float(value)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                continue
    return 1.0


def reflectance_to_unitless_multiplier(scale_factor: float) -> float:
    """Return ``m`` such that ``unitless = stored * m``.

    Accepts both common packaging conventions:

    * Multiply style (``0.0001``): ``unitless = DN * 0.0001``
    * NEON / ENVI divisor style (``10000``): ``unitless = DN / 10000``
    * Already unitless (``1.0``): ``unitless = DN``

    The raw attribute is still stored on cubes / ENVI headers for QA; this helper
    is only for converting between storage units and physical reflectance.
    """

    try:
        sf = float(scale_factor)
    except (TypeError, ValueError):
        return 1.0
    if not np.isfinite(sf) or sf == 0.0:
        return 1.0
    # Values above 1 are treated as storage divisors (e.g. NEON Scale_Factor=10000).
    if abs(sf) > 1.0:
        return float(1.0 / sf)
    return float(sf)


def stored_to_unitless(data: np.ndarray, scale_factor: float) -> np.ndarray:
    """Convert stored reflectance values to unitless reflectance."""

    multiplier = np.float32(reflectance_to_unitless_multiplier(scale_factor))
    return np.asarray(data, dtype=np.float32) * multiplier


def unitless_to_stored(data: np.ndarray, scale_factor: float) -> np.ndarray:
    """Convert unitless reflectance back to the cube's storage scale."""

    multiplier = float(reflectance_to_unitless_multiplier(scale_factor))
    if multiplier == 0.0:
        return np.asarray(data, dtype=np.float32)
    return np.asarray(data, dtype=np.float32) / np.float32(multiplier)


def read_neon_reflectance_unitless(
    reflectance_ds: h5py.Dataset,
) -> tuple[np.ndarray, float, float]:
    """Return unitless reflectance scaled by the NEON factor with ignore masked.

    Parameters
    ----------
    reflectance_ds : h5py.Dataset
        The NEON reflectance dataset (``/Reflectance/Reflectance_Data`` or similar).

    Returns
    -------
    tuple[np.ndarray, float, float]
        ``(data_unitless, scale_factor, ignore_value)`` where ``data_unitless`` is a
        float32 array scaled into 0–1 reflectance with ignore values set to ``NaN``.
        ``scale_factor`` is the raw dataset attribute (for example ``10000`` or
        ``1e-4``); conversion to unitless always goes through
        :func:`reflectance_to_unitless_multiplier`.
    """

    data = np.asarray(reflectance_ds[()], dtype=np.float32)
    ignore_value = _extract_no_data(reflectance_ds)
    scale_factor = _extract_scale_factor(reflectance_ds)

    data_unitless = stored_to_unitless(data, scale_factor)
    data_unitless = np.where(data == ignore_value, np.nan, data_unitless)

    return data_unitless, scale_factor, ignore_value


def _find_dataset_path(h5_file: h5py.File, candidates: Iterable[str], ndim: int | None = None) -> Optional[str]:
    lowered = [candidate.lower() for candidate in candidates]
    matches: list[str] = []

    def _visitor(name: str, obj: h5py.Dataset) -> None:
        if not isinstance(obj, h5py.Dataset):  # pragma: no cover - h5py typing quirk
            return
        if ndim is not None and obj.ndim != ndim:
            return
        path_lower = name.lower()
        for candidate in lowered:
            if path_lower.endswith(candidate):
                matches.append(name)
                break

    h5_file.visititems(_visitor)
    if matches:
        matches.sort(key=len)
        return matches[0]
    return None


def _as_sample_slice(sample_slice: slice | tuple[int, int] | None) -> slice | None:
    if sample_slice is None:
        return None
    if isinstance(sample_slice, tuple):
        if len(sample_slice) != 2:
            raise ValueError("sample_slice tuple must be (start, stop)")
        return slice(int(sample_slice[0]), int(sample_slice[1]))
    return sample_slice


def _resolve_half_open_window(
    n: int,
    window: slice | tuple[int, int] | None,
) -> tuple[int, int, slice | None]:
    """Return ``(start, stop, normalized_slice_or_none)`` for a half-open window."""

    if window is None:
        return 0, int(n), None
    resolved = _as_sample_slice(window)
    assert resolved is not None
    start, stop, _ = resolved.indices(int(n))
    return int(start), int(stop), slice(start, stop)


def _samples_axis_count(shape: tuple[int, ...], wavelength_count: int) -> int:
    if len(shape) != 3:
        raise RuntimeError("Reflectance data does not have (lines, columns, bands) dimensions.")
    if shape[2] == wavelength_count:
        return int(shape[1])
    if shape[0] == wavelength_count:
        return int(shape[2])
    if shape[1] == wavelength_count:
        return int(shape[2])
    return int(shape[1])


def _lines_axis_count(shape: tuple[int, ...], wavelength_count: int) -> int:
    if len(shape) != 3:
        raise RuntimeError("Reflectance data does not have (lines, columns, bands) dimensions.")
    if shape[2] == wavelength_count:
        return int(shape[0])
    if shape[0] == wavelength_count:
        return int(shape[1])
    if shape[1] == wavelength_count:
        return int(shape[0])
    return int(shape[0])


def _slice_reflectance_dataset(
    reflectance_ds: h5py.Dataset,
    wavelength_count: int,
    sample_slice: slice | None,
    line_slice: slice | None = None,
) -> np.ndarray:
    """Read reflectance, optionally slicing line/sample axes before load."""

    if sample_slice is None and line_slice is None:
        return np.asarray(reflectance_ds[()], dtype=np.float32)

    shape = reflectance_ds.shape
    if len(shape) != 3:
        raise RuntimeError("Reflectance data does not have (lines, columns, bands) dimensions.")
    line_sl = line_slice if line_slice is not None else slice(None)
    sample_sl = sample_slice if sample_slice is not None else slice(None)
    if shape[2] == wavelength_count:
        return np.asarray(reflectance_ds[line_sl, sample_sl, :], dtype=np.float32)
    if shape[0] == wavelength_count:
        return np.asarray(reflectance_ds[:, line_sl, sample_sl], dtype=np.float32)
    if shape[1] == wavelength_count:
        return np.asarray(reflectance_ds[line_sl, :, sample_sl], dtype=np.float32)
    return np.asarray(reflectance_ds[line_sl, sample_sl, :], dtype=np.float32)


def _shift_map_info_for_window(
    map_info_list: list[str],
    sample_start: int = 0,
    line_start: int = 0,
) -> tuple[list[str], tuple[float, float, float, float, float, float] | None, float | None, float | None]:
    """Shift ENVI map info for optional sample/line window origins."""

    if not map_info_list:
        return map_info_list, None, None, None

    shifted = list(map_info_list)
    ref_x, ref_y, ref_easting, ref_northing, pixel_x, pixel_y = _map_info_core(shifted)
    ulx = ref_easting - pixel_x * (ref_x - 0.5) + sample_start * pixel_x
    uly = ref_northing + abs(pixel_y) * (ref_y - 0.5) - line_start * abs(pixel_y)
    if sample_start != 0:
        shifted[3] = str(ulx + pixel_x * (ref_x - 0.5))
    if line_start != 0:
        shifted[4] = str(uly - abs(pixel_y) * (ref_y - 0.5))
    yres = -abs(pixel_y)
    transform = (ulx, pixel_x, 0.0, uly, 0.0, yres)
    return shifted, transform, ulx, uly


def _shift_map_info_for_sample_start(
    map_info_list: list[str],
    sample_start: int,
) -> tuple[list[str], tuple[float, float, float, float, float, float] | None, float | None, float | None]:
    return _shift_map_info_for_window(map_info_list, sample_start=sample_start, line_start=0)


def _orient_cube(data: np.ndarray, wavelength_count: int) -> np.ndarray:
    array = np.asarray(data, dtype=np.float32)
    if array.ndim != 3:
        raise RuntimeError("Reflectance data does not have (lines, columns, bands) dimensions.")
    if array.shape[2] == wavelength_count:
        return array
    if array.shape[0] == wavelength_count:
        return np.moveaxis(array, 0, 2)
    if array.shape[1] == wavelength_count:
        return np.moveaxis(array, 1, 2)
    return array


def _metadata_root_from_path(dataset_path: str) -> Optional[str]:
    parts = dataset_path.split("/")
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx].lower() == "metadata":
            return "/".join(parts[: idx + 1])
    if len(parts) > 1:
        return "/".join(parts[:-1])
    return None


def _read_new_neon_layout(
    h5_file: h5py.File,
    sample_slice: slice | tuple[int, int] | None = None,
    line_slice: slice | tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    base_key: Optional[str] = None
    for key in h5_file.keys():
        candidate = f"{key}/Reflectance/Reflectance_Data"
        if candidate in h5_file:
            base_key = key
            break

    if base_key is None and "Reflectance/Reflectance_Data" not in h5_file:
        raise KeyError("Could not locate NEON reflectance dataset within the HDF5 file.")

    base_group: h5py.Group | h5py.File
    if base_key is None:
        base_group = h5_file
    else:
        base_group = h5_file[base_key]

    resolved = resolve(base_group)
    reflectance_ds = resolved.ds_reflectance
    scale_factor = _extract_scale_factor(reflectance_ds)

    wavelength_nm, fwhm_nm, to_sun_zenith, to_sensor_zenith = canonical_vectors(resolved)
    wavelengths = np.asarray(wavelength_nm, dtype=np.float32).reshape(-1)
    n_samples = _samples_axis_count(reflectance_ds.shape, len(wavelengths))
    n_lines = _lines_axis_count(reflectance_ds.shape, len(wavelengths))
    sample_start, sample_stop, column_slice = _resolve_half_open_window(
        n_samples, sample_slice
    )
    line_start, line_stop, row_slice = _resolve_half_open_window(n_lines, line_slice)
    data = _slice_reflectance_dataset(
        reflectance_ds, len(wavelengths), column_slice, row_slice
    )
    fwhm = (
        np.asarray(fwhm_nm, dtype=np.float32).reshape(-1)
        if fwhm_nm is not None
        else None
    )

    reflectance_group = reflectance_ds.parent
    if not isinstance(reflectance_group, h5py.Group):
        raise KeyError("Reflectance dataset is not within a group as expected.")

    metadata_group = reflectance_group.get("Metadata")
    if metadata_group is None:
        raise KeyError("Missing 'Metadata' group within NEON reflectance file.")

    wavelength_ds = resolved.ds_wavelength
    spectral_group = wavelength_ds.parent
    if not isinstance(spectral_group, h5py.Group):
        raise KeyError("Missing 'Spectral_Data' group within NEON reflectance metadata.")
    wavelength_units = _extract_units(wavelength_ds, spectral_group) or "Unknown"

    coordinate_group = metadata_group.get("Coordinate_System")
    map_info_dataset = coordinate_group.get("Map_Info") if coordinate_group is not None else None
    projection_dataset = (
        coordinate_group.get("Coordinate_System_String") if coordinate_group is not None else None
    )

    map_info_list: list[str] = []
    if map_info_dataset is not None:
        map_info_list = _prepare_map_info(map_info_dataset[()])

    projection_wkt = ""
    if projection_dataset is not None:
        projection_wkt = _as_str(projection_dataset[()])

    map_info_list, transform, ulx, uly = _shift_map_info_for_window(
        map_info_list, sample_start=sample_start, line_start=line_start
    )

    no_data = _extract_no_data(reflectance_ds)
    cube = _orient_cube(data, len(wavelengths))

    meta: Dict[str, Any] = {
        "map_info": map_info_list,
        "projection": projection_wkt,
        "transform": transform,
        "ulx": ulx,
        "uly": uly,
        "wavelength_units": wavelength_units,
        "fwhm": fwhm,
        "wavelength_nm": wavelengths,
        "fwhm_nm": fwhm,
        "to_sun_zenith": to_sun_zenith,
        "to_sensor_zenith": to_sensor_zenith,
        "no_data": no_data,
        "scale_factor": scale_factor,
        "samples": int(cube.shape[1]),
        "lines": int(cube.shape[0]),
        "bands": int(cube.shape[2]),
        "metadata_group_paths": [metadata_group.name],
        "base_key": base_key,
        "layout": "reflectance_group",
        "sample_start": int(sample_start),
        "sample_stop": int(sample_stop),
        "full_samples": int(n_samples),
        "line_start": int(line_start),
        "line_stop": int(line_stop),
        "full_lines": int(n_lines),
    }
    return cube, wavelengths, meta


def _read_old_neon_layout(
    h5_file: h5py.File,
    sample_slice: slice | tuple[int, int] | None = None,
    line_slice: slice | tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    data_path = _find_dataset_path(h5_file, ("reflectance_data", "reflectance"), ndim=3)
    if data_path is None:
        raise KeyError("Legacy NEON file missing a reflectance dataset.")
    data_ds = h5_file[data_path]
    scale_factor = _extract_scale_factor(data_ds)

    wavelength_path = _find_dataset_path(
        h5_file,
        ("wavelength", "wavelengths", "center_wavelength"),
        ndim=1,
    )
    if wavelength_path is None:
        raise KeyError("Legacy NEON file missing a wavelength dataset.")
    wavelength_ds = h5_file[wavelength_path]
    wavelengths = np.asarray(wavelength_ds[()], dtype=np.float32).reshape(-1)
    n_samples = _samples_axis_count(data_ds.shape, len(wavelengths))
    n_lines = _lines_axis_count(data_ds.shape, len(wavelengths))
    sample_start, sample_stop, column_slice = _resolve_half_open_window(
        n_samples, sample_slice
    )
    line_start, line_stop, row_slice = _resolve_half_open_window(n_lines, line_slice)
    data = _slice_reflectance_dataset(
        data_ds, len(wavelengths), column_slice, row_slice
    )

    fwhm_path = _find_dataset_path(h5_file, ("fwhm", "full_width_half_max"), ndim=1)
    fwhm = np.asarray(h5_file[fwhm_path][()], dtype=np.float32).reshape(-1) if fwhm_path else None
    wavelength_units = _extract_units(wavelength_ds, None) or "Unknown"

    map_info_path = _find_dataset_path(h5_file, ("map_info",))
    map_info_list: list[str] = []
    if map_info_path:
        map_info_list = _prepare_map_info(h5_file[map_info_path][()])

    projection_path = _find_dataset_path(
        h5_file,
        ("coordinate_system_string", "projection", "wkt"),
    )
    projection_wkt = ""
    if projection_path:
        projection_wkt = _as_str(h5_file[projection_path][()])

    map_info_list, transform, ulx, uly = _shift_map_info_for_window(
        map_info_list, sample_start=sample_start, line_start=line_start
    )

    no_data = _extract_no_data(data_ds)
    cube = _orient_cube(data, len(wavelengths))

    metadata_root = _metadata_root_from_path(wavelength_path)
    base_key = data_path.split("/")[0] if "/" in data_path else data_path

    meta: Dict[str, Any] = {
        "map_info": map_info_list,
        "projection": projection_wkt,
        "transform": transform,
        "ulx": ulx,
        "uly": uly,
        "wavelength_units": wavelength_units,
        "fwhm": fwhm,
        "wavelength_nm": wavelengths,
        "fwhm_nm": fwhm,
        "to_sun_zenith": None,
        "to_sensor_zenith": None,
        "no_data": no_data,
        "scale_factor": scale_factor,
        "samples": int(cube.shape[1]),
        "lines": int(cube.shape[0]),
        "bands": int(cube.shape[2]),
        "metadata_group_paths": [metadata_root] if metadata_root else [],
        "base_key": base_key,
        "layout": "legacy_hdf5",
        "sample_start": int(sample_start),
        "sample_stop": int(sample_stop),
        "full_samples": int(n_samples),
        "line_start": int(line_start),
        "line_stop": int(line_stop),
        "full_lines": int(n_lines),
    }
    return cube, wavelengths, meta


def _read_site_group_legacy_layout(
    h5_file: h5py.File,
    sample_slice: slice | tuple[int, int] | None = None,
    line_slice: slice | tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    root_keys = list(h5_file.keys())
    if len(root_keys) != 1:
        raise KeyError("Site-group legacy layout expects a single root group.")

    site_group_key = root_keys[0]
    site_group_obj = h5_file.get(site_group_key)
    if not isinstance(site_group_obj, h5py.Group):
        raise KeyError("Root entry for legacy site-group layout is not a group.")

    reflectance_group = site_group_obj.get("Reflectance")
    if not isinstance(reflectance_group, h5py.Group):
        raise KeyError("Legacy site-group layout missing 'Reflectance' group.")

    data_ds = reflectance_group.get("Reflectance_Data")
    if not isinstance(data_ds, h5py.Dataset):
        raise KeyError("Legacy site-group layout missing 'Reflectance_Data' dataset.")

    scale_factor = _extract_scale_factor(data_ds)

    metadata_group = reflectance_group.get("Metadata")
    if metadata_group is None:
        raise KeyError("Legacy site-group layout missing 'Metadata' group.")

    spectral_group = metadata_group.get("Spectral_Data")
    if spectral_group is None:
        raise KeyError("Legacy site-group layout missing 'Spectral_Data'.")

    wavelength_ds: Optional[h5py.Dataset] = None
    for key, value in spectral_group.items():
        if isinstance(value, h5py.Dataset) and value.ndim >= 1:
            if key.lower() in {"wavelength", "wavelengths"}:
                wavelength_ds = value
                break
    if wavelength_ds is None:
        raise KeyError("Legacy site-group layout missing spectral wavelength dataset.")

    wavelengths = np.asarray(wavelength_ds[()], dtype=np.float32).reshape(-1)
    n_samples = _samples_axis_count(data_ds.shape, len(wavelengths))
    n_lines = _lines_axis_count(data_ds.shape, len(wavelengths))
    sample_start, sample_stop, column_slice = _resolve_half_open_window(
        n_samples, sample_slice
    )
    line_start, line_stop, row_slice = _resolve_half_open_window(n_lines, line_slice)
    data = _slice_reflectance_dataset(
        data_ds, len(wavelengths), column_slice, row_slice
    )

    fwhm_ds: Optional[h5py.Dataset] = None
    for key, value in spectral_group.items():
        if isinstance(value, h5py.Dataset) and value.ndim >= 1:
            if key.lower() == "fwhm":
                fwhm_ds = value
                break

    fwhm = np.asarray(fwhm_ds[()], dtype=np.float32).reshape(-1) if fwhm_ds else None
    wavelength_units = _extract_units(wavelength_ds, spectral_group) or "Unknown"

    coordinate_group = metadata_group.get("Coordinate_System")
    map_info_dataset = coordinate_group.get("Map_Info") if coordinate_group else None
    projection_dataset = (
        coordinate_group.get("Coordinate_System_String") if coordinate_group else None
    )

    map_info_list: list[str] = []
    if map_info_dataset is not None:
        map_info_list = _prepare_map_info(map_info_dataset[()])

    projection_wkt = ""
    if projection_dataset is not None:
        projection_wkt = _as_str(projection_dataset[()])

    map_info_list, transform, ulx, uly = _shift_map_info_for_window(
        map_info_list, sample_start=sample_start, line_start=line_start
    )

    no_data = _extract_no_data(data_ds)
    cube = _orient_cube(data, len(wavelengths))

    meta: Dict[str, Any] = {
        "map_info": map_info_list,
        "projection": projection_wkt,
        "transform": transform,
        "ulx": ulx,
        "uly": uly,
        "wavelength_units": wavelength_units,
        "fwhm": fwhm,
        "wavelength_nm": wavelengths,
        "fwhm_nm": fwhm,
        "to_sun_zenith": None,
        "to_sensor_zenith": None,
        "no_data": no_data,
        "scale_factor": scale_factor,
        "samples": int(cube.shape[1]),
        "lines": int(cube.shape[0]),
        "bands": int(cube.shape[2]),
        "metadata_group_paths": [metadata_group.name],
        "base_key": f"{site_group_key}/Reflectance",
        "layout": "legacy_site_group",
        "site": site_group_key,
        "sample_start": int(sample_start),
        "sample_stop": int(sample_stop),
        "full_samples": int(n_samples),
        "line_start": int(line_start),
        "line_stop": int(line_stop),
        "full_lines": int(n_lines),
    }

    return cube, wavelengths, meta


def peek_neon_raster_shape(h5_path: Path) -> tuple[int, int]:
    """Return ``(n_lines, n_samples)`` without loading the reflectance cube."""

    path = Path(h5_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with h5py.File(path, "r") as h5_file:
        base_key: Optional[str] = None
        for key in h5_file.keys():
            candidate = f"{key}/Reflectance/Reflectance_Data"
            if candidate in h5_file:
                base_key = key
                break
        if base_key is not None or "Reflectance/Reflectance_Data" in h5_file:
            base_group: h5py.Group | h5py.File
            if base_key is None:
                base_group = h5_file
            else:
                base_group = h5_file[base_key]
            resolved = resolve(base_group)
            n_bands = int(np.asarray(resolved.ds_wavelength[()], dtype=np.float32).size)
            shape = resolved.ds_reflectance.shape
            return (
                _lines_axis_count(shape, n_bands),
                _samples_axis_count(shape, n_bands),
            )

        data_path = _find_dataset_path(h5_file, ("reflectance_data", "reflectance"), ndim=3)
        wavelength_path = _find_dataset_path(
            h5_file,
            ("wavelength", "wavelengths", "center_wavelength"),
            ndim=1,
        )
        if data_path is not None and wavelength_path is not None:
            n_bands = int(np.asarray(h5_file[wavelength_path][()], dtype=np.float32).size)
            shape = h5_file[data_path].shape
            return (
                _lines_axis_count(shape, n_bands),
                _samples_axis_count(shape, n_bands),
            )

    raise RuntimeError(f"Unable to peek NEON raster shape for {path}")


def peek_neon_sample_count(h5_path: Path) -> int:
    """Return the across-track sample count without loading the reflectance cube."""

    return peek_neon_raster_shape(h5_path)[1]


def read_neon_cube(
    h5_path: Path,
    sample_slice: slice | tuple[int, int] | None = None,
    line_slice: slice | tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Return ``(cube, wavelengths, metadata)`` for ``h5_path`` regardless of layout.

    ``sample_slice`` / ``line_slice`` are optional half-open windows on the
    across-track and along-track axes. When omitted, the full cube is loaded.
    """

    path = Path(h5_path)
    if not path.exists():
        raise FileNotFoundError(path)

    layout_error: Exception | None = None
    column_slice = _as_sample_slice(sample_slice)
    row_slice = _as_sample_slice(line_slice)

    with h5py.File(path, "r") as h5_file:
        root_keys = list(h5_file.keys())
        if is_pre_2021(path):
            readers = (
                _read_site_group_legacy_layout,
                _read_old_neon_layout,
                _read_new_neon_layout,
            )
        else:
            readers = (
                _read_new_neon_layout,
                _read_old_neon_layout,
                _read_site_group_legacy_layout,
            )

        for reader in readers:
            try:
                return reader(
                    h5_file,
                    sample_slice=column_slice,
                    line_slice=row_slice,
                )
            except Exception as exc:  # pragma: no cover - defensive cascade
                if layout_error is None:
                    layout_error = exc
                continue

    root_summary = ", ".join(root_keys) if root_keys else "<no root groups>"
    if layout_error is not None:
        raise RuntimeError(
            f"Unable to interpret NEON HDF5 layout for {path} (root groups: {root_summary}): {layout_error}"
        ) from layout_error

    raise RuntimeError(
        f"Unable to interpret NEON HDF5 layout for {path} (root groups: {root_summary})."
    )
