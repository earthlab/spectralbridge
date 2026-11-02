"""Explicit cloud recovery orchestration; scientific algorithms remain in package APIs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from spectralbridge.remote import GocmdRemoteBackend, RemoteEntry, remote_join

CAUTIONS = [
    "Retain ten TIFF bands only after exact H5 equality; other channels are unclassified.",
    "Bundled acquisition times are used; package/manifest date disagreements require review.",
    "Terrain masks are preserved. Review scientific QA before promoting results.",
]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, default=str) + "\n")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_listing(text, parent):
    entries = []
    for section in json.loads(text):
        for row in section["data"]:
            if "Name" not in row:
                continue
            name, kind = row["Name"], row["Type"]
            if "/" in name or name in {".", ".."} or kind not in {"collection", "data-object"}:
                raise ValueError(f"Unexpected remote child: {row}")
            entries.append(RemoteEntry(remote_join(parent, name), name, kind == "collection",
                                       int(row["Size"]) if row.get("Size") else None,
                                       modified=row.get("Modify Time")))
    return entries


class JsonGocmdBackend(GocmdRemoteBackend):
    """Read GoCommands' explicit JSON, independently of the default table UI."""

    def list_directory(self, remote_path):
        result = self._run("ls", "--output_json", remote_path, operation="JSON inventory")
        return parse_listing(result.stdout, remote_path)


def download_sources(package, directory, backend):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    entries = {e.name: e for e in backend.list_directory(package.remote_package_path)
               if not e.is_collection}
    for name in [package.h5_name, "aligned_orthomosaic.tif", "aligned_slope.tif", "aligned_aspect.tif"]:
        entry = entries.get(name)
        if entry is None or not entry.size_bytes:
            raise ValueError(f"Missing source/size: {package.package_name}/{name}")
        target = directory / name
        receipt = target.with_name(name + ".transfer.json")
        if target.exists() and receipt.exists():
            saved = json.loads(receipt.read_text())
            if saved.get("remote") == entry.to_dict() and saved.get("sha256") == sha256(target):
                continue
        temporary = target.with_name(name + ".part")
        temporary.unlink(missing_ok=True)
        backend.download_file(entry.path, temporary)
        if temporary.stat().st_size != entry.size_bytes:
            raise ValueError(f"Incomplete transfer: {entry.path}")
        downloaded_hash = sha256(temporary)
        if target.exists() and sha256(target) == downloaded_hash:
            temporary.unlink()  # Metadata refresh must not invalidate identical source bytes.
        else:
            temporary.replace(target)
        write_json(receipt, {"remote": entry.to_dict(), "sha256": downloaded_hash})
    return directory


def prepare_reference(source_dir, h5_name, destination, bands=tuple(range(1, 11))):
    """Explicit ten-band recipe with bounded exact comparisons and strict grids."""
    import h5py
    import numpy as np
    import rasterio
    from rasterio.windows import Window
    from spectralbridge.pipelines.drone import _drone_grid_transforms_match

    source_dir, destination = Path(source_dir), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "verified_reflectance.tif"
    temporary = destination / "verified_reflectance.part.tif"
    with rasterio.open(source_dir / "aligned_orthomosaic.tif") as src, h5py.File(source_dir / h5_name) as h:
        groups = [v["Reflectance"] for v in h.values()
                  if isinstance(v, h5py.Group) and "Reflectance" in v]
        if len(groups) != 1:
            raise ValueError("Expected one source reflectance group")
        group = groups[0]
        data = group["Reflectance_Data"]
        t = src.transform
        if not src.crs or not src.crs.is_projected or t.a <= 0 or t.e >= 0 or t.b or t.d:
            raise ValueError("Expected projected north-up unrotated TIFF")
        if len(bands) != 10 or len(set(bands)) != 10 or min(bands) < 1 or max(bands) > src.count:
            raise ValueError("Recipe requires ten distinct existing TIFF bands")
        if data.shape != (src.height, src.width, 10):
            raise ValueError("TIFF/H5 dimensions disagree")
        ancillary_grids = {}
        for name in ["aligned_slope.tif", "aligned_aspect.tif"]:
            with rasterio.open(source_dir / name) as terrain:
                if (terrain.crs != src.crs or terrain.shape != src.shape or terrain.count != 1
                        or not _drone_grid_transforms_match(t, terrain.transform, src.shape)):
                    raise ValueError(f"Ancillary grid mismatch: {name}")
                corners = ((0, 0), (src.width, 0), (0, src.height), (src.width, src.height))
                differences = np.asarray([np.asarray(t * c) - np.asarray(terrain.transform * c)
                                          for c in corners])
                ancillary_grids[name] = {
                    "maximum_corner_displacement_map_units": float(np.abs(differences).max()),
                    "source_transform_gdal": list(terrain.transform.to_gdal()),
                    "reference_transform_gdal": list(t.to_gdal()),
                    "policy": "eight_float64_coordinate_ulps; no resampling or value changes",
                }
        view = {}
        for field in ["Zenith", "Azimuth"]:
            ds = group[f"Metadata/to-sensor_{field}_Angle"]
            first = None
            for row in range(0, ds.shape[0], 128):
                values = np.asarray(ds[row:row + 128])
                if first is None:
                    first = float(values.flat[0])
                if not np.isfinite(values).all() or not np.all(values == first):
                    raise ValueError("View geometry is not a validated finite scalar")
            view[field.lower()] = first
        waves = group["Metadata/Spectral_Data/Wavelength"][()].tolist()
        widths = group["Metadata/Spectral_Data/FWHM"][()].tolist()
        if len(waves) != 10 or len(widths) != 10:
            raise ValueError("Expected ten wavelengths and FWHMs")
        profile = src.profile.copy()
        profile.update(driver="GTiff", count=10)
        try:
            with rasterio.open(temporary, "w", **profile) as dst:
                dst.update_tags(**src.tags())
                for row in range(0, src.height, 128):
                    window = Window(0, row, src.width, min(128, src.height - row))
                    a = src.read(list(bands), window=window)
                    b = np.moveaxis(data[row:row + int(window.height), :, :], 2, 0)
                    if not np.array_equal(a, b, equal_nan=True):
                        raise ValueError("Retained TIFF values differ from source H5")
                    dst.write(a, window=window)
                for index, band in enumerate(bands, 1):
                    if src.descriptions[band - 1]:
                        dst.set_band_description(index, src.descriptions[band - 1])
            if output.exists() and sha256(output) == sha256(temporary):
                temporary.unlink()
            else:
                temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        omitted = sorted(set(range(1, src.count + 1)) - set(bands))
    for name in ["aligned_slope.tif", "aligned_aspect.tif"]:
        target = destination / name
        if target.is_symlink():
            target.unlink()
        target.symlink_to((source_dir / name).resolve())
    write_json(destination / "source_recipe.json", {
        "recipe": "explicit-ten-band-source-grid-v1", "selected_bands": list(bands),
        "omitted_bands_unclassified": omitted, "view": view, "cautions": CAUTIONS,
        "ancillary_grid_validation": ancillary_grids,
        "sources": {p.name: sha256(p) for p in source_dir.iterdir()
                    if p.is_file() and p.suffix in {".h5", ".tif"}},
        "reference_sha256": sha256(output),
    })
    return output, dict(tiff_sensor_zenith_deg=view["zenith"], tiff_sensor_azimuth_deg=view["azimuth"],
                        tiff_wavelengths_nm=waves, tiff_fwhm_nm=widths)


def select_inventory(inventory, test_package=None):
    """Explicitly scope an integration test without weakening production completeness."""
    if test_package is None:
        return inventory
    from dataclasses import replace

    selected = tuple(p for p in inventory.eligible_packages if p.package_name == test_package)
    if len(selected) != 1 or not selected[0].manifest_matched:
        raise ValueError("One-flight test requires exactly one eligible manifest-matched package")
    package = selected[0]
    years = tuple(replace(y, expected_manifest_flights=(package.manifest_id,))
                  for y in inventory.year_sources if y.year == package.year)
    if len(years) != 1 or years[0].source_status != "resolved":
        raise ValueError("One-flight test year source is unavailable")
    return replace(inventory, packages=selected, year_sources=years,
                   requested_years=(package.year,))


def require_complete(inventory, statuses):
    expected = {p.remote_package_path for p in inventory.eligible_packages}
    completed = {k for k, v in statuses.items() if v.get("bulk_ready")}
    if not inventory.discovery_complete or not expected or completed != expected:
        raise RuntimeError(f"Campaign incomplete: {len(completed & expected)}/{len(expected)} ready")


def upload_tree(local, remote_parent, executable):
    """Resume checksum-verified uploads only within this run's own destination."""
    local = Path(local).resolve()
    if any(p.is_symlink() for p in local.rglob("*")):
        raise ValueError("Upload requires durable files, not symlinks")
    files = {str(p.relative_to(local)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
             for p in sorted(local.rglob("*")) if p.is_file() and p.name != "upload_manifest.json"}
    write_json(local / "upload_manifest.json", {"files": files, "cautions": CAUTIONS})
    subprocess.run([executable, "mkdir", "-p", remote_parent], check=True)
    subprocess.run([executable, "put", "--diff", "--verify_checksum", "--progress",
                    "--stop_on_error", str(local), remote_parent], check=True)
    return remote_join(remote_parent, local.name)
