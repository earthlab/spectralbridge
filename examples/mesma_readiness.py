"""Experimental MESMA readiness audit: compact data, explicit support, grouped tests."""

import argparse
import logging
from spectralbridge.mesma_readiness import run_readiness, ReadinessConfig

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument("--compact", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--first-pass", action="store_true")
    p.add_argument("--skip-flight-folds", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    result = run_readiness(
        args.source,
        args.compact,
        args.output,
        first_pass=args.first_pass,
        config=ReadinessConfig(all_flights=not args.skip_flight_folds),
    )
    print(result["status"])
