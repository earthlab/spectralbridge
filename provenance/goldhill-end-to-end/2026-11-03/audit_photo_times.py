"""Join supplied camera IDs to original photo tags without inferring time zones."""

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
WORK = Path("/private/tmp/goldhill-end-to-end-20261103")
files = sorted((WORK / "source_metadata").glob("SD*_image_metadata.csv"))
source = []
frames = []
for path in files:
    source.append(
        dict(
            path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            bytes=path.stat().st_size,
            remote_origin="/iplant/home/shared/earthlab/macrosystems/field-data/uas-packages/AOP-GOLDHILL-08-14-23-ExportPackage/Metadata/"
            + path.name,
        )
    )
    frame = pd.read_csv(path)
    frame["source_metadata_file"] = path.name
    frames.append(frame)
photos = pd.concat(frames, ignore_index=True)
photos["PhotoID"] = photos.filename.map(lambda value: Path(value).stem)
photos["timestamp_unzoned"] = pd.to_datetime(
    photos.TIFFTAG_DATETIME, format="%Y:%m:%d %H:%M:%S"
)
assert photos.PhotoID.is_unique
camera = pd.read_csv(
    "/Users/tuff/Downloads/AOP-GOLDHILL-camera_locations.csv", skiprows=2
)
camera.columns = camera.columns.str.strip().str.removeprefix("# ")
matched = camera.merge(photos, on="PhotoID", how="left", validate="one_to_one")
assert matched.TIFFTAG_DATETIME.notna().all()
matched.to_csv(HERE / "camera_poses_with_photo_times.csv", index=False)
start, end = matched.timestamp_unzoned.min(), matched.timestamp_unzoned.max()
mid = start + (end - start) / 2
inherited = pd.Timestamp("2023-08-15 19:53:07")
record = dict(
    status="PASS",
    sources=source,
    original_photos=len(photos),
    unique_photo_ids=int(photos.PhotoID.nunique()),
    all_photo_tag_dates=sorted(
        photos.timestamp_unzoned.dt.strftime("%Y-%m-%d").unique().tolist()
    ),
    all_photo_start=str(photos.timestamp_unzoned.min()),
    all_photo_end=str(photos.timestamp_unzoned.max()),
    camera_records=len(camera),
    camera_records_uniquely_matched=len(matched),
    unmatched=0,
    ambiguous_ids=0,
    matched_start=str(start),
    matched_end=str(end),
    matched_midpoint=str(mid),
    inherited_solar_datetime=str(inherited),
    inherited_minus_midpoint_seconds=(inherited - mid).total_seconds(),
    timezone_status="NOT_EXPLICIT_IN_TIFFTAG_DATETIME CSV; do not silently assign a timezone",
    interpretation="All linked photo tags support August 15, not the August 14 nominal package name/note. The inherited solar time lies 5.5 seconds from their midpoint in the same clock-number convention. This supports the inherited scene timestamp but does not establish camera-clock/timezone accuracy or per-pixel solar/view contributor assignments.",
)
(HERE / "photo_time_reconciliation.json").write_text(
    json.dumps(record, indent=2) + "\n"
)
print(json.dumps(record, indent=2))
