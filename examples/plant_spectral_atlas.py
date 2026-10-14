"""Reproduce a plant-balanced corrected spectral atlas from the source library."""

import argparse
import logging
from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default="Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    )
    parser.add_argument("--output", default="artifacts/plant_spectral_atlas")
    parser.add_argument("--min-plants", type=int, default=10)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(
        run_plant_spectral_atlas(
            args.source, args.output, min_plants_per_species=args.min_plants
        )
    )
