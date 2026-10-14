"""One-flight independent Landsat C2 L2 validation; no bulk download or fitting."""

import argparse
import json
import logging
from pathlib import Path
from spectralbridge.landsat_flight_validation import (
    FlightValidationInput,
    FlightValidationConfig,
    compare_flight_to_real_landsat,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("flight_manifest", help="JSON with FlightValidationInput fields")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--cached-search", help="Optional saved unsigned STAC FeatureCollection"
    )
    p.add_argument("--bootstraps", type=int, default=499)
    args = p.parse_args()
    flight = FlightValidationInput(**json.loads(Path(args.flight_manifest).read_text()))
    items = None
    if args.cached_search:
        import pystac

        items = [
            pystac.Item.from_dict(v)
            for v in json.loads(Path(args.cached_search).read_text())["features"]
        ]
    logging.basicConfig(level=logging.INFO)
    result = compare_flight_to_real_landsat(
        flight,
        args.output,
        config=FlightValidationConfig(bootstraps=args.bootstraps),
        items=items,
    )
    print(result["status"])


if __name__ == "__main__":
    main()
