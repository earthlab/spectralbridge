"""Run conditional sampled-plant PFT contrasts on existing compact spectra."""
import argparse
import logging
from spectralbridge.plant_pft_statistics import PFTStatisticsConfig, run_pft_statistics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparisons")
    parser.add_argument("--output", required=True)
    parser.add_argument("--permutations", type=int, default=9999)
    parser.add_argument("--bootstraps", type=int, default=999)
    parser.add_argument("--min-plants", type=int, default=10)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run_pft_statistics(args.comparisons, args.output, config=PFTStatisticsConfig(
        permutations=args.permutations, bootstraps=args.bootstraps, min_plants=args.min_plants))
