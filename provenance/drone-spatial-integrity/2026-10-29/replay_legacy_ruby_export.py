"""Replay the pre-repair exporter on original Ruby H5; not a historical output."""

import argparse
import json
from pathlib import Path

import rasterio

from spectralbridge.envi_writer import EnviWriter
from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import _prepare_drone_h5_working_copy


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-h5", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=True)
    working, _ = _prepare_drone_h5_working_copy(
        a.source_h5, working_path=a.workspace / "legacy__working.h5", overwrite=True
    )
    cube = NeonCube(working)
    header = cube.build_envi_header()
    # Exact pre-repair behavior: copy unadapted Map_Info, and no standard WKT field.
    writer = EnviWriter(a.workspace / "legacy__native", header)
    try:
        for ys, ye, xs, xe, chunk in cube.iter_chunks(
            chunk_y=128, chunk_x=cube.columns
        ):
            writer.write_chunk(chunk, ys, xs)
    finally:
        writer.close()
    with rasterio.open(a.workspace / "legacy__native.img") as ds:
        d = dict(
            scope="Replayed original export behavior, not a downloaded historical pipeline output",
            h5_reader_gdal_transform=cube.transform,
            export_affine=list(ds.transform)[:6],
            export_crs=ds.crs.to_string(),
            source_h5=str(a.source_h5),
            native_replay=str(a.workspace / "legacy__native.img"),
            working_replay=str(working),
        )
    (a.evidence / "legacy_ruby_export_replay.json").write_text(
        json.dumps(d, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
