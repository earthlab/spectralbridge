"""Inspect a tiny synthetic spectral library offline, through the public API.

No observations are downloaded, corrected or calibrated. The temporary table is
invented teaching data, not a model of real sensor performance.
"""

from pathlib import Path
import json
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from spectralbridge import inspect_spectral_library_preflight


def main():
    rows = []
    for species in ("example_plant_A", "example_plant_B"):
        for sample in range(3):
            rows.append({
                "pixel_id": f"{species}-{sample}",
                "species": species,
                "polygon_id": 1 if species.endswith("A") else 2,
                "flightline_id": "synthetic-flight",
                "site": "synthetic-site",
                "corr_b001_wl0450nm": 0.10 + sample * 0.01,
                "corr_b002_wl0550nm": 0.20 + sample * 0.01,
                "corr_b003_wl0700nm": 0.30 + sample * 0.01,
            })
    with tempfile.TemporaryDirectory(prefix="spectralbridge-first-example-") as directory:
        source = Path(directory) / "synthetic-library.parquet"
        pq.write_table(pa.Table.from_pylist(rows), source)
        report = inspect_spectral_library_preflight(source)
        print(json.dumps({
            "data_kind": "invented teaching data; no scientific validation",
            "wavelengths_nm": [450, 550, 700],
            "counts": report["counts"],
            "pdfs_generated": report["pdfs_generated"],
        }, indent=2))


if __name__ == "__main__":
    main()
