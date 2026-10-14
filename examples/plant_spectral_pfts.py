"""Tag source species by PFT and regenerate plant-balanced spectral plot families."""

import argparse
import logging
from spectralbridge.plant_spectral_pfts import run_pft_spectral_analysis
from spectralbridge.plant_spectral_quantiles import QuantileModelConfig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparisons", default="artifacts/plant_spectral_atlas/comparisons"
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/pft_analysis"
    )
    parser.add_argument("--crosswalk", default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-individual-overlays", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    result = run_pft_spectral_analysis(
        args.comparisons,
        args.output,
        crosswalk=args.crosswalk,
        config=QuantileModelConfig(workers=args.workers),
        individual_overlays=not args.skip_individual_overlays,
    )
    print(
        {k: v for k, v in result.items() if k not in ("inputs", "config", "validation")}
    )
