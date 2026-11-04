"""Read classic TIFF metadata without decoding its eleven image channels."""

import json
from pathlib import Path
import struct
from PIL.TiffTags import TAGS

HERE = Path(__file__).resolve().parent
source = Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif")
with source.open("rb") as stream:
    header = stream.read(8)
    order = "<" if header[:2] == b"II" else ">"
    magic, offset = struct.unpack(order + "HI", header[2:])
    assert magic == 42
    stream.seek(offset)
    count = struct.unpack(order + "H", stream.read(2))[0]
    entries = [struct.unpack(order + "HHII", stream.read(12)) for _ in range(count)]
    rows = []
    for tag, kind, size, value in entries:
        row = dict(tag=tag, name=TAGS.get(tag, str(tag)), type=kind, count=size)
        if kind == 2 or tag == 700:
            if size <= 4:
                raw = struct.pack(order + "I", value)[:size]
            else:
                stream.seek(value)
                raw = stream.read(size)
            row["value"] = raw.decode("utf-8", errors="replace").rstrip("\x00")
        rows.append(row)
(HERE / "original_tiff_ifd.json").write_text(json.dumps(rows, indent=2) + "\n")
assert not ({270, 305, 306, 700, 34665} & {r["tag"] for r in rows})
print(
    "Original TIFF has no embedded description/software/time/XMP/EXIF declaration of applied reflectance calibration"
)
