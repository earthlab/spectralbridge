"""Offline checks of the root cloud notebook's explicit recovery recipe."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest
import rasterio
from affine import Affine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drone_cloud_workflow", ROOT / "scripts/drone_cloud_workflow.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def sources(tmp_path):
    directory = tmp_path / "original"
    directory.mkdir()
    values = np.arange(11 * 3 * 5, dtype="float32").reshape(11, 3, 5)
    values[:, 0, 0] = np.nan
    profile = dict(driver="GTiff", height=3, width=5, count=11, dtype="float32",
                   crs="EPSG:26913", transform=Affine(.1, 0, 450000, 0, -.1, 4430000))
    with rasterio.open(directory / "aligned_orthomosaic.tif", "w", **profile) as dst:
        dst.write(values)
    profile.update(count=1)
    for name in ["aligned_slope.tif", "aligned_aspect.tif"]:
        with rasterio.open(directory / name, "w", **profile) as dst:
            dst.write(np.zeros((1, 3, 5), dtype="float32"))
    with h5py.File(directory / "original.h5", "w") as h:
        group = h.create_group("NIWO/Reflectance")
        group.create_dataset("Reflectance_Data", data=np.moveaxis(values[:10], 0, 2))
        for field, angle in [("Zenith", 0.), ("Azimuth", 25.)]:
            group.create_dataset(f"Metadata/to-sensor_{field}_Angle", data=np.full((3, 5), angle))
        group.create_dataset("Metadata/Spectral_Data/Wavelength", data=np.arange(10) + 450.)
        group.create_dataset("Metadata/Spectral_Data/FWHM", data=np.full(10, 20.))
    return directory, values


def test_reference_preserves_grid_values_and_restart(tmp_path):
    directory, values = sources(tmp_path)
    original_hash = workflow.sha256(directory / "original.h5")
    reference, options = workflow.prepare_reference(directory, "original.h5", tmp_path / "prepared")
    with rasterio.open(reference) as dst, rasterio.open(directory / "aligned_orthomosaic.tif") as src:
        np.testing.assert_array_equal(dst.read(), values[:10])
        assert dst.transform == src.transform and dst.crs == src.crs
    before = reference.stat().st_mtime_ns
    workflow.prepare_reference(directory, "original.h5", tmp_path / "prepared")
    assert reference.stat().st_mtime_ns == before
    assert workflow.sha256(directory / "original.h5") == original_hash
    assert options["tiff_sensor_azimuth_deg"] == 25
    assert json.loads((reference.parent / "source_recipe.json").read_text())["omitted_bands_unclassified"] == [11]


@pytest.mark.parametrize("damage", ["reflectance", "view", "terrain"])
def test_bad_source_stops_before_publishing(tmp_path, damage):
    directory, _ = sources(tmp_path)
    if damage == "terrain":
        with rasterio.open(directory / "aligned_slope.tif", "r+") as dst:
            dst.transform = Affine(.1, 0, 450001, 0, -.1, 4430000)
    else:
        with h5py.File(directory / "original.h5", "r+") as h:
            key = "Reflectance_Data" if damage == "reflectance" else "Metadata/to-sensor_Zenith_Angle"
            ds = h[f"NIWO/Reflectance/{key}"]
            if damage == "reflectance":
                ds[1, 1, 0] = 900
            else:
                ds[1, 1] = 5
    with pytest.raises(ValueError):
        workflow.prepare_reference(directory, "original.h5", tmp_path / "prepared")
    assert not (tmp_path / "prepared/verified_reflectance.tif").exists()


def test_json_listing_and_completeness():
    rows = [{"data": [{"Path": "/source", "Type": "collection"}]},
            {"data": [{"Name": "flight", "Type": "collection", "Size": ""},
                      {"Name": "file.h5", "Type": "data-object", "Size": "123"}]}]
    entries = workflow.parse_listing(json.dumps(rows), "i:/source")
    assert entries[1].path == "i:/source/file.h5" and entries[1].size_bytes == 123
    inventory = SimpleNamespace(discovery_complete=True,
                                eligible_packages=[SimpleNamespace(remote_package_path="flight")])
    workflow.require_complete(inventory, {"flight": {"bulk_ready": True}})
    for statuses in [{}, {"flight": {"bulk_ready": False}},
                     {"flight": {"bulk_ready": True}, "stale": {"bulk_ready": True}}]:
        with pytest.raises(RuntimeError, match="incomplete"):
            workflow.require_complete(inventory, statuses)
    inventory.discovery_complete = False
    with pytest.raises(RuntimeError):
        workflow.require_complete(inventory, {"flight": {"bulk_ready": True}})


def test_upload_checksums_and_excludes_symlinks(tmp_path, monkeypatch):
    folder = tmp_path / "flight_products"
    folder.mkdir()
    (folder / "corrected.img").write_bytes(b"processed")
    commands = []
    monkeypatch.setattr(workflow.subprocess, "run", lambda argv, **kw: commands.append(argv))
    remote = workflow.upload_tree(folder, "i:/results/run1", "gocmd")
    assert remote == "i:/results/run1/flight_products"
    assert "--verify_checksum" in commands[-1] and "--diff" in commands[-1]
    manifest = json.loads((folder / "upload_manifest.json").read_text())
    assert manifest["files"]["corrected.img"]["sha256"] == workflow.sha256(folder / "corrected.img")
    (folder / "source_link").symlink_to(folder / "corrected.img")
    with pytest.raises(ValueError, match="symlinks"):
        workflow.upload_tree(folder, "i:/results/run1", "gocmd")


def test_notebook_clean_and_code_compiles():
    notebook = json.loads((ROOT / "Drone_2023_2024_Cloud_Production.ipynb").read_text())
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None
            compile("".join(cell["source"]), f"cell {index}", "exec")
    source = "\n".join("".join(c["source"]) for c in notebook["cells"])
    assert 'RUN = False' in source and 'UPLOAD = False' in source
    assert 'materialize_observations=False' in source
    assert source.index('require_complete(inventory, statuses)') < source.index('preflight = run_bulk_pipeline')
