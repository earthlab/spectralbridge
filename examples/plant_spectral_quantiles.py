"""Fit 1–99% boosted signatures for species/site and individual polygons."""

import argparse
import logging
from spectralbridge.plant_spectral_quantiles import (
    QuantileModelConfig,
    run_boosted_quantile_atlas,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparisons", default="artifacts/plant_spectral_atlas/comparisons"
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/quantile_models"
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=80)
    parser.add_argument("--min-plants", type=int, default=10)
    parser.add_argument(
        "--stages", nargs="+", default=["raw", "corr", "olioli", "micasense"]
    )
    parser.add_argument("--skip-individual-pdf", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    config = QuantileModelConfig(
        workers=args.workers,
        boosting_rounds=args.rounds,
        min_plants_per_species=args.min_plants,
        stages=tuple(args.stages),
    )
    print(
        run_boosted_quantile_atlas(
            args.comparisons,
            args.output,
            config=config,
            make_individual_pdf=not args.skip_individual_pdf,
        )
    )
