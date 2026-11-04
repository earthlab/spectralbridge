"""Real CyVerse discovery and verified source staging; no publication or upload."""

import argparse
import json
from pathlib import Path
from spectralbridge.remote import GocmdRemoteBackend
from spectralbridge.drone_production import (
    inspect_original_drone_packages,
    stage_original_drone_package,
)

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2] / "archive/local/drone-three-site-integration/2026-11-04"
SOURCE = "/iplant/home/shared/earthlab/macrosystems/field-data/uas-packages"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=["Gordon", "Goldhill", "Ruby"])
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--gocmd", default="gocmd")
    parser.add_argument("--staging-dir", type=Path, default=WORK / "inputs")
    parser.add_argument("--evidence-dir", type=Path, default=HERE)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    sites = [args.site] if args.site else ["Gordon", "Goldhill", "Ruby"]
    backend = GocmdRemoteBackend(
        args.gocmd,
        detailed_listing=True,
        verify_checksums=True,
    )
    for site in sites:
        print("Discover original package:", site, flush=True)
        selection = inspect_original_drone_packages(
            args.source, sites=[site], backend=backend
        )[site]
        (args.evidence_dir / f"{site.lower()}_remote_selection.json").write_text(
            json.dumps(selection, indent=2) + "\n"
        )
        if not selection["status"].startswith("SELECTED"):
            continue
        print("Verified staging:", selection["orthomosaic"]["path"], flush=True)
        stage = stage_original_drone_package(
            selection, staging_dir=args.staging_dir, backend=backend
        )
        (args.evidence_dir / f"{site.lower()}_transfers.json").write_text(
            json.dumps(stage, indent=2) + "\n"
        )
        print(
            site,
            len(stage["transfers"]),
            "files staged; checksums verified",
            flush=True,
        )


if __name__ == "__main__":
    main()
