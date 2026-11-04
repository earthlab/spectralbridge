"""Contract checks for the explicit numerical derivative (not calibration)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

PATH = (
    Path(__file__).resolve().parents[1]
    / "provenance/goldhill-original-source/2026-11-03/create_fixed_10k.py"
)
spec = importlib.util.spec_from_file_location("goldhill_fixed_encoding", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("source_resolution,source_size", [(0.1, 4), (0.05, 8)])
def test_fixed_type_range_preserves_nonzero_minima_and_source_validity(
    tmp_path, source_resolution, source_size
):
    source = tmp_path / "original.tif"
    template = tmp_path / "grid.tif"
    dest = tmp_path / "derived.tif"
    data = np.full((11, source_size, source_size), 174, np.uint16)
    data[10] = 65535
    data[:10, 0, 0] = 65535
    data[10, 0, 0] = 0
    data[:10, -1, -1] = 0  # legitimate observed zero
    transform = from_origin(500000, 4400000, source_resolution, source_resolution)
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=source_size,
        height=source_size,
        count=11,
        dtype="uint16",
        crs="EPSG:26913",
        transform=transform,
    ) as out:
        out.write(data)
        out.colorinterp = (
            ColorInterp.gray,
            *([ColorInterp.undefined] * 9),
            ColorInterp.alpha,
        )
    # Declare the synthetic alpha role through GDAL PAM because this GDAL
    # writer does not retain an eleventh-band alpha tag on this tiny fixture.
    source.with_suffix(".tif.aux.xml").write_text(
        '<PAMDataset><PAMRasterBand band="11"><ColorInterp>Alpha</ColorInterp>'
        "</PAMRasterBand></PAMDataset>"
    )
    with rasterio.open(
        template,
        "w",
        driver="GTiff",
        width=4,
        height=4,
        count=1,
        dtype="float32",
        crs="EPSG:26913",
        transform=from_origin(500000, 4400000, 0.1, 0.1),
    ) as out:
        out.write(np.ones((1, 4, 4), np.float32))
    before = source.read_bytes()
    record = module.create(source, template, dest)
    with rasterio.open(dest) as out:
        assert out.count == 10 and out.res == (0.1, 0.1) and np.isnan(out.nodata)
        values = out.read(1)
        assert values[1, 1] == pytest.approx(174 * 10000 / 65535, abs=3e-6)
        assert values[1, 1] > 0  # no observed-minimum subtraction
        assert values[np.isfinite(values)].max() < 100  # transparent 65535 never leaks
        assert out.dataset_mask()[0, 0] == 0
        if source_resolution == 0.1:
            assert values[-1, -1] == 0 and out.dataset_mask()[-1, -1] == 255
        assert out.tags()["PHYSICAL_CALIBRATION_STATUS"] == "UNVERIFIED"
    assert source.read_bytes() == before
    assert record["numeric_offset"] == 0 and record["clipping"] == "NONE"
    assert record["radiometry"]["status"] == "UNSUPPORTED"
    with pytest.raises(FileExistsError):
        module.create(source, template, dest)
