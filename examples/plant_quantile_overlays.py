"""Overlay each percentile across all individual plants, descending 100 to 1."""

import argparse
import logging
from spectralbridge.plant_quantile_overlays import run_quantile_overlays

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", default="artifacts/plant_spectral_atlas/quantile_models"
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/quantile_overlays"
    )
    parser.add_argument("--stages", nargs="+", default=["corr", "raw"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    result = run_quantile_overlays(args.models, args.output, stages=tuple(args.stages))
    print(
        {
            s: {k: v for k, v in r.items() if k != "GlobalIDs"}
            for s, r in result["stages"].items()
        }
    )
