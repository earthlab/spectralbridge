"""Rebuild retained synthetic/before/after diagnostics using explicit source roles."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--recovered-flight", type=Path, required=True)
    parser.add_argument("--legacy-replay", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    diagnostic = Path("scripts/diagnose_drone_spatial_integrity.py")
    synthetic = args.evidence / "synthetic_inputs"
    source = args.sources / "AOP-Ruby-08-14-23-ExportPackage"
    flight = args.recovered_flight
    stem = "AOP_Ruby_20230814"
    polygons = Path(
        "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    base = [
        "--source-tiff",
        str(source / "aligned_orthomosaic.tif"),
        "--source-bands",
        "1,2,3,4,5,6,7,8,9,10",
        "--polygons",
        str(polygons),
    ]
    cases = [
        (
            "synthetic",
            0,
            [
                "--source-tiff",
                str(synthetic / "authoritative_synthetic.tif"),
                "--h5",
                str(synthetic / "fixture__working.h5"),
                "--native",
                str(synthetic / "fixture__native.img"),
                "--corrected",
                str(synthetic / "fixture__corrected.img"),
                "--final",
                str(synthetic / "fixture__translated.img"),
                "--polygons",
                str(synthetic / "polygons.geojson"),
                "--parquet",
                str(synthetic / "spectra.parquet"),
                "--parquet-value-raster",
                str(synthetic / "fixture__corrected.img"),
                "--synthetic",
                "--label",
                "Pixel identity control; correction pass-through; synthetic translation +1",
            ],
        ),
        (
            "ruby_before",
            2,
            base
            + [
                "--h5",
                str(source / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"),
                "--native",
                str(args.legacy_replay / "legacy__native.img"),
                "--label",
                "Ruby original H5 and replayed old export; later original stages unavailable",
            ],
        ),
        (
            "ruby_after",
            0,
            base
            + [
                "--h5",
                str(flight / (stem + "__working.h5")),
                "--native",
                str(flight / (stem + "__envi.img")),
                "--corrected",
                str(flight / (stem + "__corrected.img")),
                "--final",
                str(flight / (stem + "__landsat_like_landsat_oli_translated_envi.img")),
                "--parquet",
                str(flight / (stem + "__polygons.parquet")),
                "--parquet-value-raster",
                str(flight / (stem + "__corrected.img")),
                "--id-column",
                "GlobalID",
                "--label",
                "Ruby verified source bands 1–10; existing correction and translation enabled",
            ],
        ),
    ]
    records = []
    for name, expected, options in cases:
        command = [
            sys.executable,
            str(diagnostic),
            *options,
            "--output",
            str(args.evidence / name),
        ]
        run = subprocess.run(command, text=True, capture_output=True)
        records.append(
            dict(
                name=name,
                command=command,
                returncode=run.returncode,
                expected_returncode=expected,
                stdout=run.stdout[-2000:],
                stderr=run.stderr[-2000:],
            )
        )
        print(name, run.returncode, flush=True)
        if run.returncode != expected:
            raise RuntimeError(run.stderr[-2000:])
    (args.evidence / "diagnostic_runs.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
