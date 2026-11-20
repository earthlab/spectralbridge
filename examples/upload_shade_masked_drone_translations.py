"""Upload the verified six-product manifest; never overwrite differing remote data.

Requires python-irodsclient and the user's existing iRODS environment. Credentials
are read by the client, never copied into outputs. Run after the translation
runner. Every object is verified by SHA-256 readback; a completion manifest is
published only after all payload files pass. Unchanged objects are reused.
"""

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from irods.session import iRODSSession

ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/translated-products"
)
PARENT = "/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed"
PREVIOUS = PARENT + "/gordon_goldhill_ruby_brightness_baseline_20261113_v1/2026-11-13"
DEST = PARENT + "/gordon_goldhill_ruby_micasense_landsat_translations_20261119_v1"


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def remote_digest(session, path):
    digest = hashlib.sha256()
    size = 0
    with session.data_objects.open(path, "r") as stream:
        while True:
            block = stream.read(8 * 1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return digest.hexdigest(), size


def default_payload_files(report):
    verification = json.loads((report / "verification.json").read_text())
    files = []
    for product in verification["products"]:
        if product.get("gdal_envi_metadata_roundtrip") != "PASS":
            raise ValueError("Finish standard-reader metadata verification first")
        for key in ["output_img", "output_hdr", "provenance_json"]:
            local = Path(product[key])
            expected = product["sha256"][str(local)]
            if digest_file(local) != expected:
                raise ValueError(f"Changed verified output: {local.name}")
            files.append((local, f"{product['site']}/{local.name}"))
    files.extend(
        [
            (report / "README.md", "README.md"),
            (report / "verification.json", "verification.json"),
            (
                Path(verification["registry"]),
                "provenance/fractional_reflectance_translation_registry.json",
            ),
            (
                ROOT / "examples/run_shade_masked_drone_translations.py",
                "provenance/run_shade_masked_drone_translations.py",
            ),
        ]
    )
    return files


def run(*, report=REPORT, destination=DEST, previous=PREVIOUS, payload_files=None):
    """Upload a verified payload; defaults preserve the original masked batch."""
    files = default_payload_files(report) if payload_files is None else payload_files
    records = []
    with iRODSSession(
        irods_env_file=str(Path.home() / ".irods/irods_environment.json"),
        connection_timeout=60,
    ) as session:
        if not session.collections.exists(previous):
            raise ValueError(
                "Prior calibration collection not found; do not guess destination"
            )
        print(
            f"Prior calibration collection confirmed; uploading to {destination}",
            flush=True,
        )
        for local, relative in files:
            remote = destination + "/" + relative
            sha256 = digest_file(local)
            size = local.stat().st_size
            if session.data_objects.exists(remote):
                actual, remote_size = remote_digest(session, remote)
                if actual != sha256 or remote_size != size:
                    raise ValueError(
                        f"Refusing to overwrite differing remote object: {remote}"
                    )
                status = "reused"
            else:
                session.collections.create(str(Path(remote).parent), recurse=True)
                print(f"Uploading {relative} ({size:,} bytes)", flush=True)
                # Serial transfer is bounded in memory and avoids server parallel-port assumptions.
                session.data_objects.put(str(local), remote, num_threads=1)
                actual, remote_size = remote_digest(session, remote)
                if actual != sha256 or remote_size != size:
                    raise ValueError(f"Remote SHA-256 readback mismatch: {remote}")
                status = "uploaded"
            checksum = session.data_objects.chksum(remote)
            if checksum.startswith("sha2:"):
                assert checksum[5:] == base64.b64encode(bytes.fromhex(sha256)).decode()
            elif len(checksum) == 32:
                with local.open("rb") as stream:
                    md5 = hashlib.md5()
                    for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                        md5.update(block)
                assert checksum == md5.hexdigest()
            records.append(
                dict(
                    local=str(local),
                    remote=remote,
                    bytes=size,
                    sha256=sha256,
                    server_checksum=checksum,
                    readback="PASS",
                    status=status,
                )
            )
            (report / "upload_progress.json").write_text(
                json.dumps(records, indent=2) + "\n"
            )
            print(f"Verified {relative}: SHA-256 readback PASS", flush=True)
        result = dict(
            status="COMPLETE",
            completed_utc=datetime.now(timezone.utc).isoformat(),
            destination=destination,
            previous_calibration_collection=previous,
            scientific_validation_status="EXPERIMENTAL",
            output_scale_factor=1000,
            total_bytes=sum(r["bytes"] for r in records),
            files=records,
        )
        complete = report / "datastore_upload_complete.json"
        if not complete.exists():
            complete.write_text(json.dumps(result, indent=2) + "\n")
        remote = destination + "/datastore_upload_complete.json"
        if not session.data_objects.exists(remote):
            session.data_objects.put(str(complete), remote, num_threads=1)
        if remote_digest(session, remote)[0] != digest_file(complete):
            raise ValueError("Completion manifest readback mismatch")
        print(
            f"COMPLETE: {len(records)} payload files; {result['total_bytes']:,} bytes; all readbacks verified.",
            flush=True,
        )


if __name__ == "__main__":
    run()
