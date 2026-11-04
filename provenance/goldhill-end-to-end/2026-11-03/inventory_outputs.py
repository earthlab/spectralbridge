"""Checksum the dated experimental products without copying pixel datasets."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path("/private/tmp/goldhill-end-to-end-20261103")
rows = []
for path in sorted(WORK.rglob("*")):
    if not path.is_file() or "pdf_preview" in path.parts:
        continue
    if path.suffix.lower() not in {
        ".tif",
        ".img",
        ".hdr",
        ".h5",
        ".npy",
        ".parquet",
        ".json",
        ".csv",
    }:
        continue
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b""):
            digest.update(block)
    rows.append(
        dict(
            path=str(path),
            bytes=path.stat().st_size,
            sha256=digest.hexdigest(),
            namespace=str(path.relative_to(WORK).parts[0]),
            scientific_status="EXPERIMENTAL_NUMERICAL_ONLY; no physical correction/library approval",
        )
    )
(HERE / "outputs_manifest.json").write_text(
    json.dumps(
        dict(
            root=str(WORK),
            files=rows,
            total_bytes=sum(x["bytes"] for x in rows),
            production_store_writes=0,
        ),
        indent=2,
    )
    + "\n"
)
print(len(rows), "experimental files checksummed")
