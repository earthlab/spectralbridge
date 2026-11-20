"""Read-only retrieval of the exact-named archived training-product headers.

Uses the user's existing iRODS session configuration. Downloads headers only,
never full rasters, and never records credentials. Retains duplicate locations
and verifies whether their header contents agree before interpreting units.
Requires python-irodsclient (temporary install is sufficient).
"""

import base64
import hashlib
import json
from pathlib import Path

import pandas as pd
from irods.models import Collection, DataObject
from irods.column import Like
from irods.session import iRODSSession
from spectralbridge.envi import hdr_to_dict
from spectralbridge.bulk.provenance import write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
DEST = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/aop-translation-audit"
)
REMOTE = "/iplant/home/shared/earthlab/macrosystems/Aug_2026_Full_Extraction"


def run():
    manifest = json.loads(
        (ROOT / "archive/research/bulk-calibration/bulk_manifest.json").read_text()
    )
    desired = {
        Path(row["header_path"]).name: row
        for row in manifest["input_signature"]["catalog"]["source_files"]
    }
    headers = DEST / "training_headers"
    headers.mkdir(exist_ok=True)
    records = []
    with iRODSSession(
        irods_env_file=str(Path.home() / ".irods/irods_environment.json"),
        connection_timeout=30,
    ) as session:
        query = session.query(
            Collection.name, DataObject.name, DataObject.size, DataObject.checksum
        ).filter(Like(Collection.name, REMOTE + "/%"), Like(DataObject.name, "%.hdr"))
        candidates = {key: [] for key in desired}
        for i, row in enumerate(query):
            if i >= 20000:
                raise ValueError("Header discovery limit exceeded")
            name = row[DataObject.name]
            if name in candidates:
                candidates[name].append(
                    dict(
                        path=row[Collection.name] + "/" + name,
                        bytes=row[DataObject.size],
                        checksum=row[DataObject.checksum],
                    )
                )
        for index, (name, source) in enumerate(sorted(desired.items()), 1):
            locations = sorted(candidates[name], key=lambda x: x["path"])
            if not locations:
                records.append(dict(header=name, status="NOT_FOUND"))
                continue
            digests = []
            for duplicate, entry in enumerate(locations):
                if entry["bytes"] > 500000:
                    raise ValueError("Unexpectedly large header")
                path = headers / (
                    name if duplicate == 0 else name + f".duplicate{duplicate}"
                )
                if path.exists():
                    body = path.read_bytes()
                else:
                    with session.data_objects.open(entry["path"], "r") as stream:
                        body = stream.read(500001)
                    if len(body) != entry["bytes"]:
                        raise ValueError("Incomplete header read")
                    path.write_bytes(body)
                checksum = entry["checksum"]
                if checksum and checksum.startswith("sha2:"):
                    assert (
                        base64.b64encode(hashlib.sha256(body).digest()).decode()
                        == checksum[5:]
                    )
                elif checksum and len(checksum) == 32:
                    assert hashlib.md5(body).hexdigest() == checksum
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                digests.append(entry["sha256"])
            if len(set(digests)) != 1:
                raise ValueError("Conflicting duplicate training headers: " + name)
            h = hdr_to_dict(headers / name)
            dims = json.loads(source["dimensions_json"])
            if (
                int(h["bands"]) != dims["bands"]
                or int(h["lines"]) != dims["rows"]
                or int(h["samples"]) != dims["columns"]
            ):
                raise ValueError(
                    "Archived header dimensions differ from training catalogue"
                )
            records.append(
                dict(
                    header=name,
                    status="READ_VERIFIED",
                    sensor=source["sensor_name"],
                    site=source["site"],
                    flightline=source["canonical_flightline_id"],
                    reflectance_scale_factor=h.get("reflectance scale factor"),
                    radiometry_status=h.get("radiometry status"),
                    physical_multiplier=h.get("physical reflectance multiplier"),
                    physical_offset=h.get("physical reflectance offset"),
                    provenance=h.get("radiometry provenance"),
                    header_sha256=digests[0],
                    duplicate_count=len(locations),
                    matched_training_dimensions=True,
                    locations=locations,
                )
            )
            print(
                index,
                "/",
                len(desired),
                source["site"],
                source["sensor_name"],
                "scale=",
                h.get("reflectance scale factor"),
                flush=True,
            )
            write_json_atomic(
                DEST / "training_header_retrieval.json",
                dict(
                    remote_root=REMOTE,
                    records=records,
                    complete=False,
                    credentials_recorded=False,
                ),
            )
    write_json_atomic(
        DEST / "training_header_retrieval.json",
        dict(
            remote_root=REMOTE,
            records=records,
            complete=True,
            credentials_recorded=False,
        ),
    )
    pd.DataFrame(
        [{k: v for k, v in r.items() if k != "locations"} for r in records]
    ).to_csv(DEST / "training_header_scale_audit.csv", index=False)


if __name__ == "__main__":
    run()
