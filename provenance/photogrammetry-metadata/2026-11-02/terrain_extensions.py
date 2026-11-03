"""Independent derivatives of the exact aligned elevation, without source writes."""

import json
from pathlib import Path
import numpy as np
import rasterio
from validate import horn_terrain, summary, circular_difference, sha

HERE = Path(__file__).resolve().parent
WORK = Path("/private/tmp/photogrammetry-metadata-20261102")
records = json.loads((HERE / "validation.json").read_text())
preservation = json.loads((HERE / "preservation.json").read_text())
for name, r in records.items():
    p = WORK / (name + "_aligned_dem.tif")
    digest = sha(p)
    preservation["inputs_before"][str(p)] = digest
    source = Path(r["source_h5"]).parent
    with (
        rasterio.open(p) as dem,
        rasterio.open(source / "aligned_slope.tif") as slsrc,
        rasterio.open(source / "aligned_aspect.tif") as asrc,
    ):
        z = dem.read(1)
        sl, asp = horn_terrain(z, *dem.res, dem.nodata)
        stored = slsrc.read(1)
        stored_aspect = asrc.read(1)
        valid = np.isfinite(sl) & np.isfinite(stored) & (stored >= 0) & (stored <= 90)
        record = dict(
            path=str(p),
            shape=list(dem.shape),
            resolution=list(dem.res),
            crs=dem.crs.to_string(),
            source_grid_exact=dem.transform == slsrc.transform
            and dem.crs == slsrc.crs
            and dem.shape == slsrc.shape,
            slope_absolute_error=summary(abs(sl[valid] - stored[valid])),
            aspect_circular_absolute_error=summary(
                abs(circular_difference(asp[valid], stored_aspect[valid]))
            ),
            algorithm="Independent Horn 3x3 on already-aligned elevation, no circular-aspect interpolation. Comparison does not establish executed source terrain tool/version or ground classification.",
            slope_convention="degrees",
            aspect_convention="downslope clockwise from grid north",
            solar_convention="true north; grid convergence must be handled explicitly if reference conventions differ",
        )
        r["terrain"]["aligned_dem_derivative_comparison"] = record
        np.savez_compressed(
            HERE / (name + "_aligned_terrain_display.npz"),
            elevation=z[::10, ::10],
            stored_slope=stored[::10, ::10],
            derived_slope=sl[::10, ::10],
            stored_aspect=stored_aspect[::10, ::10],
            derived_aspect=asp[::10, ::10],
            valid=valid[::10, ::10],
        )
        print(
            name,
            record["slope_absolute_error"],
            record["aspect_circular_absolute_error"],
        )
    preservation["inputs_after"][str(p)] = sha(p)
    assert digest == preservation["inputs_after"][str(p)]
(HERE / "validation.json").write_text(
    json.dumps(records, indent=2, allow_nan=False) + "\n"
)
(HERE / "preservation.json").write_text(json.dumps(preservation, indent=2) + "\n")
