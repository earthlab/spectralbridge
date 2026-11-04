"""Recover actual report calibration rows without inventing PhotoID/sensor binding."""

import json
from pathlib import Path
import re
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    text = (
        ROOT
        / "provenance/goldhill-micasense-calibration/2026-11-03/goldhill_processing_report_text.txt"
    ).read_text()
    rows = []
    for number in range(4, 14):
        part = re.search(
            r"PAGE " + str(number) + r"\n(.*?)(?=\nPAGE |\Z)", text, re.S
        ).group(1)
        camera = (
            re.search(r"RedEdge-M,\s*(.*?)\n609", part, re.S)
            .group(1)
            .replace("\t", " ")
            .replace("\n", " ")
        )
        row = dict(report_page=number, report_sensor_name=camera)
        for key in ["F", "Cx", "Cy", "B1", "B2", "K1", "K2", "K3", "P1", "P2"]:
            match = re.search(
                r"\n" + key + r"\n(-?[0-9.eE+\-]+)\n(-?[0-9.eE+\-]+)\n", part
            )
            if match is None:
                raise ValueError((number, key))
            row[key] = float(match[1])
            row[key + "_reported_error"] = float(match[2])
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(HERE / "reported_sensor_calibrations.csv", index=False)
    summary = dict(
        sensors=len(frame),
        focal_pixels_range=[float(frame.F.min()), float(frame.F.max())],
        nominal_focal_pixels=5.5 / (3.75 * 0.001),
        principal_Cx_pixels_range=[float(frame.Cx.min()), float(frame.Cx.max())],
        principal_Cy_pixels_range=[float(frame.Cy.min()), float(frame.Cy.max())],
        interpretation="Report calibration coefficient rows are available and preserved. Full report includes distortion parameters and correlations. Nominal ideal rectangles were intentionally used as approximate scenarios because sensor-to-PhotoID rig binding, camera/world conventions, distortion/export applicability and per-band contributor maps are not verified. Do not claim the report lacks intrinsics.",
        photoID_association="Each position has suffix1-10; their exact association to report sensor names/wavelengths requires original BandName/Wavelength/rig metadata. Existing mosaic wavelengths remain the source-reader contract; no unverified filename-based wavelength remapping.",
        main_scenario="1280x960, nominal1466.67pixel focal length; +/-20% size and yaw90 sensitivity are wider than reported focal-length spread, but do not model exact distorted camera footprints",
    )
    (HERE / "intrinsic_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(summary)


if __name__ == "__main__":
    main()
