"""Run researcher-defined cover category inference on a polygon library."""
import argparse
import logging
from spectralbridge.pft_method_audit import AuditConfig
from spectralbridge.researcher_pft_statistics import run_researcher_statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--output', default='artifacts/plant_spectral_atlas/researcher_pft_statistics')
    parser.add_argument('--permutations', type=int, default=9999)
    parser.add_argument('--minimum', type=int, default=10)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    run_researcher_statistics(args.source,args.output,config=AuditConfig(permutations=args.permutations),minimum=args.minimum)


if __name__ == '__main__':
    main()
