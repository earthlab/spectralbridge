"""Reproduce raw/corrected/darkened and derived sensor comparison layouts."""

import argparse
import logging
from spectralbridge.plant_spectral_comparison import run_plant_comparison_atlas

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default="Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/comparisons"
    )
    parser.add_argument("--min-plants", type=int, default=10)
    parser.add_argument("--dpi", type=int, default=350)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    print(
        run_plant_comparison_atlas(
            args.source,
            args.output,
            min_plants_per_species=args.min_plants,
            dpi=args.dpi,
        )
    )
