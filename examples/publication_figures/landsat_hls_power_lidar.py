"""Bounded public lidar reads for the fixed new evergreen candidate batch."""

import argparse

import requests

import landsat_evergreen_pointcloud as cloud
import landsat_regional_candidates as regional
from landsat_hls_sampling_batch import ROOT, CACHE
from spectralbridge.bulk.provenance import write_json_atomic


def run(region):
    directory = ROOT / "public-lidar"
    directory.mkdir(exist_ok=True)
    path = directory / f"{region}-dtm-catalogue.json"
    if not path.exists():
        payload = dict(
            collections=["3dep-lidar-dtm"], bbox=regional.REGIONS[region], limit=100
        )
        result = regional.fetch_catalogue(requests.Session(), payload)
        write_json_atomic(path, result)
        print(region, "public terrain catalogue", len(result["features"]), flush=True)
    cloud.OUTPUT = ROOT
    cloud.CACHE = CACHE
    cloud.DEST = ROOT / f"pointcloud-{region}"
    cloud.run(region=region, before_reference=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--region", choices=["cascades", "front_range", "yellowstone"], required=True
    )
    args = parser.parse_args()
    run(args.region)
