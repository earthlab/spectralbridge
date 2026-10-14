"""Fit species quantile panels separately by acquisition year and NEON site."""

import argparse
import logging
from spectralbridge.plant_spectral_quantiles import QuantileModelConfig
from spectralbridge.plant_spectral_years import run_year_site_quantiles

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparisons", default="artifacts/plant_spectral_atlas/comparisons"
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/year_site_quantiles"
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    result = run_year_site_quantiles(
        args.comparisons, args.output, config=QuantileModelConfig(workers=args.workers)
    )
    print({k: v for k, v in result.items() if k not in ("inputs", "config")})
