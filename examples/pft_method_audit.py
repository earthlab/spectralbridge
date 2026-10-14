"""Compare predeclared PFT whole-spectrum tests on verified compact inputs."""
import argparse
import logging
from spectralbridge.pft_method_audit import AuditConfig, run_method_audit

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparisons')
    parser.add_argument('legacy')
    parser.add_argument('--output',required=True)
    parser.add_argument('--permutations',type=int,default=9999)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    run_method_audit(args.comparisons,args.legacy,args.output,config=AuditConfig(permutations=args.permutations))
