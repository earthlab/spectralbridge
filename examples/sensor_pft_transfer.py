"""Paired synthetic OLI spectral-resolution transfer, with MicaSense safety gate."""

import argparse
import logging
from spectralbridge.pft_method_audit import AuditConfig
from spectralbridge.sensor_pft_transfer import run_sensor_pft_transfer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/sensor_pft_transfer"
    )
    p.add_argument("--permutations", type=int, default=9999)
    p.add_argument("--bootstraps", type=int, default=499)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    run_sensor_pft_transfer(
        args.source,
        args.output,
        config=AuditConfig(permutations=args.permutations),
        bootstraps=args.bootstraps,
    )


if __name__ == "__main__":
    main()
