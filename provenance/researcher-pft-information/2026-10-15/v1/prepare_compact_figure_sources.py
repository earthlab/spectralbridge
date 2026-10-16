"""Preserve compact numerical figure inputs without copying source spectra."""

import hashlib
import json
import shutil
import pandas as pd
from common import BASE, CACHE, REPO


def main():
    records = []
    for source in sorted((CACHE / "classification").glob("*/training_correlation.npz")):
        target = BASE / "tables" / f"training_correlation_{source.parent.name}.npz"
        shutil.copyfile(source, target)
        records.append(
            {
                "source": str(source.relative_to(REPO)),
                "target": str(target.relative_to(BASE)),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    source = REPO / "provenance/sensor-pft-transfer/2026-10-14/effect_retention.csv"
    frame = pd.read_csv(source)
    frame = frame[frame.scheme.eq("researcher_category")]
    target = BASE / "tables/reused_researcher_sensor_effect_retention.csv"
    frame.to_csv(target, index=False)
    records.append(
        {
            "source": str(source.relative_to(REPO)),
            "target": str(target.relative_to(BASE)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "filter": "scheme == researcher_category",
            "rows": len(frame),
        }
    )
    (BASE / "compact_figure_sources.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
