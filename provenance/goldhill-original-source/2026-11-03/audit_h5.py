"""Verify the two 25 cm H5 candidates against their neighboring TIFFs."""

import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
TEMP = Path("/private/tmp/p168-goldhill-sources")


def safe(value):
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    if isinstance(value, np.ndarray):
        return safe(value.tolist())
    if isinstance(value, np.generic):
        return safe(value.item())
    if isinstance(value, list):
        return [safe(x) for x in value]
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


records = []
for parent, tif, remote in [
    (
        "h5_original",
        "/private/tmp/spectralbridge-scale-confirmation/base/goldhill.tif",
        "summer-2023",
    ),
    (
        "h5_rescaled",
        "/private/tmp/spectralbridge-scale-confirmation/rescale/goldhill.tif",
        "summer-2023-rescale",
    ),
]:
    p = TEMP / parent / "source.h5"
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    with h5py.File(p, "r") as h, rasterio.open(tif) as src:
        d = h["NIWO/Reflectance/Reflectance_Data"]
        matches = []
        metadata = []

        def visit(name, x):
            if isinstance(x, h5py.Dataset):
                item = dict(
                    path=name,
                    shape=list(x.shape),
                    dtype=str(x.dtype),
                    attrs=safe(dict(x.attrs)),
                )
                if x.size <= 100:
                    item["value"] = safe(x[()])
                metadata.append(item)

        h.visititems(visit)
        for band in range(1, 11):
            a = d[..., band - 1]
            b = src.read(band)
            v = np.isfinite(b)
            matches.append(
                dict(
                    band=band,
                    finite_values_exact=bool(np.array_equal(a[v], b[v])),
                    missingness_exact=bool(
                        np.array_equal(np.isfinite(a), np.isfinite(b))
                    ),
                    max_abs_difference=float(np.max(abs(a[v] - b[v]))),
                )
            )
        assert all(x["finite_values_exact"] for x in matches)
        record = dict(
            path=str(p),
            remote_origin="/iplant/home/shared/earthlab/macrosystems/field-data/output/"
            + remote
            + "/AOP-GOLDHILL-08-14-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5",
            bytes=p.stat().st_size,
            sha256=before,
            shape=list(d.shape),
            dtype=str(d.dtype),
            reflectance_dataset_attributes=safe(dict(d.attrs)),
            metadata=metadata,
            paired_tiff=tif,
            bands=matches,
            physical_calibration="No explicit physical affine record established by dataset attributes",
        )
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
    records.append(record)
(HERE / "h5_source_audit.json").write_text(json.dumps(records, indent=2) + "\n")
print("Two 25 cm H5s verified against all ten neighboring TIFF bands")
